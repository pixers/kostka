import click
import os
import sys
import subprocess
from ..utils import cli, run_hooks, Container
from .update_sd_units import update_sd_units
from .rm import rm
from ..plugins import extensible_command


@cli.command()
@extensible_command
@click.argument("name")
@click.pass_context
def create(ctx, name, extensions, **kwargs):
    if name != os.path.basename(name):
        print("Invalid name: {}".format(name), file=sys.stderr)
        sys.exit(1)

    container = Container(name)
    if container.exists():
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
    elif service_status not in (3,4):
        print("Something weird is going on with systemd "
              "(`systemctl status {}` returned {} instead of 3 or 4). "
              "I don't know what to do.".format(name, service_status),
              file=sys.stderr)
        sys.exit(1)

    run_hooks('pre-create', name, kwargs['template'])

    os.mkdir("/var/lib/machines/{}".format(container.name))
    extensions(ctx, container, **kwargs)

    try:
        ctx.invoke(update_sd_units, name=name)
        lowerdirs = ':'.join(Container(name).mount_lowerdirs())
        run_hooks('post-create', name, kwargs['template'], lowerdirs)
        print("Container {} has been successfully created.".format(name))
    except ValueError as e:
        print(e.args[1])
        ctx.invoke(rm, name=name)
    except:
        ctx.invoke(rm, name=name)
        raise
