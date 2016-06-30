import click
import os
import sys
import subprocess
from configparser import SafeConfigParser
from toposort import toposort_flatten


def escape_path(path):
    return subprocess.check_output(['systemd-escape', '-p', path]).strip().decode('utf-8')


@click.option("--template", "-t", default="debian-jessie")
def create(ctx, container, template, **kwargs):
    try:
        os.mkdir("/var/lib/machines/{}".format(container.name))
        os.mkdir("/var/lib/machines/{}/fs".format(container.name))
        os.mkdir("/var/lib/machines/{}/overlay.fs-1".format(container.name))
        os.symlink(os.path.join(container.path, 'overlay.fs-1'), os.path.join(container.path, 'overlay.fs'))
        os.mkdir("/var/lib/machines/{}/workdir".format(container.name))
    except FileExistsError:
        # The overlay might be left over from a previous container
        pass

    container.dependencies = ({'imageName': dep} for dep in template.split(','))


def rm(container):
    mount_unit = escape_path(os.path.join(container.path, 'fs')) + '.mount'
    subprocess.call(['/bin/systemctl', 'stop', mount_unit],
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL)
    mount_active = subprocess.call(['/bin/systemctl', 'is-active', mount_unit],
                                   stderr=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL) == 0

    if mount_active:
        print("Unmounting the container's volume failed. Not removing.",
              file=sys.stderr)
        sys.exit(1)

    try:
        os.remove('/etc/systemd/system/{}'.format(mount_unit))
    except FileNotFoundError:
        pass


def update_sd_units(container, service, *args):
    name = container.name
    mount_name = escape_path(name)

    # Prepare the overlayfs mount unit
    mount = SafeConfigParser()
    mount.optionxform = str
    mount['Unit'] = {
        'Description': 'OverlayFS for {}'.format(name),
        'PartOf': '{}.service'.format(mount_name)
    }
    mount['Mount'] = container.mounts()[0]
    mount_path = subprocess.check_output(['systemd-escape', '--path', mount['Mount']['Where']]).strip().decode('utf-8')
    dst_filename = "/etc/systemd/system/{}.mount".format(mount_path)
    with open(dst_filename, 'w') as f:
        mount.write(f)

    unit = service['Unit']
    if 'Requires' not in unit:
        unit['Requires'] = ''
    if 'After' not in unit:
        unit['After'] = ''

    unit['Requires'] += 'var-lib-machines-{}-fs.mount '.format(mount_name)
    unit['After'] += 'var-lib-machines-{}-fs.mount '.format(mount_name)


class MountContainer:
    @property
    def dependencies(self):
        return list(dependency for dependency in self.manifest['dependencies'])

    @dependencies.setter
    def dependencies(self, dependencies):
        manifest = self.manifest
        manifest['dependencies'] = list(name for name in dependencies)
        self.manifest = manifest

    def mounts(self):
        options = 'lowerdir={initfs}:{dependencies},upperdir={upperdir},workdir={workdir}'
        options = options.format(
            initfs=os.path.join(self.path, 'init.fs'),
            dependencies=self.mount_lowerdirs(),
            upperdir=os.path.join(self.path, 'overlay.fs'),
            workdir=os.path.join(self.path, 'workdir')
        )
        return [{
            'What': 'overlayfs',
            'Where': os.path.join(self.path, 'fs'),
            'Options': options,
            'Type': 'overlay'
        }]

    def init_mounts(self):
        options = 'lowerdir={dependencies},upperdir={initfs},workdir={workdir}'
        options = options.format(
            initfs=os.path.join(self.path, 'init.fs'),
            dependencies=self.mount_lowerdirs(),
            workdir=os.path.join(self.path, 'workdir')
        )
        return [{
            'What': 'overlayfs',
            'Where': os.path.join(self.path, 'fs'),
            'Options': options,
            'Type': 'overlay'
        }]

    def mount_lowerdirs(self):
        # First, build a dependency graph in order to avoid duplicate entries
        dependencies = {}

        def dependency_path(dep):
            container = self.__class__(dep['imageName'])
            path = dep.get('path', os.readlink(os.path.join(container.path, 'overlay.fs')))
            return os.path.join(dep['imageName'], path)

        pending_deps = set(map(dependency_path, self.dependencies))
        while len(pending_deps) > 0:
            path = pending_deps.pop()
            name = path.split('/')[-2]
            if name not in dependencies:
                dependencies[path] = set(map(dependency_path, self.__class__(name).dependencies))
                pending_deps |= dependencies[path]

        # Then sort it topologically. The list is reversed, because overlayfs
        # will check the mounts in order they are given, so the base fs has to
        # be the last one.
        dependencies = reversed(list(toposort_flatten(dependencies)))
        return ':'.join(os.path.join(self.metadata_dir, dep) for dep in dependencies)

    def default_manifest(self):
        super_dict = {}
        if hasattr(super(), 'default_manifest'):
            super_dict = super().default_manifest()

        if self.name == 'debian-jessie':
            super_dict.update({"dependencies": []})
        else:
            super_dict.update({
                "dependencies": [
                    {"imageName": "debian-jessie"}
                ],
            })

        return super_dict
