import click
import subprocess
from ..utils import cli, Container, require_existing_container


@cli.command()
@click.argument("name")
@click.option("-u", "--unmount", help="Instead of mounting, unmount filesystems for the container.", is_flag=True)
@click.option("--init", help="Mount the filesystems for the first boot of the container.", is_flag=True)
@click.option("--cmdline", help="Display the mount command line instead of executing it.", is_flag=True)
@require_existing_container
def mount(name, unmount, init, cmdline):
    """Mount filesystems needed for a container"""

    container = Container(name)

    cmdlines = []
    if init:
        mounts = container.init_mounts()
    else:
        mounts = container.mounts()

    for mount in mounts:
        if unmount:
            cmd = ['umount', mount['Where']]
        else:
            cmd = ['mount', '-t', mount['Type'], '-o', mount['Options'], mount['What'], mount['Where']]
        cmdlines.append(cmd)

    if cmdline:
        for cmd in cmdlines:
            print(' '.join(cmd))
    else:
        for cmd in cmdlines:
            subprocess.check_call(cmd)
