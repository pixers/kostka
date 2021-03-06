import click
import sys
import os
import shutil
import subprocess
from ..utils import cli, require_existing_container, systemd_reload, run_hooks, Container
from ..plugins import extensible_command


@cli.command()
@extensible_command
@click.argument("name")
@click.option('--recursive', '-r', help="Also remove containers that depend on the removed container", is_flag=True)
@click.option('--reload-systemd/--no-reload-systemd', default=True)
@click.pass_context
@require_existing_container
def rm(ctx, name, recursive, extensions, reload_systemd):
    """ Removes a container """

    children = list(filter(lambda c: name in c.dependencies, Container.all()))
    if len(children) > 0:
        if recursive:
            for container in children:
                ctx.invoke(rm, name=container.name, recursive=recursive)
        else:
            children = ', '.join(map(lambda c: c.name, children))
            print("Container {} is in use by {}. Not removing.".format(name, children))
            sys.exit(1)

    if os.path.exists('/etc/systemd/systemd/{}.service'.format(name)):
        subprocess.check_call(['/bin/systemctl', 'kill', name])
        subprocess.check_call(['/bin/systemctl', 'kill', name])
    extensions(Container(name))

    try:
        os.remove('/etc/systemd/system/{}.service'.format(name))
    except FileNotFoundError:
        pass

    try:
        shutil.rmtree('/var/lib/machines/{}'.format(name))
    except FileNotFoundError:
        pass

    if reload_systemd:
        systemd_reload()

    run_hooks('post-rm', name)
