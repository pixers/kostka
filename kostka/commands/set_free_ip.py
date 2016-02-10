import click
import requests
import sys
import re
from ..utils import cli, require_existing_container
from .set_ip import set_ip


def find_free_ip(name, group=None):
    data = requests.get('http://consul.service.ovh.pixers:8500/v1/catalog/nodes') \
                   .json()

    group_name, number = re.match('([^0-9]+)(.*)', name).groups()
    if number == '':
        number = 0

    if group is None:
        groups = {re.match('[^0-9]+', node['Node']).group(0): node['Address'].split('.')[2] for node in data}

        if group_name in groups:
            group = groups[group_name]
        else:
            group = 0

    ips = set(node['Address'] for node in data)
    if group == 0:
        for i in range(10, 255):
            if "172.18.0.{}".format(i) not in ips:
                return "172.18.0.{}".format(i)

    return "172.18.{}.{}".format(group, number)


@cli.command(name="set-free-ip")
@click.argument('name')
@click.option('--group', '-g', default=None)
@click.pass_context
@require_existing_container
def set_free_ip(ctx, name, group):
    ip = find_free_ip(name, group)
    if not ip:
        print("No free ip in range 172.16.0.{10-255}.", file=sys.stderr)

    ctx.invoke(set_ip, name=name, cidr=ip + "/12")
    print("Container {} now has ip {}/12".format(name, ip))
