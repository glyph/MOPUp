"""Auto-updater for official python.org builds of python."""

from __future__ import annotations

import collections
import json
import re
import sys
from os import geteuid
from os.path import lexists  # Path.exists(follow_symlinks=False) was only added in 3.12
from pathlib import Path
from platform import mac_ver
from plistlib import dumps as dumpplist
from plistlib import loads as loadplist
from re import compile as compile_re
from subprocess import PIPE, run  # noqa: S404
from sys import argv, executable, version_info
from tempfile import NamedTemporaryFile
from typing import cast, Dict, Iterable, Iterator, Match, Pattern, TypedDict
from uuid import uuid4

import html5lib
import requests
from hyperlink import DecodedURL
from packaging.version import Version, parse
from rich.progress import Progress


PKG_RE = re.compile(r"^org\.python\.Python\.(?P<name>.*)-(?P<version>\d+\.\d+)$")

PkgFileInfo = TypedDict(
    "PkgFileInfo",
    {
        "pkgid": "str",
        "pkg-version": "str",
        "uid": int,
        "gid": int,
        "mode": int,
        "install-time": int,
    },
)
PkgInfo = TypedDict(
    "PkgInfo",
    {
        "pkgid": "str",
        "pkg-version": "str",
        "volume": "str",
        "install-location": "str",
        "paths": Dict[str, PkgFileInfo],
        "install-time": int,
        "receipt-plist-version": int,
    },
)


def alllinksin(
    u: DecodedURL, e: Pattern[str]
) -> Iterable[tuple[Match[str], DecodedURL]]:
    """Get all the links in the given URL whose text matches the given pattern."""
    for a in html5lib.parse(
        requests.get(u.to_text(), timeout=30).text, namespaceHTMLElements=False
    ).findall(".//a"):
        match = e.fullmatch(a.text or "")
        if match is not None:
            yield match, u.click(a.attrib["href"])


def choicechanges(pkgfile: str) -> str:
    """
    Compute the choice-changes XML for a given package based on what is
    currently installed.
    """

    all_installed = set(
        run(  # noqa: S603
            [
                "/usr/sbin/pkgutil",
                "--pkgs",
            ],
            stdout=PIPE,
        )
        .stdout.decode()
        .split("\n")
    )
    dicts = loadplist(
        run(  # noqa: S603
            [
                "/usr/sbin/installer",
                "-showChoiceChangesXML",
                "-pkg",
                pkgfile,
            ],
            stdout=PIPE,
        ).stdout
    )
    for each in dicts:
        if each["choiceAttribute"] == "selected":
            choice_id = each["choiceIdentifier"]
            setting = int(choice_id in all_installed)
            if setting:
                print("selecting choice", each["choiceIdentifier"])
                each["attributeSetting"] = setting
    return dumpplist(dicts).decode()


