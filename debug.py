#!/usr/bin/python3
import common
ResponseError = common.ResponseError

__doc__ = "SCGI Debugger"

async def main(
    header: email.message.Message,
    stdin: asyncio.streams.StreamReader,
    stdout: asyncio.streams.StreamWriter
):
    """ Process HTTP request """
    common.write_email(
            req = header,
            stdout = stdout,
            resp = email.message_from_string(
                "Content-Type: text/plain; charset=utf-8\n\nHeaders:\n",
                policy = email.policy.HTTP
            )
    )
    stdout.write(bytes(header))
    stdout.write(b"\n\nBody:\n")
    body = await common.parse_data(header, stdin)
    if isinstance(body, dict):
        stdout.write(repr(body).encode("utf-8"))
    else:
        stdout.write(b"Unsupported body format")
    stdout.write(b"\n")
