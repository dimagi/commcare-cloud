from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import binascii
from passlib.hash import pbkdf2_sha1
from passlib.utils import binary


def couchdb_password_hash(password, salt, iterations=10):
    dk = pbkdf2_sha1.using(rounds=iterations, salt=salt).hash(password)
    decoded = binary.ab64_decode(dk.split('$')[-1])
    return '-pbkdf2-{hash},{salt},{iterations}'.format(
        hash=binascii.hexlify(decoded),
        salt=salt,
        iterations=iterations
    )


class FilterModule(object):
    def filters(self):
        return {
            'couchdb_password_hash': couchdb_password_hash,
        }
