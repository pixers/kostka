import click
import uuid
from ..utils import cli, systemd_reload, require_existing_container


@cli.command(name='update-sd-units')
@click.argument('name')
@click.option("--template", "-t", default="debian-jessie")
@require_existing_container
def update_sd_units(name, template):
    """ Recreate the systemd units for the container. """

    # Prepare the overlayfs mount unit
    with open("var-lib-machines-container-fs.mount") as f:
        mount_template = f.read()
    dst_filename = "/etc/systemd/system/var-lib-machines-{}-fs.mount".format(name)
    with open(dst_filename, 'w') as f:
        f.write(mount_template.format(name=name, template=template))

    # Prepare the container service
    with open("container.service") as f:
        container_template = f.read()
    with open("/etc/systemd/system/{}.service".format(name), 'w') as f:
        f.write(container_template.format(name=name, uuid=str(uuid.uuid1())))

    systemd_reload()
