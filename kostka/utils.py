import subprocess
import os
import sys
import click


@click.group()
def cli():
    pass


def get_pid(name):
    data = subprocess.check_output(['/bin/machinectl', 'show', name]) \
                     .decode("utf-8").strip().split("\n")
    data = dict(line.split("=", 1) for line in data)
    return data['Leader']


def systemd_reload():
    subprocess.check_call(["/bin/systemctl", "daemon-reload"])


def container_exists(name):
    return name == os.path.basename(name) \
       and os.path.exists(os.path.join("/var/lib/machines", name))


def require_existing_container(f):
    def inner(*args, **kwargs):
        name = kwargs['name']
        if not container_exists(name):
            print("Container {} does not exist".format(name), file=sys.stderr)
            sys.exit(1)

        f(*args, **kwargs)

    inner.__name__ = getattr(f, '__name__', None) or f.name
    return inner


def is_active(name):
    return subprocess.call(['/bin/systemctl', 'is-active', name],
                           stdout=subprocess.DEVNULL) == 0


def run_hooks(type, *args):
    if not os.path.exists('hooks/' + type):
        return

    for path in sorted(os.listdir('hooks/' + type)):
        path = os.path.join('hooks', type, path)
        if not os.path.isfile(path) or not os.access(path, os.X_OK):
            print("NOT running hook {path} "
                  "(`chmod +x {path}`?)".format(path=path), file=sys.stderr)
            continue

        subprocess.call([path] + list(args))
