"""Command-line interface."""
import click

from mopup import main as libmain


@click.command()
@click.version_option()
def main() -> None:
    """MOPUp."""
    libmain()


if __name__ == "__main__":
    main(prog_name="MOPUp")  # pragma: no cover
