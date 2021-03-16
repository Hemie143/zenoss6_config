#!/bin/sh

NOW=$(date +"%F")
LOGFILE=/opt/zenoss6_admin/export_settings.log
echo "$(date "+%m%d%Y %T") : Starting export" >> $LOGFILE

echo "$(date "+%m%d%Y %T") : Starting devices export" >> $LOGFILE
python devices_export.py -s z6_test -f yaml/devices_TST_$NOW.yaml
echo "$(date "+%m%d%Y %T") : Devices exported" >> $LOGFILE

echo "$(date "+%m%d%Y %T") : Starting event classes export" >> $LOGFILE
python eventclasses_export.py -s z6_test -f yaml/eventclasses_TST_$NOW.yaml
echo "$(date "+%m%d%Y %T") : Event Classes exported" >> $LOGFILE

echo "$(date "+%m%d%Y %T") : Starting manufacturers export" >> $LOGFILE
python manufacturers_export.py -s z6_test -f yaml/manufacturers_TST_$NOW.yaml
echo "$(date "+%m%d%Y %T") : Manufacturers exported" >> $LOGFILE

echo "$(date "+%m%d%Y %T") : Starting mibs export" >> $LOGFILE
python mibs_export.py -s z6_test -f yaml/mibs_TST_$NOW.yaml
echo "$(date "+%m%d%Y %T") : Mibs exported" >> $LOGFILE

echo "$(date "+%m%d%Y %T") : Starting processes export" >> $LOGFILE
python processes_export.py -s z6_test -f yaml/processes_TST_$NOW.yaml
echo "$(date "+%m%d%Y %T") : Processes exported" >> $LOGFILE

echo "$(date "+%m%d%Y %T") : Starting templates export" >> $LOGFILE
python templates_export.py -s z6_test -f yaml/templates_TST_$NOW.yaml
echo "$(date "+%m%d%Y %T") : Templates exported" >> $LOGFILE

echo "$(date "+%m%d%Y %T") : Starting triggers export" >> $LOGFILE
python triggers_export.py -s z6_test -f yaml/triggers_TST_$NOW.yaml
echo "$(date "+%m%d%Y %T") : Triggers exported" >> $LOGFILE


echo "$(date "+%m%d%Y %T") : Starting services export" >> $LOGFILE
python services_export.py -s z6_test -f yaml/services_TST_$NOW.yaml
echo "$(date "+%m%d%Y %T") : Services exported" >> $LOGFILE

echo "$(date "+%m%d%Y %T") : Export completed" >> $LOGFILE

