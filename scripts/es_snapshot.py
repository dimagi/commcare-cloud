#!/usr/bin/env python3
#
# Script to delete unused snapshot data from Swift object storage
#
# See this doc for info on snapshot storage structure:
#   https://www.elastic.co/blog/found-dive-into-elasticsearch-storage#storing-snapshots

import argparse
import inspect
import json
import logging
import os
import subprocess
from datetime import datetime
from functools import wraps
from io import open
from textwrap import indent

import requests
from requests import HTTPError, Timeout

from commcare_cloud.python_migration_utils import open_for_json_dump

logger = logging.getLogger(__name__)


def retry_timeouts(fn):
    @wraps(fn)
    def _inner(*args, **kwargs):
        retry_count = 0
        while True:
            try:
                return fn(*args, **kwargs)
            except Timeout:
                retry_count += 1
                if retry_count > 2:
                    raise

    return _inner


class SwiftClient(object):
    def __init__(self, auth_url, username, password, container):
        self.auth_url = auth_url
        self.username = username
        self.password = password
        self.container = container

        self.timeout = 30

        self.auth_token = None
        self.storage_url = None

    def authenticate(self):
        if not self.auth_token:
            resp = requests.get(self.auth_url, headers={
                'X-Auth-User': self.username,
                'X-Auth-Key': self.password
            })
            resp.raise_for_status()
            self.storage_url = resp.headers['X-Storage-Url']
            self.auth_token = resp.headers['X-Auth-Token']

    def _auth_headers(self):
        return {
            'X-Auth-Token': self.auth_token
        }

    def list(self, prefix=None, delimiter='/'):
        params = {
            'format': 'json',
        }
        if prefix:
            params['prefix'] = prefix
        if delimiter:
            params['delimiter'] = delimiter
        url = self.storage_url
        if self.container:
            url = '{}/{}'.format(url, self.container)
        resp = requests.get(url, params, headers=self._auth_headers(), timeout=self.timeout)
        return resp.json()

    def get(self, path):
        url = '/'.join([self.storage_url, self.container, path])
        resp = requests.get(url, headers=self._auth_headers(), timeout=self.timeout)
        resp.raise_for_status()
        return resp.content

    def write_content_to_file(self, item, local_dir_path, clobber=False):
        path = item['name']
        expected_md5 = item['hash']
        output_path = os.path.join(local_dir_path, path)
        if self._should_skip(output_path, expected_md5, clobber):
            logger.debug('Skipping (md5 match to existing file) %s: %s', item['name'], sizeof_fmt(item['bytes']))
            return

        logger.debug('Downloading %s: %s', item['name'], sizeof_fmt(item['bytes']))
        os.makedirs(os.path.join(local_dir_path, os.path.dirname(path)), exist_ok=True)
        url = '/'.join([self.storage_url, self.container, path])
        with requests.get(url, headers=self._auth_headers(), timeout=self.timeout, stream=True) as r:
            r.raise_for_status()
            with open(output_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

    def _should_skip(self, output_path, expected_md5, clobber):
        if os.path.exists(output_path) and os.path.isfile(output_path) and expected_md5:
            md5 = subprocess.check_output(['md5sum', output_path]).decode('utf8').split()[0]
            if md5 == expected_md5:
                return True
            if not clobber:
                raise Exception(
                    f'Existing file md5 mismatch: {output_path}, {md5} != {expected_md5}\n'
                    f'Consider using "--clobber" to overwrite existing files.'
                )
            return False

    @retry_timeouts
    def get_json(self, path):
        return json.loads(self.get(path))

    @retry_timeouts
    def delete(self, path):
        url = '/'.join([self.storage_url, self.container, path])
        resp = requests.delete(url, headers=self._auth_headers(), timeout=self.timeout)
        try:
            resp.raise_for_status()
        except HTTPError:
            if resp.status_code != 404:
                raise

    def put_content(self, path, content):
        url = '/'.join([self.storage_url, self.container, path])
        resp = requests.put(url, data=content, headers=self._auth_headers())
        resp.raise_for_status()

    def account_info(self):
        resp = requests.get(self.storage_url, headers=self._auth_headers(), timeout=self.timeout)
        return {
            'quota_bytes': int(resp.headers['X-Account-Meta-Quota-Bytes']),
            'used_bytes': int(resp.headers['X-Account-Bytes-Used']),
            'object_count': int(resp.headers['X-Account-Object-Count']),
            'container_count': int(resp.headers['X-Account-Container-Count']),
        }


def get_matching_index_items(client, index_path, matcher):
    """
    :param client: Swift client
    :param index_path: path to index root in Object Storage
    :param matcher: function which returns True if item matches
    :return: generator of items that can be removed
    """
    shards = []
    logger.info('Processing index %s', index_path)
    for item in client.list(prefix=index_path):
        if 'subdir' in item:
            shards.append(item['subdir'])
        elif matcher(item):
            item['type'] = 'index_metadata'
            yield item

    for shard in shards:
        yield from get_matching_shard_items(client, shard, matcher)


def get_matching_shard_items(client, shard, matcher):
    logger.info('Processing shard %s', shard.split('/')[-2])
    shard_files = {}
    matching_manifests = []
    for item in client.list(prefix=shard):
        path = item.get('name', '')
        name = path.split(shard)[1]
        if name.startswith('__'):
            shard_files[name] = item
        elif matcher(item):
            matching_manifests.append(item)

    matching_files = set()
    for item in matching_manifests:
        manifest_path = item['name']
        logger.debug('Checking matched manifest %s', manifest_path.split('/')[-1])
        manifest = client.get_json(manifest_path)
        for file in manifest['files']:
            if file['name'] in shard_files:
                matching_files.add(file['name'])

    for file in matching_files:
        if file in shard_files:
            item = shard_files[file]
            item['type'] = 'shard_file'
            item['shard'] = shard
            yield item
        else:
            yield {'name': f'{shard}{file}', 'missing': True, 'type': 'shard_file', 'shard': shard}

    for item in matching_manifests:
        item['type'] = 'shard_manifest'
        yield item


def sizeof_fmt(num, suffix='iB'):
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Y', suffix)


def get_items_for_snapshot_version(client, snapshot_version):
    def matcher(item):
        return item.get('name', '').endswith(snapshot_version)

    indices = [
        item['subdir']
        for item in client.list(prefix='indices/')
        if 'subdir' in item
    ]

    for index_path in indices:
        yield from get_matching_index_items(client, index_path, matcher)

    listing = client.list()
    for item in listing:
        if matcher(item):
            item['type'] = 'version_metadata'
            yield item


class Cleanup(object):
    slug = 'clean'
    help = """Remove unused snapshot data"""

    def __init__(self, client, args):
        self.client = client
        self.dry_run = args.dry_run
        self._files_to_keep = {}
        self.keep_list = {
            'index',
        }

    @classmethod
    def add_arguments(cls, parser):
        pass

    def run(self):
        index = json.loads(self.client.get('index'))
        live_snapshots = index['snapshots']

        print('Live snapshot versions:')
        for version in live_snapshots:
            print(f'    {version}')

        confirm = input(
            f"Are you sure you want to delete all files that don't belong to a live ES snapshot? [y/n]")
        if confirm != 'y':
            return

        total_bytes = 0
        count = 0
        for item in self.client.list(delimiter=None):
            if self._can_remove(live_snapshots, item):
                total_bytes += item['bytes']
                count += 1
                logger.info('Deleting %s%s', item['name'], '(dry run)' if self.dry_run else '')
                if not self.dry_run:
                    self.client.delete(item['name'])
                if count % 100 == 0:
                    logger.info('Deleted %s items (%s)', count, sizeof_fmt(total_bytes))

    def _can_remove(self, live_snapshots, item):
        if item['name'] in self.keep_list:
            return False

        for snap in live_snapshots:
            if snap in item['name']:
                return False

        # make sure we don't remove anything that's also part of a live snapshot
        parts = item['name'].split('/')
        if parts[0] == 'indices' and parts[-1].startswith('__'):
            shard_path = '{}/'.format('/'.join(parts[:-1]))
            return item['name'] not in self._shard_files_to_keep(live_snapshots, shard_path)
        return True

    def _shard_files_to_keep(self, live_snapshots, shard_path):
        if shard_path not in self._files_to_keep:
            live_manifests = [f'{shard_path}snapshot-{snap}' for snap in live_snapshots]

            files_to_keep = set()
            for manifest_path in live_manifests:
                logger.debug('Checking live manifest %s', manifest_path)
                try:
                    manifest = self.client.get_json(manifest_path)
                except HTTPError as e:
                    if e.response.status_code == 404:
                        pass
                    else:
                        raise
                else:
                    for file in manifest['files']:
                        name = file['name']
                        files_to_keep.add(f"{shard_path}{name}")
            self._files_to_keep[shard_path] = files_to_keep

        return self._files_to_keep[shard_path]


class Info(object):
    slug = "info"
    help = "Show snapshot repo info"

    def __init__(self, client, args):
        self.client = client
        self.dry_run = args.dry_run
        self.metadata = args.metadata
        self.detail = args.detail

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('--detail', action='store_true', help='Print more detailed output')
        parser.add_argument('--metadata', action='store_true', help='Print raw metadata for each live version')

    def run(self):
        info = self.client.account_info()
        print(
                'Account info: \n'
                '   Objects:    %s\n'
                '   Capacity:   %.1f%% (%s / %s)\n' %
                (
                    info['object_count'],
                    100 * info['used_bytes'] // info['quota_bytes'],
                    sizeof_fmt(info['used_bytes']),
                    sizeof_fmt(info['quota_bytes']),
                )
        )

        index = self.client.get_json('index')
        live_snapshots = index['snapshots']

        print('Live snapshot versions:')
        for snapshot in live_snapshots:
            snap_info = self.client.get_json(f'snapshot-{snapshot}')['snapshot']
            state = snap_info['state']
            suffix = ''
            failure = state != 'SUCCESS'
            if failure:
                total = snap_info['total_shards']
                success = snap_info['successful_shards']
                suffix = f" ({total - success} of {total} shards failed)"
            print(f"    {snapshot} [{state}]{suffix}")
            if self.detail:
                start = datetime.fromtimestamp(snap_info['start_time']/1000)
                end = datetime.fromtimestamp(snap_info['end_time']/1000)
                duration = str(end - start)
                print(f"        Took {duration} from {start.strftime('%Y-%m-%d %H:%M:%S')} to {end.strftime('%Y-%m-%d %H:%M:%S')}")
                if failure:
                    print(indent(json.dumps(snap_info['failures'], indent=4), ' ' * 8))
                print()

            if self.metadata:
                print(indent(json.dumps(snap_info, indent=4), ' ' * 8))
                print()


class DeleteSnapshotVersion(Cleanup):
    slug = 'delete'
    help = """Delete a snapshot version"""

    def __init__(self, client, args):
        super(DeleteSnapshotVersion, self).__init__(client, args)
        self.snapshot_version = args.snapshot_version

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('snapshot_version', help="Name of snapshot version to delete")

    def run(self):
        index = self.client.get_json('index')
        live_snapshots = index['snapshots']

        logger.info('Found %s live snapshots', len(live_snapshots))
        logger.debug('Live snapshots: %s', live_snapshots)

        confirm = input(f"Are you sure you want to delete a snapshot: {self.snapshot_version}? [y/n]")
        if confirm != 'y':
            return

        if self.snapshot_version in live_snapshots:
            live_snapshots.remove(self.snapshot_version)

        total_bytes = 0
        count = 0
        for item in get_items_for_snapshot_version(self.client, self.snapshot_version):
            if self._can_remove(live_snapshots, item):
                total_bytes += item['bytes']
                count += 1
                logger.info('Deleting %s%s', item['name'], '(dry run)' if self.dry_run else '')
                if not self.dry_run:
                    self.client.delete(item['name'])
                if count % 100 == 0:
                    logger.info('Deleted %s items (%s)', count, sizeof_fmt(total_bytes))

        if not self.dry_run:
            index['snapshots'] = live_snapshots
            logger.info('Removing snapshot version from index: %s', self.snapshot_version)
            self.client.put_content('index', json.dumps(index))

    def _can_remove(self, live_snapshots, item):
        if item['type'] != 'shard_file':
            return True

        if item.get('missing', False):
            return False

        # make sure we don't remove anything that's also part of a live snapshot
        return item['name'] not in self._shard_files_to_keep(live_snapshots, item['shard'])


class DownloadSnapshotVersion(object):
    slug = 'download'
    help = """Download all files for a snapshot version"""

    def __init__(self, client, args):
        self.client = client
        self.dry_run = args.dry_run
        self.snapshot_version = args.snapshot_version
        self.download_path = args.download_path
        self.clobber = args.clobber

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('snapshot_version', help="Name of snapshot version to download")
        parser.add_argument('download_path', help="Directory to download the files to")
        parser.add_argument('--clobber', action='store_true', help="Overwrite existing files")

    def run(self):
        index = self.client.get_json('index')
        live_snapshots = index['snapshots']

        logger.info('Found %s live snapshots', len(live_snapshots))
        logger.debug('Live snapshots: %s', live_snapshots)

        if self.snapshot_version not in live_snapshots:
            logger.error(f"Snapshot version '{self.snapshot_version}' not found")
            return 1

        if not self.dry_run:
            with open_for_json_dump(os.path.join(self.download_path, 'index')) as fp:
                json.dump({'snapshots': [self.snapshot_version]}, fp)

        total_bytes = 0
        count = 0
        for item in get_items_for_snapshot_version(self.client, self.snapshot_version):
            if self._should_download(item):
                total_bytes += item['bytes']
                count += 1
                if not self.dry_run:
                    self.client.write_content_to_file(
                        item, self.download_path, self.clobber
                    )
                else:
                    logger.debug('Downloading %s: %s (dry run)', item['name'], sizeof_fmt(bytes))
                if count % 100 == 0:
                    logger.info('Downloaded %s items (%s)', count, sizeof_fmt(total_bytes))

    def _should_download(self, item):
        if item['type'] != 'shard_file':
            return True

        if item.get('missing', False):
            return False

        return True


class VerifySnapshotVersion(object):
    slug = 'verify'
    help = """Verify that a snapshot version is consistent (all referenced files exist)"""

    def __init__(self, client, args):
        self.client = client
        self.dry_run = args.dry_run
        self.snapshot_version = args.snapshot_version
        self.metadata = args.metadata

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('snapshot_version', help="Name of snapshot version to verify")
        parser.add_argument('--metadata', action='store_true', help='Print out snapshot metadata')

    def run(self):
        total_bytes = 0
        count = 0
        bad_items = 0
        for item in get_items_for_snapshot_version(self.client, self.snapshot_version):
            total_bytes += item['bytes']
            count += 1
            logger.debug('Checking %s', item['name'])
            if item.get('missing'):
                bad_items += 1
                logger.warning('Missing shard file: %s', item['name'])
            if count % 100 == 0:
                logger.info('Checked %s items (%s)', count, sizeof_fmt(total_bytes))

        state = f'INVALID ({bad_items} files missing)' if bad_items else 'VALID'
        print(
            f'Snapshot version {self.snapshot_version}:\n'
            f'    File count: {count}\n'
            f'    Total size: {sizeof_fmt(total_bytes)}\n'
            f'    State:      {state}\n'
        )

        if self.metadata:
            metadata = self.client.get_json(f'snapshot-{self.snapshot_version}')
            print(json.dumps(metadata, indent=4))


COMMANDS = [
    Cleanup,
    Info,
    DeleteSnapshotVersion,
    VerifySnapshotVersion,
    DownloadSnapshotVersion,
]


def main():
    parser = argparse.ArgumentParser('Elasticsearch snapshot tool')
    subparsers = parser.add_subparsers(dest='command')
    for command_type in COMMANDS:
        sub = subparsers.add_parser(
            command_type.slug,
            help=inspect.cleandoc(command_type.help).splitlines()[0],
            description=inspect.cleandoc(command_type.help),
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        command_type.add_arguments(sub)

        sub.add_argument(
            "-a", '--auth-url',
            help="Swift Auth URL. Defaults to env[ST_AUTH].", default=os.getenv('ST_AUTH')
        )
        sub.add_argument(
            "-c", '--container',
            help="Swift container. Defaults to env[ST_CONTAINER].", default=os.getenv('ST_CONTAINER')
        )
        sub.add_argument(
            "-u", '--username',
            help="Swift username. Defaults to env[ST_USER].", default=os.getenv('ST_USER')
        )
        sub.add_argument(
            "-p", '--password',
            help="Swift password. Defaults to env[ST_KEY].", default=os.getenv('ST_KEY')
        )
        sub.add_argument('-v', '--verbose', help="Verbose logging", action='count', default=0)
        sub.add_argument('--dry-run', action='store_true')

    args = parser.parse_args()

    missing_args = []
    for arg in ('username', 'password', 'auth_url', 'container'):
        if not getattr(args, arg):
            missing_args.append(arg)

    if missing_args:
        parser.print_help()
        print('\nSome required arguments are missing: {}'.format(', '.join(missing_args)))
        return 1

    command = [c for c in COMMANDS if c.slug == args.command]
    if not command:
        parser.print_help()
        print('\n No command supplied')
        return 1

    command = command[0]

    if not args.verbose:
        level = logging.ERROR
    else:
        level = {
            1: logging.WARNING,
            2: logging.INFO,
            3: logging.DEBUG
        }.get(args.verbose, logging.DEBUG)

    logging.basicConfig(level=level, format='%(asctime)s %(levelname)-8s %(message)s')
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    client = SwiftClient(args.auth_url, args.username, args.password, args.container)
    client.authenticate()

    return command(client, args).run() or 0


if __name__ == '__main__':
    exit(main())