def main(interactive: bool, force: bool, minor_upgrade: bool, dry_run: bool) -> None:
    """Do an update."""
    _ensure_sudo_if_needed(dry_run)

    this_mac_ver = tuple(map(int, mac_ver()[0].split(".")[:2]))
    ver = compile_re(r"(\d+)\.(\d+).(\d+)/")
    macpkg = compile_re(r"python-(\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?)-macosx?(\d+).pkg")

    thismajor, thisminor, thismicro, releaselevel, serial = version_info
    level = {
        "alpha": "a",
        "beta": "b",
        "candidate": "rc",
        "final": "",
    }[releaselevel]

    thispkgver = Version(
        f"{thismajor}.{thisminor}.{thismicro}" + (f".{level}{serial}" if level else "")
    )

    # {macos, major, minor: [(Version, URL)]}
    # major, minor, micro, macos: [(version, URL)]
    versions: dict[
        int, dict[int, dict[int, dict[str, list[tuple[Version, DecodedURL]]]]]
    ] = collections.defaultdict(
        lambda: collections.defaultdict(
            lambda: collections.defaultdict(lambda: collections.defaultdict(list))
        )
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
            fullversion = parse(pyver)
            if fullversion.pre and not thispkgver.pre:
                continue
            if (
                fullversion.major,
                fullversion.minor,
                fullversion.micro,
            ) == (
                major,
                minor,
                micro,
            ):
                versions[major][minor][micro][macver].append((fullversion, pkgdl))

    newminor = max(versions[thismajor].keys())
    newmicro = max(versions[thismajor][newminor].keys())
    available_mac_vers = versions[thismajor][newminor][newmicro].keys()
    best_available_mac = max(
        available_mac_ver
        for available_mac_ver in available_mac_vers
        if this_mac_ver >= tuple(int(x) for x in available_mac_ver.split("."))
    )

    download_urls = versions[thismajor][newminor][newmicro][best_available_mac]

    best_ver, download_url = sorted(download_urls, reverse=True)[0]

    print(f"this version: {thispkgver}; new version: {best_ver}")
    update_needed = best_ver > thispkgver

    print(
        "update",
        "needed" if update_needed else "not needed",
        "from",
        download_url,
    )

    if dry_run or not (update_needed or force):
        return

    finalname = do_download(download_url)
    with NamedTemporaryFile(mode="w", suffix=".plist") as tf:
        if interactive:
            argv = ["/usr/bin/open", "-b", "com.apple.installer", finalname]
        else:
            tf.write(choicechanges(finalname))
            tf.flush()
            # We already have sudo from _ensure_sudo_if_needed
            argv = [
                "/usr/sbin/installer",
                "-applyChoiceChangesXML",
                tf.name,
                "-pkg",
                finalname,
                "-target",
                "/",
            ]
        run(argv)  # noqa: S603
    print("Complete.")


def list_installed() -> None:
    """List all Python versions installed with official Python.org installers."""
    version_executables: list[tuple[Version, str, Path]] = []
    for pkg, _short_name, version in _find_python_packages():
        try:
            plist_data = _get_package_metadata_json(pkg)
        except Exception as e:
            print(f"Warning: {e}")
            continue

        location = plist_data.get("install-location", "")
        volume = plist_data.get("volume", "/")
        paths = plist_data.get("paths", {})
        if not location:
            continue

        base_path = Path(volume) / location
        exe_paths = [
            f"Versions/{version}/bin/python{version}t",
            f"Versions/{version}/bin/python{version}",
        ]
        for exe_path in exe_paths:
            exe_meta = paths.get(exe_path, _empty_pkgfileinfo(pkg))
            is_executable = exe_meta.get("mode", 0) & 0o111
            if is_executable:
                version_executables.append((version, pkg, base_path / exe_path))
                break

    version_executables.sort()

    for version, pkg, python_exe in version_executables:
        exact_version = None
        if python_exe.is_file():
            version_result = run(  # noqa: S603
                [str(python_exe), "-c", "import sys; print(sys.version)"],
                capture_output=True,
                text=True,
            )
            if version_result.returncode == 0:
                exact_version = version_result.stdout.split(" ", 1)[0]
        if exact_version:
            print(f"{exact_version:<12}{pkg:<44}{python_exe}")
        else:
            print(f"{version:<12}{pkg:<44}")


def uninstall(
    *,
    minor_release_version: str,
    dry_run: bool = False,
    interactive: bool = False,
    force: bool = False,
) -> None:
    """
    Uninstall a specific Python version from the system.

    `minor_release_version` is a string like "3.13". If `dry_run` is True, only show
    what would be removed without actually removing. If `interactive` is True, ask for
    confirmation before proceeding. If `force` is True, remove even if extra files are
    present.
    """
    _ensure_sudo_if_needed(dry_run)
    version = Version(minor_release_version)

    packages = []
    packages = [p[0] for p in _find_python_packages(version)]

    if not packages:
        print(f"No Python {minor_release_version} installation found.")
        return

    print(f"Found Python {minor_release_version} packages:")
    for pkg in packages:
        print(f"  - {pkg}")

    all_files, all_dirs, package_root_dirs = _collect_package_files(packages)

    if not all_files and not all_dirs:
        print(f"No files found for Python {minor_release_version}.")
        return

    ok_to_proceed, acceptable_extras = _check_extra_files(all_files, version, force)
    if not ok_to_proceed:
        return

    # Add acceptable extra files to the removal list
    all_files_to_remove = all_files | acceptable_extras

    # Also collect parent directories of the acceptable extras
    extra_dirs = set()
    for extra_file in acceptable_extras:
        parent = extra_file.parent
        while parent and parent not in all_dirs and parent not in extra_dirs:
            # Only add if it's within our check directories (version-specific dirs)
            # Use the actual check directories from package files instead of hardcoding
            if any(
                str(parent).startswith(str(pkg_dir)) for pkg_dir in package_root_dirs
            ):
                extra_dirs.add(parent)
            parent = parent.parent

    all_dirs_to_remove = all_dirs | extra_dirs

    if not dry_run and interactive:
        print(
            f"\nThis will remove {len(all_files_to_remove)} files"
            f" and {len(all_dirs_to_remove)} directories."
        )
        confirmation = input("Are you sure? Type 'yes' to continue: ")
        if confirmation.lower() != "yes":
            print("Uninstall cancelled.")
            return

    remove = "Would be removing" if dry_run else "Removing"
    removed = "Would have removed" if dry_run else "Removed"
    failed = "Would have failed" if dry_run else "Failed"

    print(f"\n{remove} {len(all_files_to_remove)} files...")
    removed_files, failed_files = _remove_files(all_files_to_remove, dry_run)
    print(f"{removed} {len(removed_files)} files.")

    if failed_files:
        print(f"{failed} to remove {len(failed_files)} files:")
        for file_path, error in failed_files.items():
            print(f"  - {file_path}: {error}")

    print(f"{remove} {len(all_dirs_to_remove)} directories...")
    removed_dirs, failed_dirs = _remove_directories(
        all_dirs_to_remove, dry_run, removed_files=removed_files
    )
    print(f"{removed} {len(removed_dirs)} directories.")

    if failed_dirs:
        print(f"{failed} to remove {len(failed_dirs)} directories:")
        for dir_path, error in failed_dirs.items():
            print(f"  - {dir_path}: {error}")

    _forget_packages(packages, dry_run)

    if dry_run:
        print(
            f"\nDry run complete."
            f" Python {minor_release_version} would be uninstalled."
        )
    else:
        print(f"\nPython {minor_release_version} has been uninstalled.")


def do_download(download_url: DecodedURL) -> str:
    """
    Download the given URL into the downloads directory.

    Returning the path when successful.
    """
    basename = download_url.path[-1]
    partial = basename + ".mopup-partial"
    downloads_dir = Path.home() / "Downloads"
    partialdir = downloads_dir / partial
    contentname = partialdir / f"{uuid4()}.content"
    finalname = downloads_dir / basename

    with requests.get(
        download_url.to_uri().to_text(), stream=True, timeout=30
    ) as response:
        response.raise_for_status()
        try:
            partialdir.mkdir(parents=True, exist_ok=True)
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
            contentname.rename(finalname)
        except BaseException:
            contentname.unlink(missing_ok=True)
            partialdir.rmdir()
            raise
        else:
            partialdir.rmdir()
            return str(finalname)


def _ensure_sudo_if_needed(dry_run: bool) -> None:
    """Ensure we have sudo privileges if needed, or relaunch with sudo."""
    is_root = geteuid() == 0

    # If not root and not dry_run, relaunch with sudo
    if not is_root and not dry_run:
        # Check if sudo is already active
        sudo_check = run(  # noqa: S603
            ["/usr/bin/sudo", "-nv"],
            capture_output=True,
        )

        # If sudo is not active, enable it
        if sudo_check.returncode != 0:
            print("Enter your administrative password to uninstall:")
            result = run(["/usr/bin/sudo", "-v"])  # noqa: S603
            if result.returncode != 0:
                print("Failed to obtain administrative privileges.")
                sys.exit(1)

        # Relaunch ourselves with sudo
        cmd = ["/usr/bin/sudo", executable, "-BI"] + argv
        result = run(cmd, cwd="/")  # noqa: S603

        if sudo_check.returncode != 0:
            # Kill sudo session after completion if we enabled it
            run(["/usr/bin/sudo", "-k"])  # noqa: S603
            sys.exit(result.returncode)


def _get_package_metadata_json(pkg: str) -> PkgInfo:
    """
    Get package metadata as JSON dictionary.

    Raises an exception if the package metadata cannot be retrieved or parsed.
    """
    # Export package info as plist
    plist_result = run(  # noqa: S603
        ["/usr/sbin/pkgutil", "--export-plist", pkg],
        capture_output=True,
    )

    if plist_result.returncode != 0:
        error_msg = (
            plist_result.stderr.decode() if plist_result.stderr else "Unknown error"
        )
        raise RuntimeError(f"Failed to get pkgutil plist for {pkg}: {error_msg}")

    # Convert plist XML to JSON using plutil
    json_result = run(  # noqa: S603
        ["/usr/bin/plutil", "-convert", "json", "-o", "-", "-"],
        input=plist_result.stdout,
        capture_output=True,
    )

    if json_result.returncode != 0:
        error_msg = (
            json_result.stderr.decode() if json_result.stderr else "Unknown error"
        )
        raise RuntimeError(f"Failed to convert plist to JSON for {pkg}: {error_msg}")

    return cast(PkgInfo, json.loads(json_result.stdout))


def _find_python_packages(
    version: Version | None = None,
) -> Iterator[tuple[str, str, Version]]:
    """Generate (full pkg name, short name, version) for installed Pythons.

    If `version` is given, only the packages matching that version will be returned.
    """

    if version is not None:
        if len(version.release) != 2 or version.pre or version.post:
            raise ValueError(
                f"Invalid version '{version}', expected 'major.minor' (like '3.13')"  # noqa: B907
            )

    result = run(  # noqa: S603
        ["/usr/sbin/pkgutil", "--pkgs"],
        stdout=PIPE,
        text=True,
    )

    if result.returncode != 0:
        error_msg = result.stderr if result.stderr else "Unknown error"
        raise RuntimeError(f"Failed to list packages with pkgutil: {error_msg}")

    for pkg in result.stdout.strip().split("\n"):
        if match := PKG_RE.match(pkg):
            short_name = match["name"]
            actual_version = Version(match["version"])
            if version is None or version == actual_version:
                yield pkg, short_name, actual_version


def _collect_package_files(
    packages: list[str],
) -> tuple[set[Path], set[Path], set[Path]]:
    """Collect all files and directories from packages."""
    all_files: set[Path] = set()
    all_dirs: set[Path] = set()
    package_root_dirs: set[Path] = set()

    # Extract version from package names (e.g. "org.python.Python.PythonFramework-3.13")
    version = None
    for pkg in packages:
        if "-" in pkg:
            version = pkg.split("-")[-1]
            break

    for pkg in packages:
        try:
            plist_data = _get_package_metadata_json(pkg)
        except Exception as e:
            print(f"Warning: {e}")
            continue

        # Get install location and volume
        location = plist_data.get("install-location", "")
        volume = plist_data.get("volume", "/")

        if not location:
            continue

        base_path = Path(volume) / location
        package_root_dirs.add(base_path)

        # Only add the base path to dirs to remove if it's Python-specific
        # Don't add system directories like /usr/local/bin or /Applications
        base_path_str = str(base_path)
        if version and ("Python" in base_path_str or version in base_path_str):
            all_dirs.add(base_path)

        # Process all paths in the package
        paths = plist_data.get("paths", {})
        for relative_path in paths:
            full_path = base_path / relative_path

            if full_path.exists():
                if full_path.is_file() or full_path.is_symlink():
                    all_files.add(full_path)
                elif full_path.is_dir():
                    all_dirs.add(full_path)

    return all_files, all_dirs, package_root_dirs


def _find_lib_python_files(
    check_path: Path, version: Version, abiflags: str
) -> set[Path]:
    ignore_files: set[Path] = set()
    lib_python = check_path / "lib" / f"python{version}{abiflags}"
    site_packages = lib_python / "site-packages"
    ensurepip_bundled = lib_python / "ensurepip" / "_bundled"

    if site_packages.is_dir():
        for item in site_packages.glob("*.dist-info"):
            record_file = item / "RECORD"
            try:
                lines = record_file.read_text().splitlines()
            except Exception as exc:
                print(f"Warning: can't read {record_file}: {exc}")
                continue
            for line in lines:
                if not line.strip():
                    continue
                # RECORD format: file,hash,size
                file_path = line.split(",")[0]
                if file_path:
                    if file_path.startswith(".."):
                        # Handle ../../../pip3 style paths
                        abs_path = (site_packages / file_path).resolve()
                    else:
                        abs_path = site_packages / file_path
                    ignore_files.add(abs_path)
                    # Also add the dist-info directory itself
                    ignore_files.add(item)

    # Also ignore any .whl files in ensurepip/_bundled (upgraded pip wheels)
    if ensurepip_bundled.is_dir():
        for whl in ensurepip_bundled.glob("*.whl"):
            ignore_files.add(whl)

    # Special case: The PythonT framework postinstall script renames pip3 to pip3t
    # and pip3.X to pip3.Xt, so these files aren't tracked in the wheel's RECORD
    if abiflags == "t":
        bin_python = check_path / "bin"
        if bin_python.exists():
            for pip_name in (f"pip{version.major}t", f"pip{version}t"):
                pip_path = bin_python / pip_name
                if pip_path.exists():
                    ignore_files.add(pip_path)

    return ignore_files


def _check_extra_files(
    all_files: set[Path], version: Version, force: bool
) -> tuple[bool, set[Path]]:
    """
    Check for extra files not managed by packages.
    Returns (OK to proceed, set of acceptable extra files to remove).
    """
    extra_files: set[Path] = set()
    acceptable_extras: set[Path] = set()

    # Find the most specific directories that contain our package files
    check_dirs: set[Path] = set()

    # Group files by their parent directories to find Python-specific roots
    version_roots = {f"Python {version}", str(version)}
    for file_path in all_files:
        for parent in file_path.parents:
            if parent.name in version_roots:
                check_dirs.add(parent)
                break

    # Build a set of files to ignore: pip-installed packages and ensurepip-related stuff
    ignore_files: set[Path] = set()
    for check_path in check_dirs:
        ignore_files.update(_find_lib_python_files(check_path, version, ""))
        ignore_files.update(_find_lib_python_files(check_path, version, "t"))

    # Walk these directories and find files not in our package list
    for check_path in check_dirs:
        for item in check_path.rglob("*"):
            # Skip if already known
            if item in all_files:
                continue

            if item.is_file() or item.is_symlink():
                # Safe to remove during installation without a fuss
                if (
                    item.suffix == ".pyc"
                    or item.is_symlink()
                    or item in ignore_files
                    or any(
                        item.is_relative_to(ignored)
                        for ignored in ignore_files
                        if ignored.is_dir()
                    )
                ):
                    acceptable_extras.add(item)
                else:
                    # Unsafe to delete, will complain later
                    if not item.is_symlink():
                        extra_files.add(item)

    if extra_files:
        cutoff = 1000  # Show first `cutoff` files
        sorted_extras = sorted(extra_files, key=str)
        prefix = "" if force else "Error: "
        print(f"\n{prefix}Found extra files not installed by the package:")

        for file in sorted_extras[:cutoff]:
            print(f"  - {file}")
        if len(extra_files) > cutoff:
            print(f"  ... and {len(extra_files) - cutoff} more")
        if not force:
            print(
                "\nUse --force=true to remove anyway,"
                " or manually clean up these files first."
            )
            return False, set()

    if force:
        acceptable_extras.update(extra_files)

    return True, acceptable_extras


def _remove_files(
    all_files: set[Path], dry_run: bool = False
) -> tuple[set[Path], dict[Path, str]]:
    """Remove files one by one.

    Returns a two-tuple with (successfully_removed, failed_files). Successfully removed
    is a set, failed files is a dictionary where paths are keys and exception messages
    are values.
    """
    removed_count = 0
    failed_files: dict[Path, str] = {}
    successfully_removed: set[Path] = set()

    for path in sorted(all_files, key=str, reverse=True):  # Remove in reverse order
        try:
            if lexists(path):
                if path.is_symlink() or path.is_file():
                    if not dry_run:
                        path.unlink()
                    removed_count += 1
                    successfully_removed.add(path)
        except Exception as e:
            failed_files[path] = str(e)

    return successfully_removed, failed_files


def _remove_directories(
    all_dirs: set[Path],
    dry_run: bool = False,
    *,
    removed_files: set[Path] | None = None,
) -> tuple[set[Path], dict[Path, str]]:
    """Remove directories.

    Returns (removed_dirs, failed_dirs).
    """
    removed_dirs: set[Path] = set()
    removed_files = removed_files or set()
    failed_dirs: dict[Path, str] = {}

    for path in sorted(all_dirs, key=str, reverse=True):
        try:
            if not path.exists():
                continue
            if not path.is_dir():
                continue
            if dry_run:
                # In dry run, check if dir would be empty after file/subdir removal
                remaining_items = [
                    item
                    for item in path.iterdir()
                    if item not in removed_files and item not in removed_dirs
                ]
                if not remaining_items:
                    removed_dirs.add(path)
                else:
                    # Check if all remaining items are dirs that will be removed
                    all_dirs_removed = all(
                        item in all_dirs and item in removed_dirs
                        for item in remaining_items
                        if item.is_dir()
                    )
                    all_files_removed = all(
                        item in removed_files
                        for item in remaining_items
                        if item.is_file()
                    )

                    if all_dirs_removed and all_files_removed:
                        removed_dirs.add(path)
                    else:
                        actual_remaining = [
                            item
                            for item in remaining_items
                            if (item.is_file() and item not in removed_files)
                            or (item.is_dir() and item not in all_dirs)
                        ]
                        if actual_remaining:
                            remaining_names = ", ".join(
                                item.name for item in actual_remaining[:5]
                            )
                            if len(actual_remaining) > 5:
                                remaining_names += (
                                    f", ... and {len(actual_remaining) - 5} more"
                                )
                            failed_dirs[path] = f"Files remaining: {remaining_names}"
                        elif remaining_items:
                            # There are remaining items but they're all in our removal
                            # list but haven't been removed yet (processing order issue)
                            # This should still be counted as a failure
                            remaining_names = ", ".join(
                                item.name for item in remaining_items[:5]
                            )
                            if len(remaining_items) > 5:
                                remaining_names += (
                                    f", ... and {len(remaining_items) - 5} more"
                                )
                            failed_dirs[path] = f"Files remaining: {remaining_names}"
            else:
                path.rmdir()
                removed_dirs.add(path)
        except Exception as e:
            failed_dirs[path] = str(e)

    return removed_dirs, failed_dirs


def _forget_packages(packages: list[str], dry_run: bool = False) -> None:
    """Forget packages from the system database."""
    print("\nForgetting packages from system database...")
    for pkg in packages:
        if dry_run:
            print(f"  - Would forget {pkg}")
        else:
            result = run(  # noqa: S603
                ["/usr/sbin/pkgutil", "--forget", pkg],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(f"Warning: Failed to forget package {pkg}: {result.stderr}")
            else:
                print(f"  - Forgot {pkg}")


def _empty_pkgfileinfo(pkgid: str, install_time: int = 0) -> PkgFileInfo:
    return {
        "pkgid": pkgid,
        "pkg-version": "0",
        "uid": 0,
        "gid": 0,
        "mode": 0,
        "install-time": install_time,
    }
