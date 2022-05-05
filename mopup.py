import requests
import html5lib
from re import compile as compile_re
import collections
from hyperlink import DecodedURL
from typing import Tuple, Iterable, re, Match
from sys import version_info
from platform import mac_ver


this_mac_ver = tuple(map(int, mac_ver()[0].split(".")[:2]))
ver = compile_re("(\d+)\.(\d+).(\d+)/")
macpkg = compile_re("python-(.+)-macosx?(.*).pkg")

thismajor, thisminor, thismicro, *other = version_info

# major, minor, micro, macos
versions = collections.defaultdict(
    lambda: collections.defaultdict(lambda: collections.defaultdict(dict))
)

baseurl = DecodedURL.from_text("https://www.python.org/ftp/python/")


def alllinksin(u: DecodedURL, e: re) -> Iterable[Tuple[Match, DecodedURL]]:
    for a in html5lib.parse(
        requests.get(u.to_text()).text, namespaceHTMLElements=False
    ).findall(".//a"):
        match = e.fullmatch(a.text)
        if match is not None:
            yield match, u.click(a.attrib["href"])


for eachver, suburl in alllinksin(baseurl, ver):
    major, minor, micro = map(int, eachver.groups())
    print("fetching versions for", major, minor, micro)
    for eachmac, pkgdl in alllinksin(suburl, macpkg):
        pyver, macver = eachmac.groups()
        if pyver == f"{major}.{minor}.{micro}":
            versions[major][minor][micro][macver] = pkgdl

import pprint

pprint.pprint(versions)
newmicro = max(versions[thismajor][thisminor].keys())
print("new micro-version:", thismajor, thisminor, newmicro)
available_mac_vers = versions[thismajor][thisminor][newmicro].keys()
best_available_mac = max(
    available_mac_ver
    for available_mac_ver in available_mac_vers
    if this_mac_ver >= tuple(int(x) for x in available_mac_ver.split("."))
)

print(
    "update",
    "needed" if newmicro > thismicro else "not needed",
    "from",
    versions[thismajor][thisminor][newmicro][best_available_mac],
)
