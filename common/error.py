#! /usr/bin/python3

import asyncio
import email.policy
import http

from . import output

__doc__ = "Exceptions"

class ResponseError(Exception):
    " Represent an error to be sent to the client "
    def __init__(self, status: int = 500, reason: str = None):
        super().__init__()
        self.status = status
        self.reason = reason or http.HTTPStatus(status).phrase
    def __repr__(self) -> str:
        return "".join(("<ProcessError code=",str(self.status), " reason=\"",self.reason,"\">"))
    def __str__(self) -> str:
        return " ".join(("Process Error:",str(self.status),self.reason))
    def write(self, req: dict, stdout: asyncio.streams.StreamWriter):
        " Write the ResponseError to stdout "
        output.write_email(
            req, stdout, status = self.status,
            resp = email.message_from_string("\n"+self.reason, policy = email.policy.HTTP)
        )
