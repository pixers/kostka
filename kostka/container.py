from toposort import toposort_flatten
from .cached_property import cached_property
import os
import json


def trim_interface_name(name):
    if len(name) >= 15:
        return name[0:15]
    return name


class Container:
    def __init__(self, name):
        self.name = name

    @classmethod
    def all(cls):
        def exists(name):
            return name == os.path.basename(name) \
               and os.path.exists(os.path.join("/var/lib/machines", name, 'fs'))

        machines = sorted(os.listdir('/var/lib/machines'))
        machines = list(filter(exists, machines))
        return (cls(name) for name in machines)

    @cached_property
    def manifest(self):
        try:
            with open('/var/lib/machines/{}/manifest'.format(self.name)) as f:
                return json.loads(f.read())
        except FileNotFoundError:
            return {
                "kostkaVersion": "0.0.2",
                "name": self.name,
                "dependencies": [
                    {"imageName": "debian-jessie"}
                ],
                "networks": [
                    {"type": "bridge",
                     "bridge": "br-lan",
                     "host": trim_interface_name("vb-{}-lan".format(self.name)),
                     "guest": "host0"},
                ]
            }

    @manifest.setter
    def manifest(self, manifest):
        with open('/var/lib/machines/{}/manifest'.format(self.name), 'w') as f:
            f.write(json.dumps(manifest, indent=2))
        return manifest

    @property
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
                pending_deps |= dependencies[name]

        # Then sort it topologically. The list is reversed, because overlayfs
        # will check the mounts in order they are given, so the base fs has to
        # be the last one.
        dependencies = reversed(list(toposort_flatten(dependencies)))
        return ':'.join('/var/lib/machines/{}/overlay.fs'.format(dep) for dep in dependencies)

    @property
    def networks(self):
        return self.manifest.get('networks', [
            {"type": "bridge",
             "bridge": "br-lan",
             "host": trim_interface_name("vb-{}-lan".format(self.name)),
             "guest": "host0"
             },
        ])

    @property
    def bridges(self):
        return list(filter(lambda net: net['type'] == 'bridge', self.networks))

    def add_network(self, bridge, host=None, guest=None, mac=None):
        manifest = self.manifest
        if not host:
            host = "vb-{}-{}".format(self.name, bridge.split('-', 1)[1])
        if not guest:
            guest = "host-{}".format(bridge.split('-', 1)[1])

        if mac:
            mac = '{}:{}:{}:{}:{}:{}'.format(mac[0:2], mac[2:4], mac[4:6], mac[6:8], mac[8:10], mac[10:12])

        if any(filter(lambda net: net['host'] == host, self.networks)):
            raise ValueError('Duplicate host interface name: ' + host)

        if any(filter(lambda net: net['guest'] == guest, self.networks)):
            raise ValueError('Duplicate container interface name: ' + guest)

        if any(filter(lambda net: net.get('guest_address', '') == mac, self.networks)):
            raise ValueError('Duplicate guest mac address: ' + mac)

        if len(host) > 15:
            raise ValueError('Host interface name {} is {} bytes too long.'.format(host, len(host) - 15))

        if len(guest) > 15:
            raise ValueError('Container interface name {} is {} bytes too long.'.format(guest, len(guest) - 15))

        manifest['networks'].append({
            "type": "bridge",
            "bridge": bridge,
            "host": host,
            "guest": guest,
        })

        if mac:
            manifest['networks'][-1]['guest_address'] = mac

        self.manifest = manifest
