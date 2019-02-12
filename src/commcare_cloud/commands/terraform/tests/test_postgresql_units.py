from nose.tools import assert_equal, assert_raises
from parameterized.test import assert_contains

from commcare_cloud.commands.terraform.postgresql_units import convert_to_unit, SECOND, \
    BLOCK_8KB, MS, convert_to_standard_unit


def test_convert_to_unit__time():
    # 1 minute is 60 seconds
    assert_equal(convert_to_unit('1m', SECOND), 60)
    assert_equal(convert_to_unit('1 m', SECOND), 60)


def test_convert_to_unit__bytes():
    # 12 GB is 12 * 1024 * 1024 / 8 "8kB blocks" = 1572864 "8kB blocks"
    assert_equal(convert_to_unit('12GB', BLOCK_8KB), 1572864)
    assert_equal(convert_to_unit('12 GB', BLOCK_8KB), 1572864)


def test_convert_to_unit__bad_input():
    # number part must be an int
    with assert_raises(ValueError) as context:
        convert_to_unit('12.5 GB', BLOCK_8KB)
    assert_contains(context.exception.message, '12.5 GB')


def test_convert_to_unit__mixed_units():
    with assert_raises(ValueError) as context:
        convert_to_unit('1kB', MS)
    assert_contains(context.exception.message, '1kB')
    assert_contains(context.exception.message, 'TimeInMilliseconds')


def test_convert_to_standard_unit__time():
    # authentication_timeout is measured in seconds
    assert_equal(convert_to_standard_unit('authentication_timeout', '1m'), 60)


def test_convert_to_standard_unit__bytes():
    # effective_cache_size is measured in 8kB blocks
    # 11520MB = 11520 * 1024 / 8 "8kB blocks" = 1474560 "8kB blocks"
    assert_equal(convert_to_standard_unit('effective_cache_size', '11520MB'), 1474560)


def test_convert_to_standard_unit__mixed_units():
    # authentication_timeout is measured in seconds
    with assert_raises(ValueError) as context:
        convert_to_standard_unit('authentication_timeout', '1kB')
    assert_contains(context.exception.message, '1kB')
    assert_contains(context.exception.message, 'TimeInMilliseconds')
    assert_contains(context.exception.message, ' (authentication_timeout)')
