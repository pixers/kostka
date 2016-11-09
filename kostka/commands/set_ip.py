import click
import os
import re
from ..utils import cli, require_existing_container, is_active
from .enter import enter


@cli.command(name='set-ip')
@click.option('-i', '--interface', default='host0')
@click.option('--gateway', help='Default gateway for the interface')
@click.argument('name')
@click.argument('cidr')
@click.pass_context
@require_existing_container
def set_ip(ctx, name, cidr, interface, gateway):
    """ Sets an ip address for a container's network interface.

        Instead of passing a static IP address, you can use
        `kostka set-ip CONTAINER dhcp` to get the address from
        a DHCP server.
    """
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

        with open('etc/network/interfaces.d/' + interface, 'w') as f:
            if cidr == 'dhcp':
                template = """
                auto {interface}
                iface {interface} inet dhcp
                """.format(interface=interface)
            else:
                ip, netmask = cidr.split('/', 1)
                template = """
                auto {interface}
                iface {interface} inet static
                    address {ip}
                    netmask {netmask}
                """.format(ip=ip, netmask=netmask, interface=interface)
                if gateway is not None:
                    template += "    gateway {gateway}\n".format(gateway=gateway)
            template = re.sub(r"^ {16}", "", template, flags=re.MULTILINE).lstrip()
            f.write(template)
    finally:
        os.chdir(cwd)

    # We want it to work both for running and not running containers.
    # If the container is running, we have to set it's ip without rebooting it.
    if is_active(name):
        ctx.invoke(enter, name=name, cmd=('ifup', interface))
