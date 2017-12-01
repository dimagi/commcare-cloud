from setuptools import setup, find_packages

setup(
    name='commcare-cloud-bootstrap',
    packages=find_packages('.'),
    entry_points={
        'console_scripts': ['commcare-cloud-bootstrap = commcare_cloud_bootstrap:main'],
    },
    install_requires=(
        'six',
        'jsonobject',
        'awscli',
    ),
)
