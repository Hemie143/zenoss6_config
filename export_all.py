#!/bin/python

import logging
import logging.handlers
import sys

import devices_export


LOGFILE = "/opt/zenoss6_admin/export_all.log"
LOGFILE = "export_all.log"
DIR = "/opt/zenoss6_admin"
FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
TODAY = "20220214"
ENVIRON = 'z6_test'

# Logger
rootLogger = logging.getLogger()

# Add settings for rotation
fileHandler = logging.FileHandler(LOGFILE)
logFormatter = logging.Formatter(FORMAT)
fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler(sys.stdout)
rootLogger.addHandler(consoleHandler)

rootLogger.setLevel(logging.INFO)

logging.info('Starting export')
logging.info('Starting devices export')
devices_export.export(ENVIRON, 'yaml/devices_TST_20220214.yaml')
logging.info('Finished devices export')
