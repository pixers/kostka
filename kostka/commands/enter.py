import click
import subprocess
import sys
from ..utils import cli, is_active, get_pid


@cli.command()
@click.argument("name")
@click.argument("cmd", nargs=-1)
@click.option("--host-net", is_flag=True, help="Use the host's network namesapce.")
def enter(name, cmd, host_net):
    if not is_active(name):
        print("Container {} is down. Start it before using this command.".format(name))
        sys.exit(1)

    if cmd == ():
        cmd = ['/bin/bash', '-l']
    cmd = list(cmd)

    isolation_options = ['--mount', '--uts', '--ipc', '--pid', '--root', '--wd']
    if not host_net:
        isolation_options.append('--net')

    subprocess.call(['nsenter', '-t', get_pid(name)] + isolation_options + cmd)
