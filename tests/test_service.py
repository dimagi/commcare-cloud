from __future__ import print_function

from commcare_cloud.commands.ansible.helpers import ProcessDescriptor
from commcare_cloud.commands.ansible.service import get_managed_service_options

process_descriptors = [
        ProcessDescriptor('h1', 'p1', 0, 'p1-0'),
        ProcessDescriptor('h1', 'p1', 1, 'p1-1'),
        ProcessDescriptor('h2', 'p1', 2, 'p1-2'),
        ProcessDescriptor('h1', 'p2', 0, 'p2-0'),
        ProcessDescriptor('h3', 'p3', 0, 'p3-0'),
    ]


def test_get_managed_service_options():
    options = get_managed_service_options(process_descriptors)
    assert options == [
        'p1:[0-2]',
        'p2',
        'p3',
    ], options
