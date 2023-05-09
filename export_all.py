#!/bin/python

import argparse
import glob
import logging
import os
import sys
import tarfile
import time

from datetime import date
from logging import Formatter
from logging.handlers import RotatingFileHandler

import devices_export
import eventclasses_export
import manufacturers_export
import mibs_export
import processes_export
# import reports_export
# import services_export
import templates_export
import triggers_export
# import users_list

# TODO: Enhance how directories and files are referred
LOGFILE = "export_all.log"
LOG_SIZE = 1024 * 1024
LOG_COUNT = 10
FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
RETENTION = 30           # How long should the config files (tar files) be kept, in days ?

ENV_SETS = {
    'TEST': 'z6_test',
    'PROD': 'z6_prod',
    'CLOUD': 'zcloud',
}

def init_loggers(log_path, cron):
    # Logger
    rootLogger = logging.getLogger()
    rootLogger.setLevel((logging.INFO))

    consoleHandler = logging.StreamHandler(sys.stdout)
    if cron:
        consoleHandler.setLevel(logging.WARNING)
    else:
        consoleHandler.setLevel(logging.INFO)

    fileHandler = RotatingFileHandler(log_path, maxBytes=LOG_SIZE, backupCount=LOG_COUNT)
    fileHandler.setLevel(logging.INFO)
    fileHandler.setFormatter(Formatter(FORMAT))

    rootLogger.addHandler(fileHandler)
    rootLogger.addHandler(consoleHandler)

def export_settings(environ, env_set, date_format, config_folder):
    # Export

    # TODO: Put the following in a loop
    # TODO: Enhance the formatting

    logging.info('Starting devices export')
    devices_export.export(env_set, '{}/devices_{}_{}.yaml'.format(config_folder, environ, date_format), cron)
    logging.info('Finished devices export')

    logging.info('Starting event classes export')
    eventclasses_export.export(env_set, '{}/eventclasses_{}_{}.yaml'.format(config_folder, environ, date_format), cron)
    logging.info('Finished event classes export')

    logging.info('Starting manufacturers export')
    manufacturers_export.export(env_set, '{}/manufacturers_{}_{}.yaml'.format(config_folder, environ, date_format), cron)
    logging.info('Finished manufacturers export')

    logging.info('Starting mibs export')
    mibs_export.export(env_set, '{}/mibs_{}_{}.yaml'.format(config_folder, environ, date_format), cron)
    logging.info('Finished mibs export')

    logging.info('Starting processes export')
    # processes_export.export(env_set, '{}/processes_{}_{}.yaml'.format(config_folder, environ, date_format), cron)
    logging.info('Finished processes export')

    # logging.info('Starting reports export')
    # reports_export.export(env_set, '{}/reports_{}_{}.yaml'.format(config_folder, environ, date_format))
    # logging.info('Finished reports export')

    logging.info('Starting templates export')
    templates_export.export(env_set, '{}/templates_{}_{}.yaml'.format(config_folder, environ, date_format), cron)
    logging.info('Finished templates export')

    logging.info('Starting triggers export')
    triggers_export.export(env_set, '{}/triggers_{}_{}.yaml'.format(config_folder, environ, date_format), cron)
    logging.info('Finished triggers export')

def tar_export(config_folder):
    # tar export files
    logging.info('Creating tar file')
    tar = tarfile.open('{}/config_{}_{}.tgz'.format(config_folder, environ, date_format), 'w:gz')
    export_files = glob.glob('{}/*_{}_{}.yaml'.format(config_folder, environ, date_format))
    for f in export_files:
        tar.add(f)
    tar.close()

    # Delete export files
    logging.info('Deleting export files')
    for f in export_files:
        os.remove(f)

def delete_old_tars(environ, config_folder):
    # Remove old tar files
    logging.info('Checking old tar files')
    now = time.time()
    tar_files = glob.glob('{}/config_{}_????????.tgz'.format(config_folder, environ, date_format))
    for t in tar_files:
        t_stamp = os.stat(t).st_mtime
        if t_stamp < now - RETENTION * 86400:
            logging.info('Deleting old tar file {}'.format(t))
            os.remove(t)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Export all Zenoss settings')
    parser.add_argument('-e', dest='environ', action='store', default='test')
    parser.add_argument('--cron', dest='cron', action='store_true')
    options = parser.parse_args()
    environ = options.environ.upper()
    cron = options.cron

    # Check that configs folder exists
    root_folder = os.path.dirname(os.path.realpath(__file__))
    log_path = os.path.join(root_folder, LOGFILE)
    config_folder = os.path.join(root_folder, "configs")
    if not os.path.exists(config_folder):
        os.mkdir(config_folder)


    init_loggers(log_path, cron)

    # Init
    today = date.today()
    date_format = '{}{:02d}{:02d}'.format(today.year, today.month, today.day)
    if environ not in ENV_SETS:
        logging.error('Unknown environment: {}'.format(environ))
        exit(1)
    else:
        env_set = ENV_SETS[environ]


    logging.warning('Starting export {}'.format('-' * 80))
    export_settings(environ, env_set, date_format, config_folder)
    tar_export(config_folder)
    delete_old_tars(environ, config_folder)
    logging.warning('Finished export {}'.format('-' * 80))


# TODO: get environment from argument
# TODO: Make whole tool and deps failure proof - Should reach the end even with errors
# TODO: Add way more logging in all modules
# TODO: Add services export
# TODO: Add reports export
# TODO: Add users export
# TODO: Add component groups export
# TODO: Export status of components monitored/not monitored & locking ?
