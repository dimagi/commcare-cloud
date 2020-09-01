import json
import os
import cPickle
import random
import time

from ansible.plugins.lookup import aws_secret
from cryptography.fernet import Fernet, InvalidToken

__metaclass__ = type


DOCUMENTATION = aws_secret.DOCUMENTATION
RETURN = aws_secret.RETURN


class LookupModule(aws_secret.LookupModule):

    def run(self, terms, variables, **kwargs):
        terms = tuple(terms)
        term, = terms
        value = self.get_cache(term, inventory_dir=variables['inventory_dir'])
        try:
            if value is Ellipsis:
                print('Fetching', terms)
                try:
                    value = super(LookupModule, self).run(terms, variables, **kwargs)
                except Exception as e:
                    print('Caching error: ', e)
                    value = e
                self.set_cache(term, value, inventory_dir=variables['inventory_dir'])
        except Exception as e:
            print('The error: ', e)
            raise

        if isinstance(value, Exception):
            raise value
        else:
            return value

    def get_cache(self, term, inventory_dir):
        try:
            with open(self._secrets_cache_filename(term, inventory_dir=inventory_dir), 'rb') as f:
                contents = f.read()
                if contents == b'FETCHING':
                    time.sleep(1)
                    return self.get_cache(term, inventory_dir=inventory_dir)
                return cPickle.loads(Fernet(self._encryption_key()).decrypt(contents))
        except (IOError, InvalidToken, cPickle.UnpicklingError):
            with open(self._secrets_cache_filename(term, inventory_dir=inventory_dir), 'wb') as f:
                f.write(b'FETCHING')
            return Ellipsis

    def set_cache(self, term, value, inventory_dir):
        try:
            with open(self._secrets_cache_filename(term, inventory_dir=inventory_dir), 'wb') as f:
                f.write(Fernet(self._encryption_key()).encrypt(cPickle.dumps(value)))
        except Exception as e:
            print("it is ", e)

    def _encryption_key(self):
        return os.environ['AWS_SECRETS_CACHE_KEY']

    def _secrets_cache_filename(self, term, inventory_dir):
        dir_name = os.path.join(inventory_dir, '.generated')
        if not os.path.isdir(dir_name):
            os.mkdir(dir_name)

        return os.path.join(dir_name, 'secrets_cache_{}'.format(hash(term)))
