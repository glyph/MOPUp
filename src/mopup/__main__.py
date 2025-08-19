"""Command-line interface."""

import click

from mopup import main as libmain
from mopup import uninstall as libuninstall


@click.group(
    help="""
         MOPUp - the (m)ac(O)S (P)ython.org (Up)dater

         Tool for managing Python.org installations on macOS.
         """
)
def main() -> None:
    """The main group for all Click commands."""
    pass


@main.command(
    help="""
         Update Python to the latest version.

         Run this command and enter your administrator password to install the
         most recent version from Python.org that matches your major/minor
         version.
         """
)
@click.option("--interactive", default=False, help="use the installer GUI", type=bool)
@click.option(
    "--force", default=False, help="reinstall python even if it's up to date", type=bool
)
@click.option(
    "--minor",
    default=False,
    help="do a minor version upgrade rather than the default (a micro-version)",
    type=bool,
)
@click.option(
    "--dry-run",
    default=False,
    help="don't actually download or install anything even if we're not up to date",
    type=bool,
)
def update(interactive: bool, force: bool, minor: bool, dry_run: bool) -> None:
    """Update Python to the latest version."""
    libmain(interactive=interactive, force=force, minor_upgrade=minor, dry_run=dry_run)


@main.command(
    help="""
         Uninstall a specific Python version.

         Removes all files and packages associated with the specified Python version.
         """
)
@click.argument("version", type=str)
@click.option(
    "--dry-run",
    default=False,
    help="show what would be removed without actually removing anything",
    type=bool,
)
@click.option(
    "--interactive",
    default=False,
    help="ask for confirmation before proceeding",
    type=bool,
)
@click.option(
    "--force",
    default=False,
    help="remove even if extra files are present",
    type=bool,
)
def uninstall(version: str, dry_run: bool, interactive: bool, force: bool) -> None:
    """Uninstall a specific Python version."""
    libuninstall(
        minor_release_version=version,
        dry_run=dry_run,
        interactive=interactive,
        force=force,
    )


if __name__ == "__main__":
    main(prog_name="mopup")  # pragma: no cover
