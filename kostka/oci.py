import json
import io
from pathlib import Path
import hashlib
import platform
import subprocess
import shutil
import requests
from .config import config

class Blob:
    root = Path(config['blob_root'])

    @classmethod
    def from_dirs(cls, *directories):
        (Blob.root / 'sha256').mkdir(exist_ok=True, parents=True)
        dest = (Blob.root / 'tmp')
        dest.mkdir()
        try:
            for directory in directories:
                #copytree(directory, dest)
                # Using rsync so that devices are also copied
                subprocess.check_call(['rsync', '-aHAX', str(directory) + '/', dest])

            tar = subprocess.Popen(['tar',
                '--sort=name', '--owner=0', '--group=0',
                '--numeric-owner', '-cp', '--directory={}'.format(dest),
                '--mtime=2000-01-01 00:00Z', '.'
            ], stdout=subprocess.PIPE)

            # We cannot use `tar -z` here, because it won't pass `-n` to gzip,
            # and as a consequence, won't be deterministic
            gzip = subprocess.Popen(['gzip', '-n', '-'], stdin=tar.stdout, stdout=subprocess.PIPE)
            tar.stdout.close()

            with (Blob.root / 'tmp.tar.gz').open('wb') as f:
                sha = hashlib.sha256()
                while gzip.stdout.readable():
                    chunk = gzip.stdout.read(1024*1024)
                    if len(chunk) == 0:
                        break
                    f.write(chunk)
                    sha.update(chunk)
                digest = sha.hexdigest()
                shutil.move(Blob.root / 'tmp.tar.gz', Blob.root / 'sha256' / digest)
                return cls('sha256', digest)
        finally:
            shutil.rmtree(dest)

    @classmethod
    def from_str(cls, content):
        if not isinstance(content, str):
            content = json.dumps(content)

        sha = hashlib.sha256(content.encode('utf-8')).hexdigest()
        blob = cls('sha256', sha)
        blob.path.write_text(content)
        return blob

    def __init__(self, digest_alg, digest=None, root=None):
        if digest is None and ':' in digest_alg:
            digest_alg, digest = digest_alg.split(':', 1)

        self.root = root or Blob.root
        self.digest_alg = digest_alg
        self.digest = digest

    def download(self, progressbar=True):
        from tqdm import tqdm
        if self.path.exists():
            return self # Do nothing if the blob is already downloaded
        url = '{}/blobs/{}/{}'.format(config['image_hub'], self.digest_alg, self.digest)
        req = requests.get(url, stream=True)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        total_size = int(req.headers.get('content-length', 0))
        try:
            if progressbar:
                progressbar = tqdm(total=total_size, unit='B', unit_scale=True, leave=False)
            with self.path.open('wb') as f:
                for chunk in req.iter_content(chunk_size=1024*1024):
                    if progressbar:
                        progressbar.update(len(chunk))
                    f.write(chunk)
        finally:
            if progressbar:
                progressbar.close()
        return self

    def __len__(self):
        return (self.root / self.digest_alg / self.digest).stat().st_size
    
    @property
    def path(self) -> Path:
        return self.root / self.digest_alg / self.digest

class Layer(Blob):
    root = Path(config['layer_root'])

    @classmethod
    def from_blob(cls, blob: Blob, root=None):
        return cls(blob.digest_alg, blob.digest, root, blob.root)

    def __init__(self, digest_alg, digest=None, root=None, blob_root=None):
        super().__init__(digest_alg, digest, blob_root)
        self.layer_root = root or Layer.root

    @property
    def fs_path(self) -> Path:
        return self.layer_root / self.digest_alg / self.digest

    def extract(self):
        if self.fs_path.exists():
            return
        self.fs_path.mkdir(parents=True)
        shutil.unpack_archive(self.path, self.fs_path, 'gztar')

class ImageMeta(type):
    def __contains__(self, item):
        return (Image.root / item).exists()

    def __iter__(self):
        for directory in Image.root.iterdir():
            for version in Image.root.iterdir():
                yield Image('{}:{}'.format(directory.name, version.name))

