import click
import os
from ..utils import cli, systemd_reload, require_existing_container, Container


def all_units(ctx, param, value):
    if not value:
        return
    machines = sorted(os.listdir('/var/lib/machines'))
    machines = list(machine for machine in machines if os.path.exists('/etc/systemd/system/{}.service'.format(machine)))
    for machine in machines:
        dependencies = Container(machine).dependencies
        ctx.invoke(update_sd_units, name=machine, template=','.join(dependencies))
    ctx.exit()


@cli.command(name='update-sd-units')
@click.argument('name')
@click.option("--all", "-a", is_flag=True, help="Update systemd units of all containers.", callback=all_units, is_eager=True, expose_value=False)
@require_existing_container
def update_sd_units(name):
    """ Recreate the systemd units for the container. """

    # Prepare the overlayfs mount unit
    with open("var-lib-machines-container-fs.mount") as f:
        mount_template = f.read()
    dst_filename = "/etc/systemd/system/var-lib-machines-{}-fs.mount".format(name)
    with open(dst_filename, 'w') as f:
        f.write(mount_template.format(name=name, template=Container(name).mount_lowerdirs()))

    # Prepare the container service
    with open("container.service") as f:
        container_template = f.read()
    with open("/etc/systemd/system/{}.service".format(name), 'w') as f:
        f.write(container_template.format(name=name))

    systemd_reload()
