from setuptools import find_packages, setup

install_deps = [
    'ansible-vault==2.1.0',
    'ansible~=4.3',
    'ansible-inventory==0.6.4',
    'argparse>=1.4',
    'boto3',
    'attrs',
    'clint',
    'couchdb-cluster-admin',
    'cryptography',
    'datadog>=0.2.0',
    'dimagi-memoized>=1.1.0',
    'dnspython',
    'gitpython',
    'jinja2-cli',
    'jsonobject',
    'netaddr',
    'passlib',
    'pycryptodome>=3.6.6',  # security update
    'PyGithub',
    'pytz',
    'simplejson',
    'tabulate'
]
test_deps = [
    'docopt',
    'nose @ git+https://github.com/dimagi/nose.git@06dff28bbe661b9d032ce839ea0ec8e9eaf6f337',
    'parameterized>=0.6.1',
    'requests-mock',
    'sh',
    'testil',
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
