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
        'ansible-vault==1.1.1',
        'ansible==2.4.3',
        'argparse>=1.4',
        'clint',
        'couchdb-cluster-admin>=0.2.1',
        'cryptography==2.1.4',
        'datadog==0.2.0',
        'dimagi-memoized>=1.1.0',
        'dnspython',
        'Fabric==1.10.2',
        'jsonobject>=0.8.0',
        'netaddr',
        'passlib',
        'pycrypto==2.6.1',
        'PyGithub==1.40a1',
        'pytz==2017.2',
        'six',
    ),
    tests_require=test_deps,
    extras_require=extras,
)
