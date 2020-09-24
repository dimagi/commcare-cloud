from __future__ import unicode_literals
class PreindexNotFinished(Exception):
    """Thrown when a preindex of the database is not finished in a certain time period"""


class NoHostsMatch(Exception):
    pass
