import os
import re
import subprocess
import time
import threading

from couchdbkit import Server
import requests
from termcolor import colored

import lib.couchdb_custom as couch_info


NODES = [
    {
        'url': 'http://localhost:5984',
        'authenticated_url': 'http://admin:password@localhost:5984',
        'docker_name': 'server-0',
        'color': 'yellow'
    },
    {
        'url': 'http://localhost:15984',
        'authenticated_url': 'http://admin:password@localhost:15984',
        'docker_name': 'server-1',
        'color': 'green'
    },
    {
        'url': 'http://localhost:25984',
        'authenticated_url': 'http://admin:password@localhost:25984',
        'docker_name': 'server-2',
        'color': 'magenta'
    },
]

AB_COMPLETE_REGEX = re.compile(r'Complete requests: *([0-9]+)')
AB_FAILED_REGEX = re.compile(r'Failed requests: *([0-9]+)')

should_create_docs = False  # Boolean used for doc creation thread


def create_docs_thead(url, color, reporting_interval, create_fn):
    # thread that runs and inserts documents
    counters = {
        'total_count': 0,
        'new_count': 0,
        'error_count': 0,
    }
    last_reported_time = 0

    while should_create_docs:
        create_fn(url, counters)

        cur_time = int(time.time())
        if ((cur_time - last_reported_time) > reporting_interval):
            print(
                colored(f'{url}: inserted {counters["total_count"]} total documents, {counters["new_count"]} new documents since last reported',
                        color))
            counters["new_count"] = 0
            last_reported_time = cur_time
    print(colored(f'{url} insertion done: inserted {counters["total_count"]} total documents, {counters["error_count"]} errors', color))


def create_docs(reporting_interval=4, concurrency=True, n=200, c=10):
    def create_simple(url, counters):
        try:
            doc = {"mydoc": "test"}
            Server(url).get_or_create_db("shards").save_doc(doc)
            counters['total_count'] += 1
            counters['new_count'] += 1
        except requests.RequestException:
            counters['error_count'] += 1

    def create_concurrent(url, counters):
        ab_cmd = ['ab', '-p', 'data/large.json', '-T', '"application/json"', '-n', str(n), '-c', str(c), '-q', f'"{url}/shards"']
        try:
            # result = subprocess.run(ab_cmd, capture_output=True, check=True)
            std_out = ""
            p = subprocess.Popen(ab_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            for line in p.stdout:
                std_out += line.decode('utf-8')
            successful = int(AB_COMPLETE_REGEX.search(std_out).group(1))
            failed = int(AB_FAILED_REGEX.search(std_out).group(1))
            counters['total_count'] += successful
            counters['new_count'] += successful
            counters['error_count'] += failed
        except Exception:
            pass

    # start threads
    create_fn = create_concurrent if concurrency else create_simple
    for i in range(len(NODES)):
        Server(NODES[i]['authenticated_url']).get_or_create_db("shards")
        x = threading.Thread(target=create_docs_thead,
                             args=(NODES[i]['url'], NODES[i]['color'], reporting_interval, create_fn))
        x.start()


def node_up(docker_name):
    # brings up a couchdb node via docker-compose
    run_command(['docker-compose', 'start', docker_name])


def node_down(docker_name):
    # takes down a couchdb node via docker-compose
    run_command(['docker-compose', 'stop', docker_name])


def run_command(command_list):
    # runs a command and prints output
    subprocess.run(command_list, stdout=subprocess.PIPE).stdout.decode('utf-8')


def db_is_consistent():
    # Checks to see if db is consistent based on querying individual nodes and checking doc count.
    host = 'localhost'
    port = '5984'
    local_port = '5984'
    user = 'admin'
    password = 'password'
    with requests.Session() as session:
        session.auth = (user, password)
        context = couch_info.SessionContext(host, port, local_port, session)
        shards = couch_info.get_cluster_shard_details(context, [node['url'] for node in NODES])

        doc_counts = {shard['node']: shard['doc_count'] for shard in shards}
        print(doc_counts)

        return len(set(doc_counts.values())) == 1


def cluster_down():
    # docker and docker-compose commands to tear down a cluster
    run_command(['docker-compose', 'down'])
    os.system('docker rm -f $(docker ps -a -q)')
    os.system('docker volume rm $(docker volume ls -q  | grep couchdb-cluster-playground )')


def cluster_up():
    # docker and docker-compose commands to bring up a cluster
    run_command(['docker-compose', 'up', '-d'])
    time.sleep(3)
    # adds nodes into a cluster. Verify by going to http://localhost:5984/_membership and ensuring the "all_nodes" has all 3.
    os.system('curl -X POST -H "Content-Type: application/json" http://admin:password@127.0.0.1:5984/_cluster_setup -d \'{"action": "enable_cluster", "bind_address":"0.0.0.0", "username": "admin", "password":"password", "port": 5984, "node_count": "3", "remote_node": "couchdb-1.docker.com", "remote_current_user": "admin", "remote_current_password": "password" }\'')
    os.system('curl -X POST -H "Content-Type: application/json" http://admin:password@127.0.0.1:5984/_cluster_setup -d \'{"action": "add_node", "host":"couchdb-1.docker.com", "port": "5984", "username": "admin", "password":"password"}\'')
    os.system('curl -X POST -H "Content-Type: application/json" http://admin:password@127.0.0.1:5984/_cluster_setup -d \'{"action": "enable_cluster", "bind_address":"0.0.0.0", "username": "admin", "password":"password", "port": 5984, "node_count": "3", "remote_node": "couchdb-2.docker.com", "remote_current_user": "admin", "remote_current_password": "password" }\'')
    os.system('curl -X POST -H "Content-Type: application/json" http://admin:password@127.0.0.1:5984/_cluster_setup -d \'{"action": "add_node", "host":"couchdb-2.docker.com", "port": "5984", "username": "admin", "password":"password"}\'')
    os.system('curl -X POST -H "Content-Type: application/json" http://admin:password@127.0.0.1:5984/_cluster_setup -d \'{"action": "finish_cluster"}\'')


def one_node_up_down(node_sleep=0):
    # Simple test to see one node go down and back up while threads running in background
    global should_create_docs
    should_create_docs = True
    create_docs()

    # Node is down for node_sleep interval
    node_down(NODES[1]['docker_name'])
    time.sleep(node_sleep)
    node_up(NODES[1]['docker_name'])

    should_create_docs = False
    time.sleep(20)
    if not db_is_consistent():
        print('INCONSISTENT!')


def two_nodes_up_down(node_1_sleep=0, node_2_sleep=0):
    # Simple test to see 2 nodes go down and back up in sequence while threads running in background
    global should_create_docs
    should_create_docs = True
    create_docs()

    # Node 1 is down for node_1_sleep interval
    node_down(NODES[1]['docker_name'])
    time.sleep(node_1_sleep)
    node_up(NODES[1]['docker_name'])

    # Node 2 is down for node_1_sleep interval
    node_down(NODES[2]['docker_name'])
    time.sleep(node_2_sleep)
    node_up(NODES[2]['docker_name'])

    should_create_docs = False
    time.sleep(10)
    if not db_is_consistent():
        print('INCONSISTENT!')


def main():
    # one_node_up_down(node_sleep=4)
    two_nodes_up_down(node_1_sleep=40, node_2_sleep=40)


if __name__ == "__main__":
    main()
