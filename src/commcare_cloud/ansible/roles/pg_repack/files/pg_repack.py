#!/usr/bin/env python3
#
# Script run by cron to execute pg_repack under certain conditions
# Must be run as the ``postgres`` user.
#
import argparse
import multiprocessing
import subprocess
import sys
from collections import defaultdict, namedtuple
from datetime import datetime

import psycopg2

import logging

logger = logging.getLogger('pg_repack_script')

GB = 1024**3

TUPLE_QUERY = """
    SELECT relname AS table_name, n_live_tup AS live_tup, n_dead_tup AS dead_tup
    FROM pg_stat_user_tables
    """

SIZE_QUERY = """
    SELECT relname AS table_name, pg_total_relation_size(c.oid) AS total_bytes
    FROM pg_class c
    LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE relkind = 'r' AND nspname = 'public'
    """


def log_state(pre_table_infos, post_table_infos):
    run_date = datetime.utcnow()
    rows_by_table = {
        table.table_name: [run_date, table.table_name, table.live_tup, table.dead_tup, table.total_bytes]
        for table in pre_table_infos
    }
    for table in post_table_infos:
        rows_by_table[table.table_name].append(table.total_bytes)

    rows = [','.join([str(col) for col in row]) for row in rows_by_table.values()]
    with open('/var/log/postgresql/pg_repack_log.csv', 'a') as log:
        log.writelines([f'{row}\n' for row in rows])


class TableInfo(namedtuple('TableInfo', 'table_name live_tup dead_tup total_bytes')):
    def should_repack(self, size_limit, dead_tup_ratio_limit):
        if not self.live_tup:
            return False

        dead_tup_ratio = float(self.dead_tup) / self.live_tup
        return self.total_bytes >= size_limit and dead_tup_ratio >= dead_tup_ratio_limit


def fetchall_as_namedtuple(cursor):
    Result = namedtuple('Result', [col[0] for col in cursor.description])
    return (Result(*row) for row in cursor)


def get_table_info(dbname):
    tables = defaultdict(dict)
    connection = psycopg2.connect(dbname=dbname)
    try:
        with connection.cursor() as cursor:
            cursor.execute(TUPLE_QUERY)
            for row in fetchall_as_namedtuple(cursor):
                tables[row.table_name] = row._asdict()

            cursor.execute(SIZE_QUERY)
            for row in fetchall_as_namedtuple(cursor):
                tables[row.table_name].update(row._asdict())
    finally:
        connection.close()

    return [TableInfo(**table) for table in tables.values()]


def setup_logging(verbosity):
    if not verbosity:
        level = logging.ERROR
    else:
        level = {
            1: logging.WARNING,
            2: logging.INFO,
            3: logging.DEBUG
        }.get(verbosity, logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
    file_handler = logging.FileHandler('/var/log/postgresql/pg_repack_log.log')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logging.getLogger().addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)
    logging.getLogger().addHandler(stream_handler)

    logger.setLevel(logging.DEBUG)


def main():
    parser = argparse.ArgumentParser('PG Repack Script')
    parser.add_argument('--table-size-limit', dest='size_limit', type=int, default=10,
                        help='Only consider tables larger than this size (GB)')
    parser.add_argument('--dead-tup-ratio', dest='dead_tup_ratio_limit', type=float, default=0.1,
                        help='Only consider tables with a ratio of live tuples to dead tuples above this limit')
    parser.add_argument('--pg-repack', help='Path to pg_repack', required=True)
    parser.add_argument('-d', '--database', help='Name fo the database', required=True)
    parser.add_argument('-v', dest='verbosity', help="Verbose logging. Specify multiple times (up to 3).", action='count', default=0)
    parser.add_argument('--dry-run', action='store_true')

    args = parser.parse_args()

    setup_logging(args.verbosity)

    logger.info('\n-------- Starting pg_repack run --------\n')

    size_limit_bytes = args.size_limit * GB
    tables = [
        table for table in get_table_info(args.database)
        if table.should_repack(size_limit_bytes, args.dead_tup_ratio_limit)
    ]

    if not tables:
        logger.info('No tables to pack')
        sys.exit(0)

    table_names = [table.table_name for table in tables]
    logger.info('Preparing to repack: %s', table_names)
    for table in tables:
        logger.debug('\t%s', table)

    repack_command = [
        args.pg_repack, '--no-order', '--wait-timeout=30', f'--dbname={args.database}'
    ] + [f'--table={table}' for table in table_names]

    try:
        cpu_count = multiprocessing.cpu_count()
        jobs = min(len(table_names), cpu_count / 2)
    except NotImplementedError:
        jobs = 1

    if jobs > 1:
        repack_command += [f'--jobs={jobs}']

    if args.dry_run:
        repack_command += ['--dry-run']

    if args.verbosity >= 3:
        repack_command += ['--elevel=DEBUG']

    logger.info('Running pg_repack:\n\t%s', ' '.join(repack_command))
    process = subprocess.Popen(repack_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error_output = process.communicate()
    returncode = process.poll()

    logger.info('\nSTDOUT:\n%s\nSTDERR:\n%s', output.decode(), error_output.decode())
    post_tables = [
        table for table in get_table_info(args.database)
        if table.table_name in table_names
    ]

    log_state(tables, post_tables)
    return returncode

if __name__ == '__main__':
    exit(main())
