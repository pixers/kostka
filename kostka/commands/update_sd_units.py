import re
import click
import pystache
import subprocess
from configparser import SafeConfigParser
from ..utils import cli, systemd_reload, require_existing_container, Container
from ..plugins import extensible_command


def all_units(ctx, param, value):
    if not value:
        return
    for machine in Container.all():
        ctx.invoke(update_sd_units, name=machine.name)
    ctx.exit()


@cli.command(name='update-sd-units')
@extensible_command
@click.argument('name')
@click.option("--all", "-a", is_flag=True, help="Update systemd units of all containers.", callback=all_units, is_eager=True, expose_value=False)
@require_existing_container
def update_sd_units(name, extensions):
    """ Recreate the systemd units for the container. """

    container = Container(name)

    nspawn_args = [
        '--quiet',
        '--keep-unit',
        '--boot',
        '--directory={}/fs'.format(container.path),
        '-M {}'.format(name),
    ]
    capabilities = []
    container_service = SafeConfigParser()
    container_service.optionxform = str
    container_service['Unit'] = {
        'Description': 'Container: {}'.format(name),
    }

    container_service['Service'] = {
        'ExecStart': 'systemd-nspawn {nspawn_args}',
        'ExecStop': '/bin/machinectl stop {}'.format(name),
        'KillMode': 'mixed',
        'Type': 'notify',
        'RestartForceExitStatus': '133',
        'SuccessExitStatus': '133 SIGRTMIN+4',
    }

    container_service['Install'] = {
        'WantedBy': 'default.target'
    }

    extensions(container, container_service, nspawn_args, capabilities)
    if len(capabilities) > 0:
        nspawn_args.append('--capability {}'.format(','.join(capabilities)))

    container_service['Service']['ExecStart'] = container_service['Service']['ExecStart'].format(nspawn_args=' '.join(nspawn_args))

    # Prepare the container service
    with open("/etc/systemd/system/{}.service".format(name), 'w') as f:
        container_service.write(f)

    systemd_reload()
