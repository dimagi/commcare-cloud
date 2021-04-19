import datetime

from nose.tools import assert_equals
from parameterized import parameterized

from commcare_cloud.commands.utils import timeago

MINUTE = 60
HOUR = MINUTE * 60
DAY = HOUR * 24
MONTH = DAY * (365.0 / 12.0)
YEAR = MONTH * 12


@parameterized([
    (datetime.timedelta(seconds=2), 'just now'),
    (datetime.timedelta(seconds=10), '10 seconds ago'),
    (datetime.timedelta(seconds=12), '12 seconds ago'),
    (datetime.timedelta(seconds=MINUTE), '1 minute ago'),
    (datetime.timedelta(seconds=MINUTE * 3.4), '3 minutes ago'),
    (datetime.timedelta(seconds=HOUR), '1 hour ago'),
    (datetime.timedelta(seconds=HOUR * 2), '2 hours ago'),
    (datetime.timedelta(seconds=DAY), '1 day ago'),
    (datetime.timedelta(seconds=DAY * 4.5), '4 days ago'),
    (datetime.timedelta(seconds=DAY * 7), '1 week ago'),
    (datetime.timedelta(seconds=DAY * 30), '4 weeks ago'),
    (datetime.timedelta(seconds=MONTH), '1 month ago'),
    (datetime.timedelta(seconds=MONTH * 3), '3 months ago'),
    (datetime.timedelta(seconds=YEAR), '1 year ago'),
    (datetime.timedelta(seconds=YEAR * 1.1), '1 year ago'),
    (datetime.timedelta(seconds=YEAR * 2.1), '2 years ago'),
])
def test_timeago(delta, expected):
    assert_equals(timeago(delta), expected)
