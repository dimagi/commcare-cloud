from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import binascii
import hashlib
import six

try:
    from passlib.hash import pbkdf2_sha1
    from passlib.utils import binary
    HAS_PASSLIB = True
except ImportError:
    HAS_PASSLIB = False


def couchdb_password_hash(password, salt, iterations=10):
    salt = salt.encode('utf-8') if isinstance(salt, six.text_type) else salt
    if not HAS_PASSLIB:
        return '-hashed-{hash},{salt}'.format(
            hash=hashlib.sha1(password + salt),
            salt=salt
        )
    else:
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
