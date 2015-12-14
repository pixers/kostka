import click
import os
import re
from ..utils import cli, require_existing_container, is_active
from .enter import enter


@cli.command(name='set-ip')
@click.argument('name')
@click.argument('cidr')
@click.pass_context
@require_existing_container
def set_ip(ctx, name, cidr):
    """ Sets an ip address for the container's veth interface """
    ip, netmask = cidr.split('/', 1)

    # We want it to work both for running and not running containers.
    # If the container is running, we have to set it's ip without rebooting it.
    if is_active(name):
        ctx.invoke(enter, name=name, cmd=('ip', 'link', 'set', 'host0', 'up'))
        ctx.invoke(enter, name=name, cmd=('ip', 'address', 'flush', 'dev', 'host0'))
        ctx.invoke(enter, name=name, cmd=('ip', 'address', 'add', cidr, 'dev', 'host0'))

    path = '/var/lib/machines/' + name
    if is_active('var-lib-machines-{}-fs.mount'.format(name)):
        # Now if the overlayfs is mounted, we should use it:
        path += '/fs'
    else:
        # Otherwise, use the overlay directly
        path += '/init.fs'

    cwd = os.getcwd()
    os.chdir(path)
    try:
        try:
            os.makedirs('etc/network/interfaces.d')
        except FileExistsError:
            pass

        with open('etc/network/interfaces.d/host0', 'w') as f:
            template = """
            auto host0
            iface host0 inet static
                address {ip}
                netmask {netmask}
            """.format(ip=ip, netmask=netmask)
            template = re.sub(r"^ {8}", "", template, flags=re.MULTILINE).lstrip()
            f.write(template)
    finally:
        os.chdir(cwd)
