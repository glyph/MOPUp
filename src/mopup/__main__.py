"""Command-line interface."""
import click


@click.command()
@click.version_option()
def main() -> None:
    """MOPUp."""


if __name__ == "__main__":
    main(prog_name="MOPUp")  # pragma: no cover
