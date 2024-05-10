#!/usr/bin/python3
import sys

if sys.version_info.major < 3:
    raise NotImplementedError("This program requires Python 3")

# pylint: disable=wrong-import-position
# as we are doing some version check before importing everything

import asyncio
import email.parser
import email.policy
import importlib
import os
import signal

import common
import config
ResponseError = common.ResponseError

__doc__ = "SCGI Server based on email module for header - content processing"

PATH_PREFIX = config.CONFIG["prefix"]
## 1 MiB Header Limit
MAX_HEAD_LEN = config.CONFIG["maxsize"]["head"]
AVAIL_MOD = {}

async def process_request(
    header: email.message.Message,
    stdin: asyncio.streams.StreamReader,
    stdout: asyncio.streams.StreamWriter
):
    """ Process HTTP request - Router"""
    path = os.path.normpath(
        "DOCUMENT_URI" in header
        and header["DOCUMENT_URI"]
        or header["REQUEST_URI"].split("?",1)[0]
    )
    if path.startswith(PATH_PREFIX):
        path = path[len(PATH_PREFIX):]
    (header.add_header, header.replace_header)["DOCUMENT_URI" in header]("DOCUMENT_URI", path)
    modname = path[1:].split(".",1)[0].split("/",1)[0]
    if path in "/":
        modname = "index"
    if os.path.isfile(modname+".py") or os.path.isdir(modname):
        ## External handler
        if modname not in AVAIL_MOD:
            target = importlib.import_module(modname)
            AVAIL_MOD[modname] = target.main
        target = AVAIL_MOD[modname]
        try:
            await target(header, stdin, stdout)
        except Exception as err: #pylint: disable=broad-except
            if isinstance(err, ResponseError):
                err.write( req = header, stdout = stdout )
            else:
                common.write_email(
                    req = header,
                    stdout = stdout,
                    status = 400,
                    resp = email.message_from_string(
                        "Content-Type: text/plain; charset=utf-8"+str(err),
                        policy = email.policy.HTTP
                    )
                )
            print(type(err))
            print(repr(err))
    else:
        common.write_email(
            req = header,
            stdout = stdout,
            status = 404,
            resp = email.message_from_string(
                "Content-Type: text/plain; charset=utf-8\n\n"
                "File not found: " + path,
                policy = email.policy.HTTP
            )
        )

async def handle(stdin, stdout):
    """ Socket connection handler """
    try:
        try:
            data = await stdin.readuntil(b":")
            data = data[:-1]
            headlen = int(data)
            if headlen > MAX_HEAD_LEN:
                raise ResponseError(431, "Payload head too large")
            data = await stdin.readexactly(headlen+1)
            data = data[:-2]
        except asyncio.LimitOverrunError as err:
            raise ResponseError(431, "Payload too large") from err
        except asyncio.IncompleteReadError as err:
            raise ResponseError(413, "Payload malformed") from err
        except ValueError as err:
            raise ResponseError(400, "Payload malformed") from err
        data = data.split(b"\0")
        data = [data[item << 1:1 + item << 1] for item in range(len(data) >> 1)]
        data = b"\n".join((b": ".join(item) for item in data))
    ## Now we can parse the header
        parser = email.parser.BytesParser(policy = email.policy.default)
        header = parser.parsebytes(data, headersonly=True)
    except ResponseError as err:
        err.write(None, stdout)
        try:
            await stdout.drain()
        except ConnectionError:
            print(str(err))
        await common.close_connection(stdout)
        return
    ## Stop the try here for errors without header
    try:
        if False in (entry in header for entry in (
            "CONTENT_LENGTH",
            "REQUEST_METHOD",
            "REQUEST_URI",
            "HTTP_USER_AGENT",
            "SCGI"
        )) or header["SCGI"] != "1":
            print("\n".join((": ".join(item) for item in header.items())))
            raise ResponseError(400, "Payload head missing value")
        ## Compatibility to Email
        header["Content-Type"] = header.get("content_type")
        ## Header parsed. Now process the entity with the processor.
        await process_request(header, stdin, stdout)
        await stdout.drain()
    except ResponseError as err:
        err.write(header, stdout)
    except ConnectionError:
        print("Error returning request:", header)
    await common.close_connection(stdout)

async def main():
    """ Main function for invocation via cmdline """
    server = await config.CONFIG["server"].start(handle)
    print("Started", config.CONFIG["server"])
    stop_request = asyncio.Event()
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, stop_request.set)
    await stop_request.wait()
    server.close()
    if sys.version_info.minor >= 7:
        await server.wait_closed()
    print("Stopped", config.CONFIG["server"])

if __name__ == "__main__":
    if sys.version_info.minor < 7:
        el = asyncio.get_event_loop()
        el.run_until_complete(main())
        el.close()
    else:
        asyncio.run(main())
