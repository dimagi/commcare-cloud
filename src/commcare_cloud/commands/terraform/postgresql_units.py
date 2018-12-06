import re

import six


class Bytes(int):
    pass


class TimeInMilliseconds(int):
    pass


BYTE = Bytes(1)
KB = Bytes(1024 * BYTE)
MB = Bytes(1024 * KB)
GB = Bytes(1024 * MB)
# Postgres measures some things in terms of number of 8-kB blocks
BLOCK_8KB = Bytes(8 * KB)

MS = TimeInMilliseconds(1)
SECOND = TimeInMilliseconds(1000 * MS)
MINUTE = TimeInMilliseconds(60 * SECOND)

UNITS = {
    'kB': KB,
    'MB': MB,
    'GB': GB,
    'ms': MS,
    's': SECOND,
    'm': MINUTE,
}

UNITS_BY_PARAM = {
    'effective_cache_size': BLOCK_8KB,
    'segment_size': BLOCK_8KB,
    'shared_buffers': BLOCK_8KB,
    'temp_buffers': BLOCK_8KB,
    'wal_buffers': BLOCK_8KB,
    'wal_segment_size': BLOCK_8KB,
    'log_rotation_size': KB,
    'log_temp_files': KB,
    'maintenance_work_mem': KB,
    'max_stack_depth': KB,
    'ssl_renegotiation_limit': KB,
    'temp_file_limit': KB,
    'work_mem': KB,
    'log_rotation_age': MINUTE,
    'autovacuum_vacuum_cost_delay': MS,
    'bgwriter_delay': MS,
    'deadlock_timeout': MS,
    'lock_timeout': MS,
    'log_autovacuum_min_duration': MS,
    'log_min_duration_statement': MS,
    'max_standby_archive_delay': MS,
    'max_standby_streaming_delay': MS,
    'statement_timeout': MS,
    'vacuum_cost_delay': MS,
    'wal_receiver_timeout': MS,
    'wal_sender_timeout': MS,
    'wal_writer_delay': MS,
    'archive_timeout': SECOND,
    'authentication_timeout': SECOND,
    'autovacuum_naptime': SECOND,
    'checkpoint_timeout': SECOND,
    'checkpoint_warning': SECOND,
    'post_auth_delay': SECOND,
    'pre_auth_delay': SECOND,
    'tcp_keepalives_idle': SECOND,
    'tcp_keepalives_interval': SECOND,
    'wal_receiver_status_interval': SECOND,
}


def convert_to_unit(value, new_unit):
    # type: (object, object) -> object
    """
    Converts string containing unit to integer measuring quantity in new unit

    >>> convert_to_unit('1m', SECOND)
    60
    """
    match = re.match(r'^(?P<number>\d+) *(?P<unit>\w+)$', value)
    if match is None:
        raise ValueError(
            "Values must be given in '<int> <unit>' format (space optional): {}"
            .format(value)
        )
    number_str, unit_str = match.groups()
    number = int(number_str)
    unit = UNITS[unit_str]

    # make sure the units are for the same quantity (time / bytes):
    if type(unit) != type(new_unit):
        raise ValueError("{} can't be measured as unit {}"
                         .format(value, type(new_unit).__name__))

    # Unit arithmetic: number * unit = x * new_unit
    # So: x = number * unit / new_unit
    return number * unit / new_unit


def convert_to_standard_unit(param, value):
    if param not in UNITS_BY_PARAM:
        return value
    elif isinstance(value, six.integer_types):
        return value
    else:
        try:
            return convert_to_unit(value, new_unit=UNITS_BY_PARAM[param])
        except ValueError as e:
            e.message += " ({})".format(param)
            raise