class Image(metaclass=ImageMeta):
    root = Path(config['image_root'])

    @staticmethod
    def layout():
        return {
            'imageLayoutVersion': '1.0.0',
        }

    @staticmethod
    def digest(content):
        if hasattr(content, 'digest'):
            return 'sha256:' + content.digest
        if not isinstance(content, str):
            content = json.dumps(content)
        return 'sha256:' + hashlib.sha256(content.encode('utf-8')).hexdigest()

    @classmethod
    def descriptor(cls, type, content):
        return {
            'mediaType': 'application/vnd.oci.image.{}'.format(type),
            'size': len(content),
            'digest': cls.digest(content),
        }
    
    @classmethod
    def create(cls, name, version=None):
        return cls(name, version=None, create=True)

    @classmethod
    def delete(cls, name):
        shutil.rmtree(cls.root / name)

    @classmethod
    def download(cls, name, version, progressbar=True):
        index_url = '{}/images/{}/{}/index.json'.format(config['image_hub'], name, version)
        index = requests.get(index_url).json()

        with cls(name, version, create=True) as image:
            manifest = image.blob(Blob(index['manifests'][0]['digest']).download())
            manifest = json.loads(manifest.path.read_text())

            for layer in manifest['layers']:
                blob = image.blob(Layer(layer['digest']).download(progressbar))
                image.layers.append(blob)

            return image
        

    def __init__(self, name, version=None, create=False, root=None):
        self.root = root or Image.root
        if version is None:
            name, version = name.split(':', 1)
        self.path = self.root / name / version
        self.create = create
        self.layers = []
        self.loaded = False

        if self.create:
            self.loaded = True
            self.path.mkdir(parents=True)
            (self.path / 'blobs' / 'sha256').mkdir(parents=True, exist_ok=True)

    def load(self):
        index = json.loads((self.path / 'index.json').read_text())
        manifest = Blob(index['manifests'][0]['digest'])
        manifest = json.loads(manifest.path.read_text())
        for layer in manifest['layers']:
            self.layers.append(Layer(layer['digest']))
        self.loaded = True
        return self
        

    @property
    def index(self):
        if not self.loaded:
            self.load()
        return {
            'schemaVersion': 2,
            'manifests': [self.descriptor('manifest.v1+json', self.manifest)],
        }

    @property
    def manifest(self):
        if not self.loaded:
            self.load()
        return {
            'schemaVersion': 2,
            'config': self.descriptor('config.v1+json', self.config),
            'layers': [
                self.descriptor('layer.v1.tar+gzip', layer)
                for layer in self.layers
            ],
        }

    @property
    def config(self):
        if not self.loaded:
            self.load()
        return {
            'architecture': platform.machine(),
            'os': platform.system().lower(),
            'rootfs': {
                'type': 'layers',
                'diff_ids': [layer.digest for layer in self.layers]
            },
        }

    def contentaddr(self, content):
        alg, digest = self.digest(content).split(':',1)
        return self.path / 'blobs' / alg / digest

    def blob(self, blob: Blob):
        path = (self.path / 'blobs' / blob.digest_alg / blob.digest)
        if not path.exists():
            path.symlink_to(blob.path)
        return blob

    def write(self):
        if not self.loaded:
            self.load()

        self.blob(Blob.from_str(self.manifest))
        self.blob(Blob.from_str(self.config))

        (self.path / 'oci-layout').write_text(json.dumps(self.layout()))
        (self.path / 'index.json').write_text(json.dumps(self.index))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.write()

    def add_layer(self, *directories):
        if not self.loaded:
            self.load()

        blob = Layer.from_dirs(self.path, *directories)
        self.blob(blob)
        self.layers.append(blob)

    def extract(self):
        '''Extracts layers so they can be used in a container'''
        for layer in self.layers:
            layer.extract()

# This function is currently unused, because it can't copy special files, such as devices.
def copytree(src, dest):
    import os
    '''Copies contents of src into dest. The main difference from shutil.copytree
       is that dest must exist.
       Also, the implementation is simplified and raises early if an error occurs.
    '''
    for name in os.listdir(src):
        srcname = os.path.join(src, name)
        dstname = os.path.join(dest, name)
        if os.path.islink(srcname):
            os.symlink(os.readlink(srcname), dstname)
            shutil.copystat(srcname, dstname, follow_symlinks=False)
        elif os.path.isdir(srcname):
            os.makedirs(dstname)
            copytree(srcname, dstname)
        else:
            shutil.copy2(srcname, dstname)
