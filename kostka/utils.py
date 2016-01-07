import subprocess
import os
import sys
import click
import json
from toposort import toposort_flatten


class cached_property(property):
    def __init__(self, fget=None, fset=None, fdel=None, doc=None, **kwargs):
        self.cached_value = {}
        if fget:
            if hasattr(fget, '__self__') and fget.__self__.__class__ == self.__class__:
                fget = fget.__self__._fget
            self._fget = fget
            fget = self.fget_wrapper

        if fset and fset != self.fset_wrapper:
            if hasattr(fset, '__self__') and fset.__self__.__class__ == self.__class__:
                fset = fset.__self__._fset
            self._fset = fset
            fset = self.fset_wrapper

        super().__init__(fget=fget, fset=fset, fdel=None, doc=None, **kwargs)

    def fget_wrapper(self, obj, *args, **kwargs):
        if not hasattr(obj, '_cached_values'):
            obj._cached_values = {}

        name = self._fget.__name__

        if name in obj._cached_values:
            return obj._cached_values[name]
        else:
            obj._cached_values[name] = self._fget(obj, *args, **kwargs)
            return obj._cached_values[name]

    def fset_wrapper(self, obj, *args, **kwargs):
        if not hasattr(obj, '_cached_values'):
            obj._cached_values = {}

        name = self._fget.__name__
        obj._cached_values[name] = self._fset(obj, *args, **kwargs)
        return obj._cached_values[name]


class Container:
    def __init__(self, name):
        self.name = name

    @cached_property
    def manifest(self):
        try:
            with open('/var/lib/machines/{}/manifest'.format(self.name)) as f:
                return json.loads(f.read())
        except FileNotFoundError:
            return {
                "acKind": "ImageManifest",
                "acVersion": "0.7.4",
                "kostkaVersion": "0.0.1",
                "name": self.name,
                "dependencies": [
                    {"imageName": "debian-jessie"}
                ]
            }

    @manifest.setter
    def manifest(self, manifest):
        with open('/var/lib/machines/{}/manifest'.format(self.name), 'w') as f:
            f.write(json.dumps(manifest, indent=2))

    @cached_property
    def dependencies(self):
        return list(dependency['imageName'] for dependency in self.manifest['dependencies'])

    @dependencies.setter
    def dependencies(self, dependencies):
        manifest = self.manifest
        manifest['dependencies'] = list({"imageName": name} for name in dependencies)
        self.manifest = manifest

    def mount_lowerdirs(self):
        # First, build a dependency graph in order to avoid duplicate entries
        dependencies = {}
        pending_deps = set(self.dependencies)
        while len(pending_deps) > 0:
            name = pending_deps.pop()
            if name not in dependencies:
                dependencies[name] = set(Container(name).dependencies)

        # Then sort it topologically. The list is reversed, because overlayfs
        # will check the mounts in order they are given, so the base fs has to
        # be the last one.
        dependencies = reversed(list(toposort_flatten(dependencies)))
        return ':'.join('/var/lib/machines/{}/overlay.fs'.format(dep) for dep in dependencies)


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
    dirname = os.path.dirname(__file__)
    hooks_dir = os.path.join(dirname, 'hooks', type)
    if not os.path.exists(hooks_dir):
        return

    for path in sorted(os.listdir(hooks_dir)):
        path = os.path.join(hooks_dir, path)
        if not os.path.isfile(path) or not os.access(path, os.X_OK):
            print("NOT running hook {path} "
                  "(`chmod +x {path}`?)".format(path=path), file=sys.stderr)
            continue

        subprocess.call([path] + list(args))
