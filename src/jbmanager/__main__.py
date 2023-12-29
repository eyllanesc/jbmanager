"""Command-line interface."""
import click

from .lib import copy_template
from .lib import validate_config


@click.command()
@click.version_option()
def main() -> None:
    """JBManager."""
    config = validate_config(
        r"C:\Users\HP\Documents\projects\JBManager\templates\config.yaml"
    )
    copy_template(config.template_directory, config.output_directory, config)


if __name__ == "__main__":
    main(prog_name="jbmanager")  # pragma: no cover
