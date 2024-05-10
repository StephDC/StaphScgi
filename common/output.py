#! /usr/bin/python3

import asyncio
import email.policy
import http

__doc__ = "Output Handler"

def ignore_err(err):
    "Use this to ignore the error"
    def wrapper(fun):
        def inner(*args, **kwargs):
            try:
                fun(*args, **kwargs)
            except err:
                print("Failed to write to the output")
        return inner
    return wrapper

@ignore_err(ConnectionError)
def write_http(
    req: dict,
    stdout: asyncio.streams.StreamWriter,
    status: int = 200,
    header: dict = None,
    body: bytes = b""
):
    " Write the response to stdout StreamWriter "
    ## Sanity Check
    ## For writes occurred before the header is parsed
    if req is None:
        req = {"REQUEST_METHOD": "GET"}
    if header is None:
        header = {}
    if body and "Content-Type" not in header:
        header["Content-Type"] = "text/plain; charset=utf-8"

    ## Status Line
    stdout.write(b" ".join((
        b"Status:",
        str(status).encode("ascii"),
        http.HTTPStatus(status).phrase.encode("ascii")
    )) + b"\r\n")
    ## HTTP Header
    stdout.write(b"\r\n".join((
        item[0].encode("ascii") + b": " + item[1].encode("ascii") for item in header.items()
    )))
    stdout.write(b"\r\n\r\n")
    ## HTTP Body
    stdout.write(body)

@ignore_err(ConnectionError)
def write_email(
    req: email.message.Message,
    stdout: asyncio.streams.StreamWriter,
    status: int = 200,
    resp: email.message.Message = None
):
    " Write the response to stdout StreamWriter "
    ## Sanity Check
    ## For writes occurred before the header is parsed
    if req is None:
        req = {"REQUEST_METHOD": "GET"}
    ## For blank resp
    if resp is None:
        resp = email.message_from_string("\n", policy = email.policy.HTTP)
    if resp.get_payload() and resp.get("content-type") is None:
        resp["Content-Type"] = "text/plain; charset=utf-8"
    if resp.get("x-server") is None:
        resp["X-Server"] = "StaphScgi-Email v0.1"

    ## Status Line
    stdout.write(b" ".join((
        b"Status:",
        str(status).encode("ascii"),
        http.HTTPStatus(status).phrase.encode("ascii")
    )) + b"\r\n")
    ## HTTP Response
    stdout.write(bytes(resp))
