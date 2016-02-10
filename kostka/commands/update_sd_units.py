import re
import click
import pystache
from ..utils import cli, systemd_reload, require_existing_container, Container


def all_units(ctx, param, value):
    if not value:
        return
    for machine in Container.all():
        ctx.invoke(update_sd_units, name=machine.name)
    ctx.exit()


@cli.command(name='update-sd-units')
@click.argument('name')
@click.option("--all", "-a", is_flag=True, help="Update systemd units of all containers.", callback=all_units, is_eager=True, expose_value=False)
@require_existing_container
def update_sd_units(name):
    """ Recreate the systemd units for the container. """

    container = Container(name)
    mount_name = re.sub('-', r'\x2d', name)

    # Prepare the overlayfs mount unit
    with open("var-lib-machines-container-fs.mount") as f:
        mount_template = f.read()
    dst_filename = "/etc/systemd/system/var-lib-machines-{}-fs.mount".format(mount_name)
    with open(dst_filename, 'w') as f:
        f.write(mount_template.format(name=name, template=container.mount_lowerdirs()))

    # Prepare the container service
    with open("container.service") as f:
        container_template = f.read()
    with open("/etc/systemd/system/{}.service".format(name), 'w') as f:
        f.write(pystache.render(container_template, {'name': name, 'mount_name': mount_name, 'bridges': container.bridges}))

    systemd_reload()
