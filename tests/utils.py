import logging
from contextlib import contextmanager
from io import open
from unittest import TestCase

from nose.tools import nottest


def get_file_contents(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


@contextmanager
def set_log_level(name, level=logging.WARNING):
    log = logging.getLogger(name)
    original_level = log.level
    try:
        log.setLevel(level)
        yield
    finally:
        log.setLevel(original_level)


@nottest
def test_context(test_case, mgr):
    result = mgr.__enter__()
    if isinstance(test_case, TestCase):
        test_case.addCleanup(mgr.__exit__, None, None, None)
    else:
        test_case.addClassCleanup(mgr.__exit__, None, None, None)
    return result
