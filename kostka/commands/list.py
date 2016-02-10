import os
import json
import click
import subprocess
from ..utils import cli, container_exists


@cli.command('list')
@click.option('--json', 'json_output', is_flag=True, help='Print the list as a JSON document.')
@click.option('--status', help='Show only hosts with a given status.')
def list_containers(json_output, status):
    machines = sorted(os.listdir('/var/lib/machines'))
    machines = list(filter(container_exists, machines))
    max_name_length = max(map(len, machines))
    result = {}
    for machine in machines:
        try:
            service_status = subprocess.check_output(['systemctl', 'show', machine]).decode('utf-8').strip()
        except subprocess.CalledProcessError as e:
            service_status = e.output.decode('utf-8').strip()

        service_status = dict(line.split("=", 1) for line in service_status.split("\n"))
        active = service_status['ActiveState']
        if status is not None and active != status:
            continue

        if json_output:
            result[machine] = active
        else:
            machine = "{{:<{}}}".format(max_name_length).format(machine)
            print("{} {}".format(machine, active))
    if json_output:
        print(json.dumps(result))
