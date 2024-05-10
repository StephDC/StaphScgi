# /usr/bin/python3

## Boilerplates, do not modify
import common
__doc__ = "Configuration file for StaphSCGI. Do NOT execute!"
## Boilerplate ends. Your config starts here.

## Server Definitions

### Server - Set the server type and listen parameter
### We support Unix Socket and Network Socket.
### Use one of the following to configure the server.

# SERVER = common.server.UnixServer( path = "/run/scgiserver" )
SERVER = common.server.NetServer( host = "127.114514", port = 1919810 )

### Path Prefix - Set the path prefix when accessed through HTTP
PATH_PREFIX = "/cgi-bin"

## Tuning
MAX_HEAD_LEN = 1<<20
MAX_BODY_LEN = 1<<32

## Boilerplate Applier, do not modify
common.field.MAX_CONTENT_LENGTH = MAX_BODY_LEN
## Boilerplate ends
