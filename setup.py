from setuptools import setup, find_packages

test_deps = [
    'mock>=2.0.0',
    'nose>=1.3.7',
    'parameterized>=0.6.1',
]
aws_deps = [
    'awscli',
]
extras = {
    'test': test_deps,
    'aws': aws_deps,
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
        'ansible>=2.9.4',
        'argparse>=1.4',
        'attrs>=18.1.0',
        'boto3>=1.9.131',
        'clint',
        'couchdb-cluster-admin>=0.5.0',
        # 2.8 solves issue on MacOS Catalina
        # https://github.com/pypa/pip/issues/7254
        # but 2.9 fails to compile
        'cryptography~=2.8.0',
        'datadog==0.2.0',
        'dimagi-memoized>=1.1.0',
        'dnspython',
        'Fabric3>=1.10.2,<1.11',
        # can remove once requests bumps its version requirement
        # https://github.com/requests/requests/issues/4681
        'idna==2.6',
        'jinja2-cli',
        'jsonobject>=0.9.0',
        'netaddr',
        'passlib',
        'pycryptodome>=3.6.6',  # security update
        'PyGithub>=1.43.3',
        'pytz==2017.2',
        'six',
        'tabulate'
    ),
    tests_require=test_deps,
    extras_require=extras,
)
