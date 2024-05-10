#! /usr/bin/python3

import asyncio

__doc__ = "Server Config Definitions for starting"

class ServerBase():
    """ Server Interface that provides start method """
    def __str__(self):
        return repr(self)[1:-3]
    def start(self, client_connected_cb, **kwargs):
        "Start server and return coroutine - Must be implemented"
        raise NotImplementedError()

class UnixServer(ServerBase):
    "Unix Server"
    def __init__(self, path: str):
        self.path = path
    def __repr__(self) -> str:
        return '<UnixServer path="'+self.path+'" />'
    def start(self, client_connected_cb, **kwargs):
        "Start server and return coroutine"
        return asyncio.start_unix_server(client_connected_cb, self.path, **kwargs)

class NetServer(ServerBase):
    "Net Server"
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
    def __repr__(self) -> str:
        return '"'.join((
            '<NetServer host=',
            self.host,
            ' port=',
            str(self.port),
            ' />'
        ))
    def start(self, client_connected_cb, **kwargs):
        "Start server and return coroutine"
        return asyncio.start_server(client_connected_cb, self.host, self.port & 65535, **kwargs)
