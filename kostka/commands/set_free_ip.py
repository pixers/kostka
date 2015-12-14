import click
import requests
import sys
from ..utils import cli, require_existing_container
from .set_ip import set_ip


def find_free_ip():
    data = requests.get('http://consul.service.ovh.pixers:8500/v1/catalog/nodes') \
                   .json()
    ips = set(node['Address'] for node in data)
    for i in range(10, 255):
        if "172.16.6.{}".format(i) not in ips:
            return "172.16.6.{}".format(i)


@cli.command(name="set-free-ip")
@click.argument('name')
@click.pass_context
@require_existing_container
def set_free_ip(ctx, name):
    ip = find_free_ip()
    if not ip:
        print("No free ip in range 172.16.6.{10-255}.", file=sys.stderr)

    ctx.invoke(set_ip, name=name, cidr=ip+"/16")
    print("Container {} now has ip {}/16".format(name, ip))
