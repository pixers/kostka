import click
import subprocess
from ..utils import cli, require_existing_container, run_hooks


@cli.command()
@click.argument("name")
@require_existing_container
def stop(name):
    run_hooks('pre-stop', name)
    subprocess.check_call(['/bin/systemctl', 'stop', name])
    run_hooks('post-stop', name)
