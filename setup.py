from __future__ import absolute_import

import six
from setuptools import setup, find_packages

install_deps = [
    'ansible-vault==1.1.1',
    'ansible~=2.9.7',
    'argparse>=1.4',
    'attrs>=18.1.0',
    'boto3>=1.9.131',
    'clint',
    'couchdb-cluster-admin>={}'.format("0.5.0" if six.PY2 else "0.6.0"),
    'cryptography>=3.2',
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
    'simplejson',
    'six',
    'tabulate'
]
if six.PY2:
    # moved from requirements-python-lt-2.7.9-ssl-issue.in
    install_deps.extend(["pyOpenSSL", "ndg-httpsclient"])

if six.PY3:
    install_deps.extend(['importlib-metadata==3.1.0'])

test_deps = [
    'mock>=2.0.0',
    'modernize',
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
    install_requires=install_deps,
    tests_require=test_deps,
    extras_require=extras,
)
