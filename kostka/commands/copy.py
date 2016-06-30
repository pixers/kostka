import click
from ..utils import cli, require_existing_container, Container
from .create import create
from ..plugins import extensible_command


@cli.command()
@extensible_command
@click.argument("name")
@click.argument("new_name")
@click.option("--template", "-t", default="debian-jessie")
@click.pass_context
@require_existing_container
def copy(ctx, name, new_name, template, extensions):
    ctx.invoke(create, name=new_name, template=template)
    extensions(Container(name), Container(new_name))
