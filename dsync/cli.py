"""Example cli using click."""
import click

# Import necessary project related things to use in CLI


@click.command()
@click.option("--test", help="Test argument")
def main():
    """Entrypoint into CLI app."""
