import click
import subprocess
from ..utils import cli, Container, require_existing_container


@cli.command()
@click.argument("name")
@click.option("-u", "--unmount", help="Instead of mounting, unmount filesystems for the container.", is_flag=True)
@click.option("--cmdline", help="Display the mount command line instead of executing it.", is_flag=True)
@require_existing_container
def mount(name, unmount, cmdline):
    """Mount filesystems needed for a container"""

    container = Container(name)

    cmdlines = []
    mounts = container.mounts()

    for mount in mounts:
        if unmount:
            cmd = ['umount', str(mount['Where'])]
        else:
            cmd = ['mount', '-t', mount['Type'], '-o', mount['Options'], mount['What'], str(mount['Where'])]
        cmdlines.append(cmd)

    if cmdline:
        for cmd in cmdlines:
            print(' '.join(cmd))
    else:
        for cmd in cmdlines:
            subprocess.check_call(cmd)
