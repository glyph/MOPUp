"""Command-line interface."""

import click

from mopup import main as libmain
from mopup import uninstall as libuninstall


@click.command(
    help="""
         MOPUp - the (m)ac(O)S (P)ython.org (Up)dater

         Run this program and enter your administrator password to install the
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
)
@click.option(
    "--dry-run",
    default=False,
    help="don't actually download or install anything even if we're not up to date",
)
@click.option(
    "--uninstall",
    default=None,
    help="uninstall a specific Python version (e.g., 3.13)",
    type=str,
)
def main(
    interactive: bool, force: bool, minor: bool, dry_run: bool, uninstall: str | None
) -> None:
    """MOPUp."""
    if uninstall:
        libuninstall(
            version=uninstall, dry_run=dry_run, interactive=interactive, force=force
        )
    else:
        libmain(
            interactive=interactive, force=force, minor_upgrade=minor, dry_run=dry_run
        )


if __name__ == "__main__":
    main(prog_name="mopup")  # pragma: no cover
