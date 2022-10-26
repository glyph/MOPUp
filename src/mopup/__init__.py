"""Auto-updater for official python.org builds of python."""
import collections
from os import makedirs
from os import rename
from os import rmdir
from os import unlink
from os.path import expanduser
from os.path import join as pathjoin
from platform import mac_ver
from re import compile as compile_re
from subprocess import run  # noqa: S404
from sys import version_info
from typing import Dict
from typing import Iterable
from typing import Match
from typing import Pattern
from typing import Tuple
from uuid import uuid4

import html5lib
import requests
from hyperlink import DecodedURL
from rich.progress import Progress


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


def main(interactive: bool, force: bool, minor_upgrade: bool, dry_run: bool) -> None:
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
        if minor != thisminor and not minor_upgrade:
            continue
        for eachmac, pkgdl in alllinksin(suburl, macpkg):
            pyver, macver = eachmac.groups()
            if pyver == f"{major}.{minor}.{micro}":
                versions[major][minor][micro][macver] = pkgdl

    newminor = max(versions[thismajor].keys())
    newmicro = max(versions[thismajor][newminor].keys())
    available_mac_vers = versions[thismajor][newminor][newmicro].keys()
    best_available_mac = max(
        available_mac_ver
        for available_mac_ver in available_mac_vers
        if this_mac_ver >= tuple(int(x) for x in available_mac_ver.split("."))
    )

    update_needed = (newminor, newmicro) > (thisminor, thismicro)
    download_url = versions[thismajor][newminor][newmicro][best_available_mac]
    print(
        "update",
        "needed" if update_needed else "not needed",
        "from",
        download_url,
    )

    if dry_run or not (update_needed or force):
        return

    finalname = do_download(download_url)
    if interactive:
        argv = ["/usr/bin/open", "-b", "com.apple.installer", finalname]
    else:
        print("Enter your administrative password to run the update:")
        argv = [
            "/usr/bin/sudo",
            "/usr/sbin/installer",
            "-pkg",
            finalname,
            "-target",
            "/",
        ]
    run(argv)  # noqa: S603
    print("Complete.")


def do_download(download_url: DecodedURL) -> str:
    """
    Download the given URL into the downloads directory.

    Returning the path when successful.
    """
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
        except BaseException:
            unlink(contentname)
            rmdir(partialdir)
            raise
        else:
            rmdir(partialdir)
            return finalname
