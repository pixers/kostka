import click
import os
import subprocess
from ..utils import cli, require_existing_container
from .create import create


@cli.command()
@click.argument("name")
@click.argument("new_name")
@click.option("--template", "-t", default="debian-jessie")
@click.pass_context
@require_existing_container
def copy(ctx, name, new_name, template):
    ctx.invoke(create, name=new_name, template=template)
    os.rmdir("/var/lib/machines/{}/overlay.fs".format(new_name))
    subprocess.check_call(['/bin/cp', '-a', "/var/lib/machines/{}/overlay.fs".format(name), "/var/lib/machines/{}/overlay.fs".format(new_name)])
