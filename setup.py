from setuptools import setup, find_packages

setup(
    name='kostka',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
        'requests',
        'toposort',
        'pystache',
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
    },
)
