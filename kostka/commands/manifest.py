import click
import json
from ..utils import cli, require_existing_container, Container


@cli.command()
@click.argument('name')
@require_existing_container
def manifest(name):
    print(json.dumps(Container(name).manifest, indent=2))
