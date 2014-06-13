#!/usr/bin/env python
import yaml
import logging
import os

logger = logging.getLogger('benchmark.utils')


def opt_to_str(x):
    if type(x) == dict:
        return reduce(lambda x, y: x + ' ' + y, [str(k) + ' ' + str(v) for k, v in x.iteritems()])
    else:
        return str(x)


def get_cmd_from_yaml(file, input_dir):
    yaml_data = open(file)
    config = yaml.load(yaml_data)
    cmd = 'mstate_contact_opt.py ' + \
        reduce(lambda x, y: x + ' ' + opt_to_str(y),
               config['options'], '') + ' ' + input_dir + '/'+ config['target'] + ' ' + input_dir + '/'+ config['decoys']
    return cmd


def run_target(target_dir, benchid, input_dir, redis_host_port, session, dummy_run=False):
    target = os.path.basename(target_dir)
    logger.info('Running target %s' % target)
    session.sendline('cd %s' % target_dir)
    session.sync_original_prompt()
    cmd = get_cmd_from_yaml('%s/target.yaml' % target_dir, input_dir) + ' -redis_host_port %s %d -job_name %s' % (redis_host_port[0], redis_host_port[1], '%s_%s' % (benchid, target))
    logger.debug('cmd: %s' % cmd)
    if dummy_run:
      logger.info('dummy run! skipping execution.')
      #session.sendline('bash -c "pwd > ~/log.txt"')
      logger.debug('remote pwd:' + session.before)
    else:
      session.sendline('echo "test" &>> ~/stdout.log')
      logger.debug('response:' + session.before)
    logger.info('done!.')