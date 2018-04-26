from __future__ import print_function

from nose_parameterized import parameterized

from commcare_cloud.commands.ansible.helpers import ProcessDescriptor
from commcare_cloud.commands.ansible.service import get_managed_service_options, get_processes_by_host

process_descriptors = [
        ProcessDescriptor('h1', 'p1', 0, 'p1-0'),
        ProcessDescriptor('h1', 'p1', 1, 'p1-1'),
        ProcessDescriptor('h2', 'p1', 2, 'p1-2'),
        ProcessDescriptor('h1', 'p2', 0, 'p2-0'),
        ProcessDescriptor('h3', 'p3', 0, 'p3-0'),
        ProcessDescriptor('h4', 'p3', 0, 'p3-0'),
    ]


def test_get_managed_service_options():
    options = get_managed_service_options(process_descriptors)
    assert options == [
        'p1:[0-2]',
        'p2',
        'p3',
    ], options


@parameterized([
    # no filtering
    (['h1', 'h2', 'h3', 'h4'], process_descriptors, None, {
        ('h1',): ['p1-0', 'p1-1', 'p2-0'],
        ('h2',): ['p1-2'],
        ('h3','h4'): ['p3-0']
    }),
    # filter hosts
    (['h1', 'h3'], process_descriptors, None, {
        ('h1',): ['p1-0', 'p1-1', 'p2-0'],
        ('h3',): ['p3-0']
    }),
    # filter processes
    (['h1', 'h2', 'h3', 'h4'], process_descriptors, 'p3', {
        ('h3', 'h4'): ['p3-0'],
    }),
    # filter process and host
    (['h3'], process_descriptors, 'p3', {
        ('h3',): ['p3-0'],
    }),
    # filter process with num
    (['h1', 'h2'], process_descriptors, 'p1:1', {
        ('h1',): ['p1-1'],
    }),
    # filter just process for process with multiple instances
    (['h1', 'h2'], process_descriptors, 'p1', {
        ('h1',): ['p1-0', 'p1-1'],
        ('h2',): ['p1-2'],
    }),
    # filter multiple services
    (['h1', 'h2'], process_descriptors, 'p1:1,p2:0', {
        ('h1',): ['p1-1', 'p2-0'],
    })
])
def test_get_processes_by_host(all_hosts, process_descriptors, process_pattern, expected_response):
    processes_by_host = get_processes_by_host(all_hosts, process_descriptors, process_pattern)

    # sort for comparison
    processes_by_host = {
        hosts: sorted(process)
        for hosts, process in processes_by_host.items()
    }
    assert processes_by_host == expected_response, processes_by_host
