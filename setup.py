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
    ],
    entry_points='''
        [console_scripts]
        kostka=kostka.kostka:cli
    ''',
)
