#! /usr/bin/python3

import configparser
import common
__doc__ = "Configuration file loader for StaphSCGI."

CONFIG={}

def load(path: str = "config.ini"):
    "Load config file and apply to common"
    config = configparser.ConfigParser()
    config.read(path)

    ## Server Definitions
    if config["Server"]["type"] == "net":
        server = common.server.NetServer(
            host = config["Server"]["host"],
            port = config["Server"].getint("port")
        )
    elif config["Server"]["type"] == "unix":
        server = common.server.UnixServer( path = config["Server"]["path"] )
    else:
        raise NotImplementedError()
    CONFIG["server"] = server

    ## Path Prefix - Set the path prefix when accessed through HTTP
    CONFIG["prefix"] = config["Path"]["prefix"]
    CONFIG["maxsize"] = {
        "head": config["Tuning"].getint("max head size"),
        "body": config["Tuning"].getint("max body size")
    }
    common.field.MAX_CONTENT_LENGTH = CONFIG["maxsize"]["body"]

load()
if __name__ == "__main__":
    print(CONFIG)
