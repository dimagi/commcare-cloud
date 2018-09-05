import getpass

import requests
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('username')
    parser.add_argument('-p', '--password')

    args = parser.parse_args()

    if not args.password:
        args.password = getpass.getpass("Password")

    auth = (args.username, args.password)

    control_node = '100.71.184.25'
    node_map = {
        "10.247.164.74": '100.71.184.25',
        "10.247.164.76": "100.71.184.8",
        "10.247.164.75": "100.71.184.9",
        "10.247.164.83": "100.71.184.6",
        "": "100.71.184.17",
    }

    print('\nUPDATING MEMBERSHIP\n')
    node_url = 'http://{}:15986/_nodes/couchdb@{{}}'.format(control_node)
    for old_node, new_node in node_map.items():
        if old_node:
            res = requests.get(node_url.format(old_node), auth=auth)
            if res.status_code == 200:
              rev = res.json()['_rev']
              url = node_url.format(old_node)
              res = requests.delete('{}?rev={}'.format(url, rev), auth=auth)
              print('DELETE node {}'.format(old_node), res.status_code)

        res = requests.get(node_url.format(new_node), auth=auth)
        if res.status_code != 200:
          res = requests.put(node_url.format(new_node), data="{}", auth=auth)
          print('ADD node {}'.format(new_node), res.status_code)


    print('\nUPDATING DATABASE DOCS\n')

    dbs = [
        "commcarehq",
        "commcarehq__apps",
        "commcarehq__auditcare",
        "commcarehq__domains",
        "commcarehq__fixtures",
        "commcarehq__fluff-bihar",
        "commcarehq__m4change",
        "commcarehq__meta",
        "commcarehq__mvp-indicators",
        "commcarehq__receiverwrapper",
        "commcarehq__users",
    ]

    dbs_url = 'http://{}:15986/_dbs/{{}}'.format(control_node)
    for db in dbs:
        res = requests.get(dbs_url.format(db), auth=auth)
        db_doc = res.text
        new_db_doc = db_doc
        for old_node, new_node in node_map.items():
            if old_node:
                new_db_doc = new_db_doc.replace(old_node, new_node)
        if db_doc != new_db_doc:
          res = requests.put(dbs_url.format( db), data=new_db_doc, auth=auth)
          print('UPDATE DB {}'.format(db), res.status_code)

    print('\nRE-CREATING SYSTEM DATABASES\n')
    system_dbs = [
        "_global_changes",
        "_replicator",
        "_users"
    ]
    for db in system_dbs:
        res = requests.get('http://{}:15986/_dbs/{}'.format(control_node, db), auth=auth)
        create = res.status_code == 404
        if res.status_code == 200:
          db_doc = res.json()
          create = 'couchdb@10.247.164.12' in db_doc['by_node']
          if create:
            rev = db_doc['_rev']
            res = requests.delete('http://{}:15986/_dbs/{}{}'.format(control_node, db, '?rev={}'.format(rev)), auth=auth)
            print('DELETE db {}'.format(db), res.status_code)

        if create:
          res = requests.put('http://{}:15984/{}'.format(control_node, db), data="{}", auth=auth)
          print("CREATE db {}".format(db), res.status_code)

if __name__ == '__main__':
    main()
