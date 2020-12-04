import os
import subprocess
import time
import threading

from couchdbkit import Server
import requests

import lib.couchdb_custom as couch_info


NODES = [
    {
        'url': 'http://localhost:5984',
        'docker_name': 'server-0'
    },
    {
        'url': 'http://localhost:15984',
        'docker_name': 'server-1'
    },
    {
        'url': 'http://localhost:25984',
        'docker_name': 'server-2'
    },
]

should_create_docs = False  # Boolean used for doc creation thread


def create_docs(reporting_interval=4):
    def create_docs_thead():
        # thread that runs and inserts documents
        total_count = 0
        last_reported_time = 0
        new_count = 0

        while should_create_docs:
            doc = {"mydoc": "test"}
            db.save_doc(doc)
            total_count += 1
            new_count += 1
            cur_time = int(time.time())
            if ((cur_time - last_reported_time) > reporting_interval):
                print(f'inserted {total_count} total documents, {new_count} new documents since last reported')
                new_count = 0
                last_reported_time = cur_time
        print(f'insertion done: inserted {total_count} total documents')

    # create database and start thread
    server = Server("http://admin:password@localhost:5984")
    db = server.get_or_create_db("shards")
    x = threading.Thread(target=create_docs_thead)
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
    two_nodes_up_down(node_1_sleep=40, node_2_sleep=40)


if __name__ == "__main__":
    main()
