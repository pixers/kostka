from setuptools import setup, find_packages

setup(
    name='kostka',
    version='0.2',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
        'requests',
        'toposort',
        'pystache',
        'pyyaml',
        'tqdm',
    ],
    entry_points={
        'console_scripts': 'kostka = kostka.kostka:cli',
        'kostka.create': [
            'mount = kostka.mount:create',
            'network = kostka.network:create',
        ],
        'kostka.update_sd_units': [
            'mount = kostka.mount:update_sd_units',
            'network = kostka.network:update_sd_units',
        ],
        'kostka.container': [
            'mount = kostka.mount:MountContainer',
            'network = kostka.network:NetworkContainer',
        ],
        'kostka.rm': [
            'mount = kostka.mount:rm',
        ],
        'kostka.copy': [
            'mount = kostka.mount:copy',
        ],
        'kostka.stop': [
            'mount = kostka.mount:stop',
        ],
    },
)
