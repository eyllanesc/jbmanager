"""Command-line interface."""

import click


@click.command()
@click.version_option()
def main() -> None:
    """JBManager."""


if __name__ == "__main__":
    main(prog_name="jbmanager")  # pragma: no cover
