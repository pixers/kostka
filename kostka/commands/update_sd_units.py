import click
from ..utils import cli, systemd_reload, require_existing_container, Container
from ..plugins import extensible_command


def all_units(ctx, param, value):
    if not value:
        return
    for machine in Container.all():
        ctx.invoke(update_sd_units, name=machine.name, reload_sd=False)
    systemd_reload()
    ctx.exit()


@cli.command(name='update-sd-units')
@extensible_command
@click.argument('name')
@click.option("--all", "-a", is_flag=True, help="Update systemd units of all containers.", callback=all_units, is_eager=True, expose_value=False)
@require_existing_container
def update_sd_units(name, extensions, reload_sd=True):
    """ Recreate the systemd units for the container. """

    container = Container(name)

    nspawn_args = [
        '--quiet',
        '--keep-unit',
        '--boot',
        '--directory={}/fs'.format(container.path),
        '--tmpfs=/tmp',
        '--link-journal=host',
        '-M {}'.format(name),
    ]
    capabilities = []
    container_service = {}
    container_service['Unit'] = {
        'Description': 'Container: {}'.format(name),
    }

    container_service['Service'] = {
        'ExecStart': 'systemd-nspawn {nspawn_args}',
        'ExecStop': '/bin/machinectl poweroff {}'.format(name),
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
        for (section_name, section) in container_service.items():
            f.write('\n[{}]\n'.format(section_name))
            for (name, value) in section.items():
                if isinstance(value, list):
                    for v in value:
                        f.write("{}={}\n".format(name, v))
                else:
                    f.write("{}={}\n".format(name, value))

    if reload_sd:
        systemd_reload()
