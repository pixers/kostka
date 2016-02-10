import click
import sys
import os
import shutil
import subprocess
from ..utils import cli, require_existing_container, systemd_reload, run_hooks, Container


@cli.command()
@click.argument("name")
@click.option('--recursive', '-r', help="Also remove containers that depend on the removed container", is_flag=True)
@click.pass_context
@require_existing_container
def rm(ctx, name, recursive):
    """ Removes a container """

    subprocess.call(['/bin/systemctl', 'stop', name])
    mount_unit = 'var-lib-machines-{}-fs.mount'.format(name)
    subprocess.call(['/bin/systemctl', 'stop', mount_unit],
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL)
    mount_active = subprocess.call(['/bin/systemctl', 'is-active', mount_unit],
                                   stderr=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL) == 0

    children = list(filter(lambda c: name in c.dependencies, Container.all()))
    if len(children) > 0:
        if recursive:
            for container in children:
                ctx.invoke(rm, name=container.name, recursive=recursive)
        else:
            children = ', '.join(map(lambda c: c.name, children))
            print("Container {} is in use by {}. Not removing.".format(name, children))
            sys.exit(1)

    if mount_active:
        print("Unmounting the container's volume failed. Not removing.",
              file=sys.stderr)
        sys.exit(1)

    try:
        os.remove('/etc/systemd/system/{}.service'.format(name))
    except FileNotFoundError:
        pass

    try:
        os.remove('/etc/systemd/system/var-lib-machines-{}-fs.mount'.format(name))
    except FileNotFoundError:
        pass

    try:
        shutil.rmtree('/var/lib/machines/{}'.format(name))
    except FileNotFoundError:
        pass

    systemd_reload()

    run_hooks('post-rm', name)
