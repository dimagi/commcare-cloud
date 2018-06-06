from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
    lookup: pbkdf2_hmac
    short_description: Generate a pbkdf2_hmac from given input
    description:
      - "The pbkdf2_hmac lookup creates a PBKDF2 hash from the given input and returns it along with the salt."
    options:
      _terms:
        description: the value to hash
        required: True
      hash_name:
        description: the desired name of the hash digest algorithm for HMAC, e.g. 'sha1' or 'sha256'.
        default: 'sha256'
        choices: ['sha1', 'sha256', 'sha512']
      salt_length:
        description: length of the salt value to use
        default: 32
      iterations:
        description: number of iterations to perform
        default: 100
"""

EXAMPLES = """
- debug: msg="hash={{item.hash}}, salt={{item.salt}}"
  with_items:
    - "{{ lookup('pbkdf2_hmac', '123abc') }}"
    - "{{ lookup('pbkdf2_hmac', '{{ password_var }} hash_name=sha1 salt_length=64 iterations=100000') }}") }}
"""

RETURN = """
  _raw:
    description:
      - PDKDF2 Hash of the input
    type: complex
    returned: success
    contains:
      hash:
        description: The hashed value
      salt:
        description: The salt value
"""
import random
import string
import hashlib
import binascii

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        ret = []
        for term in terms:
            params = term.split()
            input_value = params[0]
            print(input_value)
            paramvals = {
                'hash_name': 'sha256',
                'salt_length': 32,
                'iterations': 100,
            }

            paramtypes = {
                'salt_length': int,
                'iterations': int,
            }

            # parameters specified?
            try:
                for param in params[1:]:
                    name, value = param.split('=')
                    if name not in paramvals:
                        raise AnsibleError('%s not in expected arguments' % name)
                    if name in paramtypes:
                        try:
                            value = paramtypes[name](value)
                        except ValueError as e:
                            raise AnsibleError('Unexpected type for %s: %s' % (name, e))
                    paramvals[name] = value
            except (ValueError, AssertionError) as e:
                raise AnsibleError("Error parsing '%s': %s" % (term, e))

            salt_length = paramvals['salt_length']
            if not 0 < salt_length <= 256:
                raise AnsibleError('salt_length must be in range 1-256')
            salt_chars = string.ascii_lowercase + string.digits
            salt = ''.join(random.SystemRandom().choice(salt_chars) for _ in range(salt_length))

            hash_name = paramvals['hash_name']
            if hash_name not in hashlib.algorithms:
                raise AnsibleError('%s not supported hash algorithm' % hash_name)

            dk = hashlib.pbkdf2_hmac(hash_name, input_value, salt, paramvals['iterations'])
            ret.append({
                'hash': binascii.hexlify(dk),
                'salt': salt
            })

        return ret
