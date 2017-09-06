from .cached_property import cached_property
import os
import json
from .plugins import extend_with
from pathlib import Path


class BaseContainer:
    metadata_dir = Path('/var/lib/machines')

    def __init__(self, name):
        self.name = name
        self.path = self.metadata_dir / self.name

    # For now, we assume that all containers have a directory in the metadata directory
    @classmethod
    def all(cls):
        def exists(container):
            return container.name == os.path.basename(container.name) \
               and container.exists()

        machines = sorted(os.listdir(cls.metadata_dir))
        machines = list(cls(name) for name in machines)
        machines = list(filter(exists, machines))

        return machines

    def exists(self):
        return os.path.exists(self.manifest_path())

    def default_manifest(self):
        super_dict = {}
        if hasattr(super(), 'default_manifest'):
            super_dict = super().default_manifest()

        super_dict.update({
            "kostkaVersion": "0.0.2",
            "name": self.name,
        })
        return super_dict

    def manifest_path(self):
        return os.path.join(self.metadata_dir, self.name, 'manifest')

    @cached_property
    def manifest(self):
        try:
            with open(self.manifest_path()) as f:
                return json.loads(f.read())
        except FileNotFoundError:
            return self.default_manifest()

    @manifest.setter
    def manifest(self, manifest):
        with open(self.manifest_path(), 'w') as f:
            f.write(json.dumps(manifest, indent=2))
        return manifest


@extend_with('kostka.container')
class Container(BaseContainer):
    pass
