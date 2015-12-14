import click
import subprocess
from ..utils import cli


@cli.command()
@click.argument("name")
def prepare(name):
    """ Prepare a container for first boot. """
    subprocess.check_call(["./prepare", name])
