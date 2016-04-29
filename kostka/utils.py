import subprocess
import os
import sys
import click
import pkg_resources
from .container import Container


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
    return Container(name).exists()


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
    dirname = os.path.dirname(__file__)
    hooks_dir = os.path.join(dirname, 'hooks', type)
    dirs = [os.path.join(dirname, 'hooks', type),
            os.path.join('/usr/lib/kostka/hooks', type),
            os.path.join('/etc/kostka/hooks', type), ]
    hooks = []
    for hooks_dir in dirs:
        if not os.path.exists(hooks_dir):
            continue

        hooks += map(lambda f: os.path.join(hooks_dir, f), os.listdir(hooks_dir))

    for ep in pkg_resources.iter_entry_points(group='kostka'):
        path = os.path.join(ep.dist.location, ep.dist.key.replace('-', '_'), 'hooks', type)
        if os.path.exists(path):
            hooks += map(lambda f: os.path.join(path, f), os.listdir(path))

    for path in sorted(hooks):
        if not os.path.isfile(path) or not os.access(path, os.X_OK):
            print("NOT running hook {path} "
                  "(`chmod +x {path}`?)".format(path=path), file=sys.stderr)
            continue

        subprocess.call([path] + list(args))
