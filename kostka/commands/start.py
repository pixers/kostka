import click
import subprocess
from ..utils import cli, require_existing_container, run_hooks


@cli.command()
@click.argument("name")
@require_existing_container
def start(name):
    run_hooks('pre-start', name)
    subprocess.check_call(['/bin/systemctl', 'start', name])
    run_hooks('post-start', name)
