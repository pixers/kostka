import subprocess
import click
import os
from ..utils import cli
from ..container import Container
from .update_sd_units import all_units


@cli.command()
@click.argument('name')
@click.option('--update', is_flag=True, help='Update dependencies of this container to their newest versions.')
@click.pass_context
def fork(ctx, name, update):
    """Create a new copy of the container's overlay and switch existing children to use it.

    The basic idea is to be able to update the container without affecting others that
    depend on it."""

    container = Container(name)

    # There are various methods for assigning fork names,
    # but for now we choose to just find the smallest N where
    # overlay.fs-N doesn't exist.
    # This should probably be configurable in the future.
    fork_number = 1
    while os.path.exists(os.path.join(container.path, 'overlay.fs-{}'.format(fork_number))):
        fork_number += 1

    src = os.readlink(os.path.join(container.path, 'overlay.fs'))
    dst = os.path.join(container.path, 'overlay.fs-{}'.format(fork_number))
    if update:
        os.mkdir(dst)
    else:
        subprocess.check_call(['cp', '-a', src, dst])

    os.unlink(os.path.join(container.path, 'overlay.fs'))
    os.symlink(dst, os.path.join(container.path, 'overlay.fs'))

    for cont in Container.all():
        modified = False
        for dependency in cont.dependencies:
            if dependency['imageName'] != container.name:
                continue

            if 'path' in dependency:
                continue

            dependency['path'] = 'overlay.fs-{}'.format(fork_number - 1)
            modified = True

        if modified:
            cont.manifest = cont.manifest

    if update:
        for dependency in container.dependencies:
            if 'path' in dependency:
                del dependency['path']

        container.manifest = container.manifest

    all_units(ctx, 'all', True)
