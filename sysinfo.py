#!/usr/bin/python3

import email.policy
import geoip2.database
import ipaddress
import subprocess

import common

HEADER = """<!DOCTYPE html>
<html>
\t<head>
\t\t<meta charset="utf-8" />
\t\t<title>Staph Status</title>
\t</head>
\t<body>
\t\t<h1>Server Status</h1>"""

USER_INFO = "\t\t<h1>Your Info</h1>"

FOOTER = """\t</body>
</html>"""

MY_NETWORK = {
    ipaddress.ip_network("10.127.8.160/27"),
    ipaddress.ip_network("fd10:127:7::/48"),
    ipaddress.ip_network("10.126.7.0/24")
}

TRUSTED_NETWORK = {
    ipaddress.ip_network("10.127.0.0/16"),
    ipaddress.ip_network("172.20.0.0/22"),
    ipaddress.ip_network("fd10:127::/32"),
    ipaddress.ip_network("fd42::/16")
}

DATABASE_ATTRIBUTION = "\n* IP Geolocation by DB-IP <https://db-ip.com>"

def geoip2_asn(result) -> str:
    if result is None:
        return "GeoIP ASN Edition: Unknown ASN"
    return "GeoIP ASN Edition: AS"+str(result.autonomous_system_number)+" "+result.autonomous_system_organization

def locale_fallback (info: dict, locale: str, fallback: str = "en"):
    """ Handle locale fallback """
    return locale in info and info[locale] or fallback in info and info[fallback] or None

def geoip2_city(result, locale: str = "en") -> str:
    if result is None:
        return "GeoIP City Edition, Rev 2: Unknown location"
    record = (
        result.country.iso_code,
        result.subdivisions and result.subdivisions[0].iso_code or None,
        result.subdivisions and locale_fallback(result.subdivisions[0].names, locale) or None,
        locale_fallback(result.city.names, locale),
        result.postal.code,
        result.location.latitude,
        result.location.longitude
    )
    return "GeoIP City Edition, Rev 2: "+", ".join((str(item) for item in record if item is not None))

def get_geoip(addr: str) -> str:
    """ Get GeoIP Information """
    numip = ipaddress.ip_address(addr)
    if numip.is_loopback or True in (numip in item for item in MY_NETWORK):
        ## Request originated from my own network
        return "Welcome, our privileged StaphNet user!"
    elif True in (numip in item for item in TRUSTED_NETWORK):
        ## Reqest originated from a trusted peer
        return "Welcome, our privileged peering member!"
    elif numip.is_private:
        ## Request originated from a private address
        return "Welcome to StaphNet, my unknown friend!"
    ## Otherwise we may lookup the user with db
    with geoip2.database.Reader('/usr/share/GeoIP/city.mmdb') as reader:
        try:
            city = reader.city(addr)
        except geoip2.errors.AddressNotFoundError:
            city = None
    with geoip2.database.Reader('/usr/share/GeoIP/asn.mmdb') as reader:
        try:
            asn = reader.asn(addr)
        except geoip2.errors.AddressNotFoundError:
            asn = None
    return "".join((
        geoip2_city(city),"\n",
        geoip2_asn(asn),
        (asn or city) and DATABASE_ATTRIBUTION or ""
    ))

def create_response(header: dict) -> bytes:
    """ Create HTML Response """
    sysinfo = "\t\t<pre>"+subprocess.check_output("uptime", encoding="utf-8").strip()+"</pre>\n"
    sysinfo += "\t\t<pre>"+subprocess.check_output(("free", "-h"), encoding="utf-8")+"</pre>\n"
    userinfo = "".join((
        "<pre>User-Agent:\t",
        header["HTTP_USER_AGENT"],
        "</pre>\n",
        "<pre>Request-Addr:\t",
        header["REMOTE_ADDR"], ":", header["REMOTE_PORT"], "\n",
        "Proxy:\t\t",
        "HTTP_X_FORWARDED_FOR" in header and header["HTTP_X_FORWARDED_FOR"] or "No transparent proxy",
        "</pre>\n"
    ))
    ipinfo = "\t\t<pre>"+get_geoip(
        "HTTP_X_FORWARDED_FOR" in header and header["HTTP_X_FORWARDED_FOR"] or header["REMOTE_ADDR"]
    )+"</pre>\n"

    return "".join((HEADER, sysinfo, USER_INFO, userinfo, ipinfo, FOOTER)).encode("utf-8")

async def main(header: email.message.Message, _, stdout):
    """ Main invocation """
    common.write_email(
        req = header,
        stdout = stdout,
        resp = email.message_from_bytes(
            b"Content-Type: text/html; charset=utf-8\n\n" + create_response(header),
            policy=email.policy.HTTP
        )
    )
