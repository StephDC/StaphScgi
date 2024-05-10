#!/usr/bin/python3

import base64
import email.policy
import hashlib
import os

import common

__doc__ = "WebSocket test module"

def calculate_websocket_key(value: str) -> str:
    """ Calculate the Websocket Accept header """
    hasher = hashlib.sha1()
    hasher.update(value.encode("ascii"))
    hasher.update(b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11")
    return base64.b64encode(hasher.digest()).decode("ascii")

class WebSocketData():
    """ Websocket Message object """
    ## Constants for OPCODE
    OPCODE_CONTINUE = 0
    OPCODE_TEXT = 1
    OPCODE_BINARY = 2
    OPCODE_CLOSE = 8
    OPCODE_PING = 9
    OPCODE_PONG = 10

    def __init__(self, rsv: int, opcode: int, data: bytes, masked: bool = False):
        self.rsv = rsv
        self.opcode = opcode
        self.data = data
        self.masked = masked

    def __bytes__(self):
        fin = False
        result = b""
        mask = (b"",os.urandom(4))[self.masked]
        opcode = self.opcode
        data = self.data
        while not fin:
            fin = len(data) < (1<<63)-1
            extend_len = b""
            header = bytearray(2)
            header[0] = (fin << 7) | (self.rsv << 4) | opcode
            header[1] = (self.masked << 7) | (
                len(data) >= (1<<16) and 127
                or len(data) >= 126 and 126
                or len(data)
            )
            if header[1] & 0b1111111 > 125:
                extend_len = min(len(data), (1<<63)-1)
                extend_len = extend_len.to_bytes(2 << (extend_len >= (1<<16)), "big")
            result += b"".join((header, extend_len, mask))
            convdata = bytearray( self.masked and (
                mask * (min(len(data), (1<<63)-1) >> 2)
                + mask[:min(len(data), (1<<63)-1) & 3]
            ) or (min(len(data), (1<<63)-1)))
            for item in range(min(len(data), (1<<63)-1)):
                convdata[item] ^= data[item]
            result += convdata
            data = data[len(convdata):]
            if not fin:
                ## For next segment, set the continuation mark
                mask = os.urandom(4) if self.masked else b""
                opcode = 0
        return result
    def __eq__(self,other):
        return self.rsv == other.rsv and self.opcode == other.opcode and self.data == other.data
    def __str__(self):
        opcode_processes = {
            1: ("TEXT", lambda x: x.decode("UTF-8")),
            2: ("BINARY", str),
            8: ("CLOSE", lambda x: str(x and int.from_bytes(x, "big") or 1005)),
            9: ("PING", str)
        }
        return "".join((
            "<WebSocket rsv=\"",
            str(self.rsv),
            "\" opcode=\"",
            opcode_processes[self.opcode][0] \
                if self.opcode in opcode_processes else str(self.opcode),
            "\" mask=\""+("false","true")[self.masked]+"\">",
            self.opcode in opcode_processes \
                and opcode_processes[self.opcode][1](self.data) or str(self.data),
            "</WebSocket>"
        ))

    @staticmethod
    async def read_websocket(stdin):
        """ Read WebSocket Data """
        not_done = True
        init = True
        data = b""
        while not_done:
            try:
                header = await stdin.readexactly(2)
            except ConnectionError:
                print("Connection closed")
                return None
            not_done = not bool(header[0] & 0b10000000)
            if init:
                rsv = (header[0] & 0b1110000) >> 4
                opcode = header[0] & 0b1111
            size = header[1] & 0b1111111
            if size > 125:
                try:
                    size = await stdin.readexactly(2 << (size & 1))
                except ConnectionError:
                    print("Connection closed")
                    return None
            try:
                mask = None if header[1] & 0b10000000 else await stdin.readexactly(4)
                tmpdata = bytearray(await stdin.readexactly(size))
            except ConnectionError:
                print("Connection closed")
                return None
            if mask:
                for item in range(size):
                    tmpdata[item] ^= mask[item & 3]
            data += tmpdata
            init = False
        return WebSocketData(rsv = rsv, opcode = opcode, data = data, masked = bool(mask))

async def main(header: email.message.Message, stdin, stdout):
    " Main invocation "
    if "HTTP_UPGRADE" not in header or header["HTTP_UPGRADE"] != "websocket":
        common.write_email(
            header,
            stdout,
            status = 400,
            resp = email.message_from_string(
                "Content-Type: text/plain; charset=utf-8\n\nBad request",
                policy = email.policy.HTTP
            )
        )
        return
    common.write_http(
            header,
            stdout,
            status = 101,
            header = {
                "Upgrade": "websocket",
                "Connection": "Upgrade",
                "Sec-Websocket-Accept": calculate_websocket_key(header["HTTP_SEC_WEBSOCKET_KEY"])
            },
            body = b""
    )
    print("WebSocket upgraded")
    await stdout.drain()
    process_next = True
    while process_next:
        data = await WebSocketData.read_websocket(stdin)
        if data is None:
            break
        print(data)
        if data.opcode == 1:
            ## Text
            stdout.write(bytes(data))
        elif data.opcode == 9:
            ## Ping - Pong
            data.opcode = 10
            stdout.write(bytes(data))
        elif data.opcode == 8:
            ## Close
            stdout.write(bytes(data))
            process_next = False
        await stdout.drain()
    print("WebSocket closed")
