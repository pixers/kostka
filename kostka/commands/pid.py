import click
from ..utils import get_pid, cli


@cli.command()
@click.argument("name")
def pid(name):
    print(get_pid(name))
