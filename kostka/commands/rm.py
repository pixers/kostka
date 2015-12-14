import click
import sys
import os
import shutil
import subprocess
from ..utils import cli, require_existing_container, systemd_reload, run_hooks


@cli.command()
@click.argument("name")
@click.option("--data", is_flag=True, help="Remove the container's data")
@require_existing_container
def rm(name, data):
    """ Removes a container """

    subprocess.call(['/bin/systemctl', 'stop', name])
    mount_unit = 'var-lib-machines-{}-fs.mount'.format(name)
    subprocess.call(['/bin/systemctl', 'stop', mount_unit],
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL)
    mount_active = subprocess.call(['/bin/systemctl', 'is-active', mount_unit],
                                   stderr=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL) == 0
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

    if data:
        try:
            shutil.rmtree('/var/lib/machines/{}'.format(name))
        except FileNotFoundError:
            pass

    systemd_reload()

    run_hooks('post-rm', name)
