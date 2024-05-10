#! /usr/bin/python3

import asyncio
import email.policy
import json
import urllib.parse as up

from . import error

__doc__ = "FieldStorage for user input"
MAX_CONTENT_LENGTH = 1<<20

class CGIFile(email.message.EmailMessage):
    " Wrapper for CGI File Messages that behaves more like a file "
    def __len__(self):
        return len(self.get_payload(decode=True))
    def __repr__(self):
        return "".join((
            '<file name="',
            self["content-disposition"].params.get("name"),
            '" filename="',
            self.get_filename() or "None",
            '" size=',
            str(len(self)),
            ' />'
        ))

def process_multipart_formdata(stdin: email.message.Message) -> dict:
    "Format conversion to make multipart a regular message"
    result = {}
    for item in stdin.get_payload():
        contdisp = item["content-disposition"]
        if contdisp.params.get("name") is None:
            ## Not an entry to the form
            continue
        if item.get_filename() is None and item.get_content_type() == "text/plain":
            ## A text field
            try:
                payload = item.get_payload(decode=True).decode("utf-8")
            except UnicodeDecodeError:
                ## Cannot decode
                continue
            result[contdisp.params.get("name")] = payload
        elif item.get_content_maintype() == "multipart":
            ## Layered multipart/form-data
            payload = []
            for subitem in item.get_payload():
                if subitem.get_content_maintype() == "multipart":
                    continue # Too many layers of multipart. Skip it.
                payload.append(
                    item if isinstance(item, CGIFile) \
                        else email.message_from_string(str(item), CGIFile, policy=email.policy.HTTP)
                )
            if payload:
                result[contdisp.params.get("name")] = payload
        else:
            ## This is a single attached file. Store the file content.
            result[contdisp.params.get("name")] = item if isinstance(item, CGIFile) \
                else email.message_from_string(str(item),CGIFile, policy=email.policy.HTTP)
    return result

async def parse_data(header: email.message.Message, stdin: asyncio.streams.StreamReader) -> dict:
    """Parse data from HTTP request into dict"""
    try:
        if int(header["CONTENT_LENGTH"]) > MAX_CONTENT_LENGTH:
            raise error.ResponseError(413)
    except ValueError as err:
        raise error.ResponseError(400, "Bad content length") from err

    data = {}

    if "QUERY_STRING" in header:
        data = {item[0]: item[1][-1] for item in up.parse_qs(header["QUERY_STRING"]).items()}

    if header["REQUEST_METHOD"].lower() in ("get","head","options"):
        # We are not expecting a body. Return.
        return data
    if header.get_content_type() == "application/x-www-form-urlencoded":
        data.update({item[0]: item[1][-1] for item in up.parse_qs(
            (await stdin.readexactly(int(header["CONTENT_LENGTH"]))).decode("utf-8")
        ).items()})
    elif header.get_content_type() == "application/json":
        data.update(json.loads(
            (await stdin.readexactly(int(header["CONTENT_LENGTH"]))).decode("utf-8")
        ))
    elif header.get_content_type() == "multipart/form-data":
        ## Now we need a really complicated multipart/form-data parser
        data = process_multipart_formdata(email.message_from_bytes(b"\n\n".join((
            b"Content-Type: " + header["CONTENT_TYPE"].encode("ascii"),
            await stdin.readexactly(int(header["CONTENT_LENGTH"]))
        )), policy = email.policy.HTTP))
    return data

def get_max_size() -> int:
    return MAX_CONTENT_LENGTH
