import click
import subprocess
from ..utils import cli, require_existing_container, run_hooks, Container
from ..plugins import extensible_command


@cli.command()
@extensible_command
@click.argument("name")
@require_existing_container
def stop(name, extensions):
    run_hooks('pre-stop', name)
    subprocess.check_call(['/bin/systemctl', 'stop', name])
    extensions(Container(name))
    run_hooks('post-stop', name)
