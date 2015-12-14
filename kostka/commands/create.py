import click
import os
import sys
import subprocess
from ..utils import cli, run_hooks
from .update_sd_units import update_sd_units


@cli.command()
@click.argument("name")
@click.option("--template", "-t", default="debian-jessie")
@click.pass_context
def create(ctx, name, template):
    if name != os.path.basename(name):
        print("Invalid name: {}".format(name), file=sys.stderr)
        sys.exit(1)

    mount_path = "/etc/systemd/system/var-lib-machines-{}-fs.mount".format(name)
    if os.path.exists(mount_path):
        print("Container {} already exists.".format(name), file=sys.stderr)
        sys.exit(1)

    service_status = subprocess.call(["/bin/systemctl", "status", name],
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
    if service_status == 0:
        print("There is already a systemd unit called {}. "
              "You can't create a container with the same name.".format(name),
              file=sys.stderr)
        sys.exit(1)
    elif service_status != 3:
        print("Something weird is going on with systemd "
              "(`systemctl status {}` returned {} instead of 3). "
              "I don't know what to do.".format(name, service_status),
              file=sys.stderr)
        sys.exit(1)

    run_hooks('pre-create', name, template)

    os.mkdir("/var/lib/machines/{}".format(name))
    try:
        os.mkdir("/var/lib/machines/{}/fs".format(name))
        os.mkdir("/var/lib/machines/{}/overlay.fs".format(name))
        os.mkdir("/var/lib/machines/{}/workdir".format(name))
    except FileExistsError:
        # The overlay might be left over from a previous container
        pass

    ctx.invoke(update_sd_units, name=name, template=template)
    run_hooks('post-create', name, template)
    print("Container {} has been successfully created.".format(name))
