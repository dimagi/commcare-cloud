from setuptools import setup, find_packages

test_deps = [
    'mock>=2.0.0',
    'nose>=1.3.7',
    'parameterized>=0.6.1',
]
extras = {
    'test': test_deps,
}

setup(
    name='commcare-cloud',
    description="A tool for managing commcare deploys.",
    long_description="",
    license='BSD-3',
    include_package_data=True,
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    entry_points={
        'console_scripts': [
            'commcare-cloud = commcare_cloud.commcare_cloud:main',
            'cchq = commcare_cloud.commcare_cloud:main',
            'manage-commcare-cloud = commcare_cloud.manage_commcare_cloud.manage_commcare_cloud:main',
        ],
    },
    install_requires=(
        'ansible-vault==1.1.1',
        # Ansible 2.5.1 through 2.6.*
        # are affected by https://github.com/ansible/ansible/issues/44065
        # When 2.7 comes out, if not affected, should change this to >=2.7
        'ansible==2.5.0',
        'argparse>=1.4',
        'attrs>=18.1.0',
        'clint',
        'couchdb-cluster-admin>=0.4.1',
        'cryptography>=2.3',  # security update
        'datadog==0.2.0',
        'dimagi-memoized>=1.1.0',
        'dnspython',
        'Fabric==1.10.2',
        # can remove once requests bumps its version requirement
        # https://github.com/requests/requests/issues/4681
        'idna==2.6',
        'jinja2-cli',
        'jsonobject>=0.9.0',
        'netaddr',
        'passlib',
        'pycryptodome>=3.6.6',  # security update
        'PyGithub==1.40a1',
        'pytz==2017.2',
        'six',
    ),
    tests_require=test_deps,
    extras_require=extras,
)
