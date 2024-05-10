#!/usr/bin/python3.11

import sys

from . import error
from . import server
from . import field
from . import output

## 16M Max content
MAX_CONTENT_LENGTH = 1048576 << 4

__doc__ = "Common functionalities shared by scgi server"

async def close_connection(stdout):
    "Close server connection"
    try:
        stdout.close()
        if sys.version_info.minor >= 7:
            await stdout.wait_closed()
    except ConnectionError:
        print("Connection Error when closing connection.")

## Rebinding

ResponseError = error.ResponseError
write_email = output.write_email
parse_data = field.parse_data
