import subprocess
from distutils.version import StrictVersion
import click
import requests
from ..config import config
from ..utils import cli, Container
from ..oci import Image, Blob


@cli.group()
def image():
    pass


@image.command()
def ls():
    for img in Image:
        print(img.path.name)


@image.command()
@click.option('--force', is_flag=True, help='Delete and recreate the image if it already exists.')
@click.argument('container')
@click.argument('name')
def create(container, name, force):
    if isinstance(container, str):
        container = Container(container)

    if force:
        try:
            Image.delete(name)
        except FileNotFoundError:
            pass
    try:
        with Image.create(name) as image:
            print("Created image {}. Adding layers.".format(name))
            for layer in reversed(list(container.mount_lowerdirs())):
                print("Adding layer {}.".format(layer))
                image.add_layer(layer)
            print("Adding layer {}.".format(container.path / 'overlay.fs'))
            image.add_layer(container.path / 'overlay.fs')
            print("Writing metadata.")
    except FileExistsError:
        raise
    except:
        Image.delete(name)
        raise


@image.command()
def gc():
    used_hashes = {}
    for img in Image:
        for alg in (img.path / 'blobs').iterdir():
            if alg.name not in used_hashes:
                used_hashes[alg.name] = set()
            for digest in alg.iterdir():
                used_hashes[alg.name].add(digest.name)

    for alg in Blob.root.iterdir():
        if alg.is_file():
            if alg.name.startswith('tmp'):
                print('Removing temporary garbage: {}'.format(alg))
                alg.unlink()
            else:
                print("Unknown file: {}. It probably shouldn't be here.".format(alg))
            continue
        for digest in alg.iterdir():
            if alg.name not in used_hashes or digest.name not in used_hashes[alg.name]:
                print("Removing {}:{}".format(alg.name, digest.name))
                digest.unlink()


@image.command()
@click.argument('name')
def download(name):
    if not config['image_hub']:
        print('Image hub not configured. Cannot download image.')
    name = name.split(':', 1)
    if len(name) == 1:
        versions = requests.get('{}/images/{}'.format(config['image_hub'], name[0])).json()
        versions = sorted((d['name'] for d in versions), key=StrictVersion)
        name.append(versions[-1])
    name, version = name

    print('Downloading {}:{}'.format(name, version))
    Image.download(name, version)


@image.command()
@click.argument('name')
def upload(name):
    if not config['image_upload_host']:
        print('Image upload not configured. Cannot download image.')
    name = name.split(':', 1)
    if len(name) == 1:
        versions = (path.name for path in (Image.root / name[0]).iterdir())
        versions = sorted(versions, key=StrictVersion)
        name.append(versions[-1])
    name, version = name
    print('Uploading {}:{}'.format(name, version))

    image = Image(name, version)
    image.load()

    rsync_command = ['rsync']
    if config['image_upload_ssh_command']:
        rsync_command += ['--rsh={}'.format(config['image_upload_ssh_command'])]

    subprocess.check_call(rsync_command + [
        '-aPR', '--chmod=755', '{}/{}/index.json'.format(name, version),
        '{}:images/'.format(config['image_upload_host'])], cwd=str(Image.root)
    )

    blobs = image.layers[:]
    blobs.append(Blob.from_str(image.manifest))
    blobs.append(Blob.from_str(image.config))
    files = ['{}/{}'.format(blob.digest_alg, blob.digest) for blob in blobs]
    subprocess.check_call(
        rsync_command + ['-aPR', '--chmod=755'] + files +
        ['{}:blobs/'.format(config['image_upload_host'])], cwd=str(Blob.root)
    )
