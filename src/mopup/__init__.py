"""Auto-updater for official python.org builds of python."""
import collections

from subprocess import run
from rich.progress import Progress
from os import unlink, rename, makedirs, rmdir
from os.path import expanduser, join as pathjoin
from uuid import uuid4
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


def main(interactive: bool, force: bool) -> None:
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
        if major != thismajor:
            continue
        if minor != thisminor:
            continue
        for eachmac, pkgdl in alllinksin(suburl, macpkg):
            pyver, macver = eachmac.groups()
            if pyver == f"{major}.{minor}.{micro}":
                versions[major][minor][micro][macver] = pkgdl

    newmicro = max(versions[thismajor][thisminor].keys())
    available_mac_vers = versions[thismajor][thisminor][newmicro].keys()
    best_available_mac = max(
        available_mac_ver
        for available_mac_ver in available_mac_vers
        if this_mac_ver >= tuple(int(x) for x in available_mac_ver.split("."))
    )

    update_needed = newmicro > thismicro
    download_url = versions[thismajor][thisminor][newmicro][best_available_mac]
    print(
        "update",
        "needed" if update_needed else "not needed",
        "from",
        download_url,
    )

    if not (update_needed or force):
        return

    basename = download_url.path[-1]
    partial = basename + ".mopup-partial"
    downloads_dir = expanduser("~/Downloads/")
    partialdir = pathjoin(downloads_dir, partial)
    contentname = pathjoin(partialdir, f"{uuid4()}.content")
    finalname = pathjoin(downloads_dir, basename)

    with requests.get(download_url.to_uri().to_text(), stream=True) as response:
        response.raise_for_status()
        try:
            makedirs(partialdir, exist_ok=True)
            total_size = int(response.headers["content-length"])
            with open(contentname, "wb") as f:
                with Progress() as progress:
                    task = progress.add_task(
                        f"Downloading {basename}...", total=total_size
                    )
                    for chunk in response.iter_content(chunk_size=8192):
                        progress.update(task, advance=len(chunk))
                        f.write(chunk)
            print(".")
            rename(contentname, finalname)
        except:
            unlink(contentname)
            rmdir(partialdir)
            raise
        else:
            rmdir(partialdir)

    if interactive:
        print("Enter your administrative password to run the update:")
        run(["open", "-b", "com.apple.installer", finalname])
    else:
        run(["sudo", "installer", "-pkg", finalname, "-target", "/"])
    print("Complete.")
