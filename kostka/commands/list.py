import os
from ..utils import cli, is_active


@cli.command()
def list():
    machines = sorted(os.listdir('/var/lib/machines'))
    machines = dict((machine, is_active(machine)) for machine in machines)
    print(machines)
