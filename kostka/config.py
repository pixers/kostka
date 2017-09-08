import yaml

config = {
    'image_hub': None,
    'image_upload_host': None,
    'image_upload_ssh_command': None,
    'image_root': '/var/lib/kostka/images',
    'blob_root': '/var/lib/kostka/blobs',
    'layer_root': '/var/lib/kostka/layers',
}

try:
    with open('/etc/kostka.yml') as f:
        yml = yaml.load(f.read())
    for (key, value) in yml.items():
        if key in config:
            config[key] = value
except FileNotFoundError:
    pass

__all__ = config
