"""Auto-updater for official python.org builds of python."""
import collections
from platform import mac_ver
from re import compile as compile_re
from sys import version_info
from typing import Dict
from typing import Iterable
from typing import Match
from typing import Pattern
from typing import Tuple

import html5lib
import requests
from hyperlink import DecodedURL


def alllinksin(
    u: DecodedURL, e: Pattern[str]
) -> Iterable[Tuple[Match[str], DecodedURL]]:
    """Get all the links in the given URL whose text matches the given pattern."""
    for a in html5lib.parse(
        requests.get(u.to_text()).text, namespaceHTMLElements=False
    ).findall(".//a"):
        match = e.fullmatch(a.text or "")
        if match is not None:
            yield match, u.click(a.attrib["href"])


def main() -> None:
    """Do an update."""
    this_mac_ver = tuple(map(int, mac_ver()[0].split(".")[:2]))
    ver = compile_re(r"(\d+)\.(\d+).(\d+)/")
    macpkg = compile_re("python-(.+)-macosx?(.*).pkg")

    thismajor, thisminor, thismicro, *other = version_info

    # major, minor, micro, macos
    versions: Dict[
        int, Dict[int, Dict[int, Dict[str, DecodedURL]]]
    ] = collections.defaultdict(
        lambda: collections.defaultdict(lambda: collections.defaultdict(dict))
    )

    baseurl = DecodedURL.from_text("https://www.python.org/ftp/python/")

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
