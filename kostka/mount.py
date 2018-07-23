import click
import os
import sys
import subprocess
from configparser import SafeConfigParser
from toposort import toposort_flatten
from .oci import Image


def escape_path(path):
    cmd = ['systemd-escape', '-p', str(path)]
    return subprocess.check_output(cmd).strip().decode('utf-8')


@click.option("--template", "-t", help="Container to use as a base filesystem. Deprecated - use --image instead.")
@click.option("--image", "-i", help="Image to use as a base filesystem.")
def create(ctx, container, template, image, **kwargs):
    os.mkdir("/var/lib/machines/{}/fs".format(container.name))
    container.dependencies = []
    if image is not None:
        for dep in image.split(','):
            if ':' not in dep:
                dep += ':latest'

            name, version = dep.split(':')
            index = Image.download_index(name, version)
            version = index['annotations']['kostka.image.version']

            container.dependencies += [{'image': name, 'version': version}]
    elif template is None:
        return

    try:
        os.mkdir("/var/lib/machines/{}/overlay.fs-1".format(container.name))
        (container.path / 'overlay.fs').symlink_to(container.path / 'overlay.fs-1')
        os.mkdir("/var/lib/machines/{}/workdir".format(container.name))
    except FileExistsError:
        # The overlay might be left over from a previous container
        pass

    if template is not None:
        container.dependencies = ({'imageName': dep} for dep in template.split(','))


def umount(container):
    mount_unit = escape_path(container.path / 'fs') + '.mount'
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

    return mount_unit


def rm(container):
    mount_unit = umount(container)
    try:
        os.remove('/etc/systemd/system/{}'.format(mount_unit))
    except FileNotFoundError:
        pass


def stop(container):
    umount(container)


def copy(container, new_container):
    src = os.path.join(container.path, "overlay.fs")
    src = os.readlink(src)
    # We can assume it's overlay.fs-1, because it's a new container
    dest = os.path.join(new_container.path, "overlay.fs-1")
    os.rmdir(dest)
    subprocess.check_call(['/bin/cp', '-a', src, dest])


def update_sd_units(container, service, *args):
    if len(container.dependencies) == 0:
        return  # This container doesn't use overlayfs

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
        if (self.path / 'init.fs').exists():
            # Legacy container, has init.fs
            options = 'lowerdir={initfs}:{dependencies},upperdir={upperdir},workdir={workdir}'
            options = options.format(
                initfs=self.path / 'init.fs',
                dependencies=':'.join(self.mount_lowerdirs()),
                upperdir=self.path / 'overlay.fs',
                workdir=self.path / 'workdir'
            )
        else:
            options = 'lowerdir={dependencies},upperdir={upperdir},workdir={workdir}'
            options = options.format(
                dependencies=':'.join(self.mount_lowerdirs()),
                upperdir=self.path / 'overlay.fs',
                workdir=self.path / 'workdir'
            )
        return [{
            'What': 'overlayfs',
            'Where': self.path / 'fs',
            'Options': options,
            'Type': 'overlay'
        }]

    def mount_lowerdirs(self):
        # First, build a dependency graph in order to avoid duplicate entries
        dependencies = {}

        def dependency_path(dep):
            if 'image' in dep:
                return Image.download(dep['image'], dep['version'])
            if ':' in dep['imageName']:  # It's an image
                return Image.download(dep['imageName'])
            else:  # It's a container
                container = self.__class__(dep['imageName'])
                path = dep.get('path', str((container.path / 'overlay.fs').resolve()))
                return os.path.join(dep['imageName'], path)

        pending_deps = set(map(dependency_path, self.dependencies))
        while len(pending_deps) > 0:
            path = pending_deps.pop()
            if isinstance(path, Image):
                path.extract()
                prev_layer = str(path.layers[-1].fs_path)
                dependencies[prev_layer] = set()
                for layer in reversed(path.layers[:-1]):
                    dependencies[prev_layer] = {str(layer.fs_path)}
                    prev_layer = str(layer.fs_path)
            else:
                name = path.split('/')[-2]
                if name not in dependencies:
                    dependencies[path] = set(map(dependency_path, self.__class__(name).dependencies))
                    pending_deps |= dependencies[path]

        # Then sort it topologically. The list is reversed, because overlayfs
        # will check the mounts in order they are given, so the base fs has to
        # be the last one.
        dependencies = reversed(list(toposort_flatten(dependencies)))
        return (os.path.join(self.metadata_dir, dep) for dep in dependencies)

    def default_manifest(self):
        super_dict = {}
        if hasattr(super(), 'default_manifest'):
            super_dict = super().default_manifest()

        super_dict.update({"dependencies": []})

        return super_dict
