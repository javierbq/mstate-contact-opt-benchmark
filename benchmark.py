#!/usr/bin/env python

from argparse import ArgumentParser
import logging
import subprocess
import time
from glob import glob
from git import Repo
import shutil
import os
import pxssh
from getpass import getuser
import redis
from utils import get_cmd_from_yaml, run_target

parser = ArgumentParser()

parser.add_argument(
    '-enviroment',
    default='rosetta_utils_dev',
    help='Name of a virtualenv under ~/.virtualenvs/ or path to virtual enviroment.'
)
parser.add_argument(
    '-head',
    default='dig39-test',
    help='Head dig to send the simulation to R@H.'
)
parser.add_argument(
    '-test',
    action='store_true',
    help='run test structure throught 3 iterations of the optimization protocol.'
)

parser.add_argument(
    '-verbose',
    action='store_true',
    help='Set logging level to  DEBUG.'
)

parser.add_argument(
    '-dummy_run',
    action='store_true',
    help="Don't run the tests, used during development."
)
parser.add_argument(
    '-redis_host_port',
    metavar=' host port',
    nargs=2,
    default=('havic', 6379),
    help='Store progress in a redis server.'
)
parser.add_argument(
    '-cpu_slots',
    default=10,
    help='max cpu slots to be used in the head machine.'
)
parser.add_argument(
    '-reset_test_counter',
    action='store_true',
    help="Reset test counter."
)
parser.add_argument(
    '-reset_benchmark_counter',
    action='store_true',
    help="Reset benchmark counter."
)
args = parser.parse_args()

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)
logger_utils = logging.getLogger('benchmark.utils')
logger_utils.setLevel(logging.DEBUG if args.verbose else logging.INFO)

ch = logging.StreamHandler()
ch.setFormatter(formatter)
ch.setLevel(logging.DEBUG if args.verbose else logging.INFO)
logger.addHandler(ch)
logger_utils.addHandler(ch)

redis_server = redis.Redis(host='havic', port=6379)

redis_server.set('slots:' + args.head, args.cpu_slots)

home = os.path.expanduser('~')
if os.path.exists(os.path.abspath('%s/.virtualenvs/%s' % (home, args.enviroment))):
    path_to_enviroment = os.path.abspath(
        '%s/.virtualenvs/%s' % (home, args.enviroment))
elif os.path.exists(args.enviroment):
    path_to_enviroment = args.enviroment
else:
    logger.error('Enviroment not found!')
    exit(1)

logger.debug("Path to enviroment: " + path_to_enviroment)

# check branch version and state of the head

base_dir = os.path.dirname(os.path.realpath(__file__))
input_dir = base_dir + '/input'
session = pxssh.pxssh()
logger.info('Connecting to %s' % args.head)
session.login(args.head, getuser())
if os.path.exists('%s/.bashrc' % home):
    logger.info('sourcing ~/.bashrc')
    session.sendline('source %s/.bashrc' % home)
session.sendline('source %s/bin/activate' % path_to_enviroment)
session.sendline('cd %s' % base_dir)
session.prompt()
if args.test:
    if args.reset_test_counter:
        redis_server.set('test_counter', 0)
    logger.info('Running test')
    test_id = 'test_%s' % str(redis_server.incr('test_counter')).zfill(4)
    test_time = time.strftime("%Y-%m-%d-%H:%M:%S")
    if redis_server.get('latest_test'):
        redis_server.lpush('old_tests', redis_server.get('latest_test'))
    redis_server.set('latest_test', test_id)
    test_dir = 'test_results/%s' % test_id

    if os.path.exists('test_results/latest'):
        os.unlink('test_results/latest')
    os.symlink(test_id, 'test_results/latest')

    logger.debug('Making a copy of the test directory')
    shutil.copytree('test', test_dir)
    run_target(test_dir, test_id, input_dir, args.redis_host_port,
               session,path_to_enviroment, dummy_run=args.dummy_run)


else:
    if args.reset_test_counter:
        redis_server.set('bench_counter', 0)
    bench_id = 'benchmark_%s' % str(
        redis_server.incr('bench_counter')).zfill(4)
    if redis_server.get('latest_benchmark'):
        redis_server.lpush('old_benchmarks',
                           redis_server.get('latest_benchmark'))
    redis_server.set('latest_benchmark', bench_id)
    bench_dir = 'results/%s' % bench_id
    logger.info('Creating results directory at %s' % bench_dir)
    os.mkdir(bench_dir)

    logger.info('clonning the targets.')
    repo = Repo('targets')
    repo.clone('%s/results/%s' % (base_dir, bench_id))

    if os.path.exists('results/latest'):
        os.unlink('results/latest')
    os.symlink(bench_id, 'results/latest')

    target_dirs = glob('%s/results/%s/*' % (base_dir, bench_id))
    n_targets = len(target_dirs)
    logger.info('%d targets found' % n_targets)
    c = 1
    targets = {}
    for target_dir in target_dirs:
        logger.info('------------- Target %d of %d -------------' %
                    (c, n_targets))
        logger.debug('target dir: %s' % target_dir)

        run_target(target_dir, bench_id, input_dir, args.redis_host_port,
                   session, path_to_enviroment, dummy_run=args.dummy_run)

        logger.info('------------- Target Ready -------------')
        c += 1

    # run benchmark
    logger.info('firing up the jobs')
