from setuptools import setup, find_packages

setup(
    name='commcare-cloud',
    description="A tool for managing commcare deploys.",
    long_description="",
    license='BSD-3',
    packages=find_packages('.'),
    entry_points={
        'console_scripts': [
            'commcare-cloud = commcare_cloud:main',
            'cchq = commcare_cloud:main',
        ],
    },
    install_requires=(
        'six',
        'clint'
    ),
)
