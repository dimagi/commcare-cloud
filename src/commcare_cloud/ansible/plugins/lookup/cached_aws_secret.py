from ansible.plugins.lookup import aws_secret

__metaclass__ = type

DOCUMENTATION = aws_secret.DOCUMENTATION
RETURN = aws_secret.RETURN


class LookupModule(aws_secret.LookupModule):
    _secrets_cache = {}

    def run(self, terms, variables, **kwargs):
        try:
            terms = tuple(terms)
            if terms not in self._secrets_cache:
                print('Fetching', terms)
                try:
                    value = super(LookupModule, self).run(terms, variables, **kwargs)
                except Exception as e:
                    print('Caching error: ', e)
                    value = e
                self._secrets_cache[terms] = value

            value = self._secrets_cache[terms]
        except Exception as e:
            print('The error: ', e)
            raise

        if isinstance(value, Exception):
            raise value
        else:
            return value
