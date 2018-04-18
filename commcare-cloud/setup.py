from setuptools import setup, find_packages

test_deps = [
    'mock==2.0.0',
]
extras = {
    'test': test_deps,
}

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
        'clint',
        'dimagi-memoized>=1.1.0',
        'argparse>=1.4',
        'jsonobject>=0.8.0',
        'couchdb-cluster-admin>=0.2.1',
        'ansible-vault==1.1.1',
    ),
    tests_require=test_deps,
    extras_require=extras,
)
