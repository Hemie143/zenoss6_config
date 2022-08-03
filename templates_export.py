import zenAPI.zenApiLib
import argparse
import re
import yaml
import time
import logging
from collections import OrderedDict
from tqdm import tqdm


def get_parent_template(routers, uid):
    template_router = routers['Template']
    levels = uid.split('/')
    template_name = levels[-1]
    for i in range(len(levels)-3, 3, -1):
        root_uid = '{}/rrdTemplates/{}'.format('/'.join(levels[0:i]), template_name)
        response = template_router.callMethod('getInfo', uid=root_uid)
        if response['result']['success'] and response['result']['data']['uid'] == root_uid:
            return root_uid
    return


ds_all_fields = set()
dp_all_fields = set()
th_all_fields = set()
gr_all_fields = set()
gp_all_fields = set()
templates_devices = []

def get_datasources(routers, uid):
    template_router = routers['Template']
    response = template_router.callMethod('getDataSources', uid=uid)
    if not response['result']['success']:
        print('ERROR getDataSources: {}'.format(response))
        return {}
    ds_data = response['result']['data']

    datasource_json = {}
    if not ds_data:
        return datasource_json

    response = template_router.callMethod('getDataPoints', uid=uid)
    if not response['result']['success']:
        print('ERROR getDataPoints: {}'.format(response))
        return datasource_json
    dp_data = response['result']['data']

    '''
    [
     
     ('jmxPort', None), ('availableParsers', None), ('source', None), ('jmxProtocol', None), 
     ('raw20', None), ('attributeName', None), ('password', None), ('plugin_classname', None), 
     ('resource', None), ('name', None), ('jmxRawService', None), ('minimumInterval', None)
     ('meta_type', None), ('timeout', None), ('debug', None), ('ilo_result_key', None), 
     ('ports', None), ('operationParamValues', None), ('operationParamTypes', None), 
     ('webTxTimeout', None), ('statusname', None), ('group_key', None), ('operation', None), 
     ('port', None), ('description', None), ('ldapServer', None), ('authenticate', None), 
     ('ldapBaseDN', None), ('ldapBindVersion', None), ('rollup', None), ('critical', None), 
     ('result_component_value', None), ('useBasisInterval', None), ('host', None), 
     ('rmiContext', None), ('inspector_type', None), ('expression', None), ('entity_id', None), 
     ('useSSL', None), ('class_name', None), ('classname', None), ('testable', None), 
     ('cycleTime', None), ('script', None), ('strategy', None), ('result_component_key', None),
     ('username', None), ('objectName', None), ('queryset', None), ('ilo_query', None), 
     ('availableStrategies', None), ('recording', None), ('counter_key', None), 
     ('ilo_component_name_xpath', None), ('ilo_status_values', None), ('asRate', None), 
     ('uid', None), ('xpath_query', None), ('timeout_delay', None), 
     ('ilo_status_monitor', None), ('warning', None), ('maximumInterval', None), ('id', None), 
     ('property_name', None), ('initialPassword', None), ('result_value_key', None), 
     ('hostname', None), ('namespace', None), ('usePowershell', None), ('attributePath', None), 
     ('instance', None), ('expectedIpAddress', None), ('ldapBindDN', None), 
     ('ldapBindPassword', None), ('user', None), ('initialUser', None), ('chunk_size', None), 
     ('initialURL', None), ('dnsServer', None), ('database', None), ('counter', None), 
     ('dbtype', None), ('command', None)
     ]
    '''

    # TODO : commandTemplate not collected ?
    # TODO: Some fields are not exported, especially for custom types
    ds_fields = OrderedDict([('type', None), ('enabled', True), ('plugin_classname', None), ('component', ''),
                             ('eventClass', ''), ('eventKey', ''), ('severity', 3), ('cycletime', 300), ('oid', None),
                             ('commandTemplate', None), ('usessh', False), ('parser', 'Auto'),
                             ('extraContexts', None), ('initialRealm', None), ('userAgent', None),
                             ('user', None), ('password', None),
                             ('raw20_aggregation', None), ('raw20', None),
                             ('jmxPort', None),  ('jmxProtocol', 'RMI'), ('rmiContext', 'jmxrmi'),
                             ('ldapServer', None), ('ldapBaseDN', None), ('ldapBindVersion', None),
                             ('ldapBindDN', None), ('ldapBindPassword', None),
                             ('ilo_result_key', None), ('ilo_component_name_xpath', None), ('ilo_query', None),
                             ('ilo_status_values', None), ('ilo_status_monitor', True),
                             ('attributeName', None), ('resource', None), ('timeout', None), ('ports', None),
                             ('webTxTimeout', None), ('statusname', None), ('group_key', None), ('operation', None),
                             ('port', None),  ('authenticate', None), ('rollup', None), ('critical', None),
                             ('result_component_value', None), ('useBasisInterval', True), ('host', None),
                             ('expression', None), ('entity_id', None), ('useSSL', True), ('class_name', None),
                             ('classname', None), ('strategy', None), ('result_component_key', None),
                             ('username', None), ('objectName', None), ('queryset', None), ('counter_key', None),
                             ('xpath_query', None), ('timeout_delay', 60), ('warning', None), ('property_name', None),
                             ('initialPassword', None), ('result_value_key', None), ('hostname', None),
                             ('namespace', None), ('usePowershell', None), ('instance', None),
                             ('expectedIpAddress', None), ('initialUser', None), ('chunk_size', None),
                             ('initialURL', None), ('counter', None), ('dbtype', None), ('command', None),
                             ('attempts', 2), ('dnsServer', None), ('labels', None), ('service', None),
                             ('crossSeriesReducer', None), ('aggregator', None), ('filter_', None),
                             ('metric_type', None), ('groupByFields', None), ('perSeriesAligner', None),
                             ('script', None)
                             ])

    ds_exclude = ['id', 'uid', 'newId', 'name', 'availableParsers', 'source', 'inspector_type', 'meta_type',
                  'availableStrategies']

    '''
    [
    ('xpath', None), ('isrow', None), ('leaf', None), ('xpath_query', None), ('handler', None), 
    ('availableRRDTypes', None), ('name', None), ('rpn', None), ('rate', None), ('meta_type', None), 
    ('newId', None), ('createCmd', None), ('inspector_type', None), ('aliases', None), 
    ('type', None), 
    ]
    '''

    dp_fields = OrderedDict([('description', ''), ('rrdtype', ''), ('rrdmin', None), ('rrdmax', None),
                             ('xpath', None), ('isrow', True), ('leaf', True), ('xpath_query', None), ('handler', None),
                             ('rpn', None), ('rate', True), ('createCmd', None),
                             ])

    datasource_json['datasources'] = {}
    ds_data = sorted(ds_data, key=lambda i: i['name'])
    dp_data = sorted(dp_data, key=lambda i: i['name'])
    for ds in ds_data:
        ds_uid = ds['uid']
        response = template_router.callMethod('getDataSourceDetails', uid=ds_uid)
        if 'record' not in response['result']:
            print('getDataSourceDetails: {}'.format(response))
            continue
        ds_details = response['result']['record']

        # ds_keys = ds_details.keys()
        # ds_keys.remove('name')
        ds_name = ds['name']
        datasource_json['datasources'][ds_name] = {}

        for k, v in ds_details.items():
            # v = ds_details.get(k, None)
            if k in ds_exclude:
                continue
            def_value = ds_fields.get(k, None)
            if v is not None and v != def_value:
                datasource_json['datasources'][ds_name][k] = v
        if 'usessh' in ds_details:
            datasource_json['datasources'][ds_name]['usessh'] = ds_details['usessh']

        '''
        if 'Dns' in ds_details['type']:
            print(ds_details)
        '''

        # Source field
        v = ds_details.get('source', None)
        # if v and v != ds.get('plugin_classname', None):
        if (v and not v.startswith('ZenPacks.')):
            ds_type = ds_details['type']
            # TODO: Refactor with mapping
            if ds_type in ['SNMP', 'Cisco SNMP', 'NetAppMonitor SNMP']:
                datasource_json['datasources'][ds_name]['oid'] = v
            elif ds_type == 'SQL':
                datasource_json['datasources'][ds_name]['sql'] = v
            elif ds_type == 'COMMAND':
                if "over SSH" in v:
                    v = v[:-9]
                datasource_json['datasources'][ds_name]['commandTemplate'] = v
            elif ds_type == 'WebTx':
                datasource_json['datasources'][ds_name]['initialURL'] = v
            elif ds_type == 'NX-API Command':
                datasource_json['datasources'][ds_name]['command'] = v
            elif ds_type in ['ApacheMonitor', 'MySqlMonitor']:
                datasource_json['datasources'][ds_name]['hostname'] = v
            elif ds_type == 'Calculated Performance':
                datasource_json['datasources'][ds_name]['expression'] = v
            elif ds_type == 'NetAppMonitor ZAPI':
                datasource_json['datasources'][ds_name]['zapicall'] = v
            elif ds_type == 'NetAppMonitor Cmode Events ZAPI':
                datasource_json['datasources'][ds_name]['source'] = v
            elif ds_type == 'JMX':
                if v != '${dev/id}':
                    print(ds_type)
                    print('source: {}'.format(v))
                    print(ds)
                    exit()
                # No data for output
            elif ds_type in ['Google Cloud Platform Quota', 'Power']:
                datasource_json['datasources'][ds_name]['source'] = v
            elif ds_type in ['Kubernetes Metrics', 'Cisco APIC Properties', 'Cisco APIC Stats', 'LDAPMonitor',
                             'Windows Process', 'VMware vSphere', 'Property', 'PING', 'Kubernetes Calculated Metrics',
                             'Google Cloud Platform Status', 'Google Cloud Platform Stackdriver Monitoring',
                             'AzureDataSource', 'Azure Metric', 'Azure Activity Log', 'AzureEABillingDataSource',
                             'Datapoint Aggregator', 'Cisco UCS XML API', 'UCS CIMC']:
                pass
                # No data for output
            else:
                print()
                print('Datasource - unknown type')
                print(ds_type)
                print('source: {}'.format(v))
                print(ds)
                print(ds_details)
                exit()
        # ds_all_fields.update(ds_keys)

        # Datapoints
        ds_uid = ds['uid']
        ds_dp_data = [d for d in dp_data if d['uid'].startswith('{}/datapoints/'.format(ds_uid))]
        if ds_dp_data:
            datasource_json['datasources'][ds_name]['datapoints'] = {}
        for dp in ds_dp_data:
            dp_keys = dp.keys()
            dp_keys.remove('name')
            dp_name = dp['name'][len(ds['name'])+1:]
            datasource_json['datasources'][ds_name]['datapoints'][dp_name] = {}
            for k, default in dp_fields.items():
                v = dp.get(k, None)
                if k in dp_keys:
                    dp_keys.remove(k)
                if v and v != default:
                    datasource_json['datasources'][ds_name]['datapoints'][dp_name][k] = v

            dp_keys.remove('aliases')
            EXPORT_ALIAS = False
            if EXPORT_ALIAS:
                dp_aliases = dp.get('aliases', [])

                # aliases: [{id: "test", formula: "1, *"}, {id: "test2", formula: "2, *"}]

                aliases_yaml = []
                for alias in dp_aliases:
                    alias_formula = alias.get('formula', 'null')
                    if not alias_formula:
                        alias_formula = 'null'
                    # aliases_text.append("{}: '{}'".format(alias['name'], alias_formula))
                    aliases_yaml.append({'id': alias['name'], 'formula': alias['formula']})
                '''
                if aliases_text:
                    value = '{{{}}}'.format(', '.join(aliases_text)).encode('ascii')
                    datasource_json['datasources'][ds_name]['datapoints'][dp_name]['aliases'] = value
                '''
                if aliases_yaml:
                    datasource_json['datasources'][ds_name]['datapoints'][dp_name]['aliases'] = aliases_yaml
                # dp_all_fields.update(dp_keys)
    return datasource_json


def get_thresholds(routers, uid):
    # TODO: thresholds: "enabled: false" is not exported
    template_router = routers['Template']
    response = template_router.callMethod('getThresholds', uid=uid)
    if not response['result']['success']:
        print('get_thresholds error: {}'.format(response))
        return {}
    th_data = response['result']['data']

    threshold_json = {}
    if not th_data:
        return threshold_json

    # print(th_data)

    # for t in th_data:
    #     print(t['uid'])


    '''
    [
    ('uid', None), ('escalateCount', None), ('newId', None), ('timePeriod', None), 
    ('total_expression', None), ('id', None), ('eventClassKey', None), 
    ('explanation', None), ('capacity_type', None), ('description', None), 
    ('dsnames', None), ('used_expression', None), ('violationPercentage', None), 
    ('meta_type', None), ('dataPoints', None), ('inspector_type', None), 
    ('pct_threshold', None), ('resolution', None)
    ]
    '''

    th_fields = OrderedDict([('type', 'MinMaxThreshold'), ('enabled', True), ('eventClass', None),
                             ('eventClassKey', None),
                             ('severity', 3), ('optional', False), ('minval', None), ('maxval', None),
                             ('escalateCount', None), ('timePeriod', None), ('violationPercentage', None),
                             ('pct_threshold', None), ('total_expression', None), ('used_expression', None),
                             ('capacity_type', None), ('resolution', None),
                             ])

    th_data = sorted(th_data, key=lambda i: i['name'])
    threshold_json['thresholds'] = {}
    # yaml_print(key='thresholds', indent=indent)
    for threshold in th_data:
        th_keys = threshold.keys()
        th_keys.remove('name')
        threshold_name = threshold['name']
        # yaml_print(key=threshold['name'], indent=indent + 2)
        threshold_json['thresholds'][threshold_name] = {}
        for k, default in th_fields.items():
            v = threshold.get(k, '')
            if k in th_keys:
                th_keys.remove(k)
            # TODO: BUG: For enabled field, the value can be "False". In this case, it won't be exported.
            if v and v != default:
                # yaml_print(key=k, value=v, indent=indent + 4)
                threshold_json['thresholds'][threshold_name][k] = v
        if 'dsnames' in th_keys:
            th_keys.remove('dsnames')
        dsnames = threshold.get('dsnames', [])
        if dsnames:
            # v = '[{}]'.format(', '.join(dsnames))
            # yaml_print(key='dsnames', value=v, indent=indent + 4)
            # threshold_json['thresholds'][threshold_name]['dsnames'] = v
            threshold_json['thresholds'][threshold_name]['dsnames'] = dsnames
            # threshold_json['thresholds'][threshold_name]['dsnames2'] = dsnames
        # th_all_fields.update(th_keys)

    # print(threshold_json)


    return threshold_json


def get_graphs(routers, uid):
    template_router = routers['Template']
    response = template_router.callMethod('getGraphs', uid=uid)
    '''
    print(response)
    if not response['result']['success']:
        print("Could not find graphs for {}".format(uid))
        print(response)
        exit(1)
    '''
    result = response['result']

    graph_json = {}
    if not result:
        return graph_json

    '''
    All graph fields
    [
    ]
    '''

    gr_fields = OrderedDict([('type', ''), ('units', ''), ('miny', -1), ('maxy', -1), ('log', False),
                             ('base', False), ('hasSummary', True), ('height', 500), ('width', 500),
                             ('comments', []), ('sequence', None), ('ceiling', None), ('description', None),
                             ])

    '''
    All graphpoint fields
    [
    ('type', None), ('skipCalc', None), 
    ('meta_type', None), ('rrdVariables', None), ('inspector_type', None), 
    ]
    '''

    gp_fields = OrderedDict([('description', 'DataPointGraphPoint'), ('type', 'DataPoint'), ('legend', ''),
                             ('dpName', ''), ('lineType', 'LINE'), ('lineWidth', 1), ('stacked', False), ('color', ''),
                             ('colorindex', None), ('format', '%5.2lf%s'), ('cFunc', 'AVERAGE'),
                             ('limit', -1), ('rpn', ''), ('includeThresholds', False), ('thresholdLegends', {}),
                             ('threshId', None), ('text', '')])

    # yaml_print(key='graphs', indent=indent)
    graph_json['graphs'] = {}
    try:
        gr_data = sorted(result, key=lambda i: i['name'])           # TODO: May crash in some cases, to debug
    except Exception as e:
        print('ERROR gr_data: {}'.format(e.args))
        gr_data = []
    # dp_data = sorted(dp_data, key=lambda i: i['name'])
    for graph in gr_data:
        graph_name = graph['name']
        graph_json['graphs'][graph_name] = {}
        # yaml_print(key=graph['name'], indent=indent + 2)
        for k, default in gr_fields.items():
            v = graph.get(k, None)
            if v and v != default:
                # yaml_print(key=k, value=v, indent=indent + 4)
                graph_json['graphs'][graph_name][k] = v
        # gr_all_fields.update(graph.keys())

        # Graphpoints
        graph_uid = graph['uid']
        response = template_router.callMethod('getGraphPoints', uid=graph_uid)
        gp_data = sorted(response['result']['data'], key=lambda i: i['name'])

        # if gp_data:
        #     yaml_print(key='graphpoints', indent=indent + 4)
        for graphpoint in gp_data:
            if 'graphpoints' not in graph_json['graphs'][graph_name]:
                graph_json['graphs'][graph_name]['graphpoints'] = {}
            gp_name = graphpoint['name']
            # yaml_print(key=graphpoint['name'], indent=indent + 6)
            graph_json['graphs'][graph_name]['graphpoints'][gp_name] = {}
            for k, default in gp_fields.items():
                v = graphpoint.get(k, None)
                if v and v != default:
                    # yaml_print(key=k, value=v, indent=indent + 8)
                    graph_json['graphs'][graph_name]['graphpoints'][gp_name][k] = v
            # gp_all_fields.update(graphpoint.keys())
    return graph_json


def get_template(routers, uid):
    template_router = routers['Template']
    response = template_router.callMethod('getInfo', uid=uid)
    data = response['result']['data']
    fields = ['description', 'targetPythonClass']

    template_json = {}
    template_name = data['name']
    template_json[template_name] = {}
    for k in fields:
        v = data[k]
        if v:
            template_json[template_name][k] = v

    datasources= get_datasources(routers, uid)
    template_json[template_name].update(datasources)
    thresholds = get_thresholds(routers, uid)
    template_json[template_name].update(thresholds)
    graphs = get_graphs(routers, uid)
    template_json[template_name].update(graphs)
    return template_json

def fetch_all_templates(template_router, dc_filter=None, t_filter=None):
    # Generate full set of template uids, down to local component templates
    print('Retrieving templates')
    templates_name_set = set()
    templates_uid_set = set()

    response = template_router.callMethod('getTemplates', id='/zport/dmd/Devices')
    result = response['result']
    print('Found {} root entries for templates'.format(len(result)))
    filterpath = '/zport/dmd/Devices{}'.format(dc_filter)
    # for t in tqdm(result, ascii=True):
    for t in tqdm(result):
        # print(t['uid'])
        if t['name'] in templates_name_set:
            continue
        if t_filter and not re.match(t_filter, t['name']):
            continue
        templates_name_set.add(t['name'])
        t_response = template_router.callMethod('getTemplates', id=t['uid'])
        t_result = t_response['result']
        # print(t_result)
        templates_uid_set.update({r['uid'] for r in t_result if r['uid'].startswith(filterpath)})
    templates_uid = sorted(list(templates_uid_set))
    print('Retrieved {} templates'.format(len(templates_uid)))
    return templates_uid

def group_templates_by_dc(dc_templates, templates_uid):
    """
    Group templates by device class
    Returns a dict with:
        - keys : device class
        - values: set of local template uids
    """
    device_classes = {}
    while dc_templates:
        uid = dc_templates.pop()
        r = re.match('((\/zport\/dmd\/Devices)(.*))(\/rrdTemplates\/)(.*)', uid)
        if not r:
            print('No regex match for {}'.format(uid))
            exit()
        # Retrieve all templates for same device class
        dc_path = '{}{}'.format(r.group(1), r.group(4))
        dc_name = r.group(3)
        if not dc_name:
            dc_name = "/"
        dc_r = re.compile(dc_path)
        templates = set(filter(dc_r.match, templates_uid))
        device_classes[dc_name] = templates
        dc_templates = dc_templates - templates
    print('Found {} Device classes with templates'.format(len(device_classes)))
    return device_classes

def export_dc_templates(device_classes, output):
    dc_loop = tqdm(sorted(device_classes.items()), desc='Device Classes ')
    templates_json = {}
    for device_class, uids in dc_loop:
        dc_loop.set_description('Device Class ({})'.format(device_class))
        dc_loop.refresh()
        if 'device_classes' not in templates_json:
            templates_json['device_classes'] = {}
        templates_json['device_classes'][device_class] = {}
        uids = sorted(uids)
        t_loop = tqdm(uids, desc='    Templates')
        for uid in t_loop:
            t_loop.set_description('    Template ({})'.format(uid))
            t_loop.refresh()
            if 'templates' not in templates_json['device_classes'][device_class]:
                templates_json['device_classes'][device_class]['templates'] = {}
            data = get_template(routers, uid)
            templates_json['device_classes'][device_class]['templates'].update(data)
            try:
                yaml.safe_dump(templates_json, file(output, 'w'), encoding='utf-8', allow_unicode=True, sort_keys=True)
            except:
                time.sleep(10)

def export_local_templates(local_templates):
    # Local templates
    templates_json = {'device_classes': {}}
    dt_loop = tqdm(local_templates, desc='Local templates')
    for uid in dt_loop:
        dt_loop.set_description('Local template ({})'.format(uid))
        dt_loop.refresh()

        if uid.startswith('/zport/dmd/Devices/ControlCenter/'):
            continue
        dc_name = uid[18:]
        dc_name = '/'.join(dc_name.split('/')[:-1])

        templates_json['device_classes'][dc_name] = {}
        if 'templates' not in templates_json['device_classes'][dc_name]:
            # TODO: use defaultdict ?
            templates_json['device_classes'][dc_name]['templates'] = {}
        data = get_template(routers, uid)
        templates_json['device_classes'][dc_name]['templates'].update(data)

    with open(output, 'a') as f:
        f.write('# Local templates\r\n')
    yaml.safe_dump(templates_json, file(output, 'a'), encoding='utf-8', allow_unicode=True, sort_keys=True)

def parse_templates(routers, output, dc_filter, template_filter):
    template_router = routers['Template']
    templates_uid = fetch_all_templates(template_router, dc_filter, template_filter)

    # Sort dc templates from devices/components templates
    dc_templates = set([u for u in templates_uid if '/rrdTemplates/' in u])
    local_templates = [u for u in templates_uid if '/devices/' in u]
    print('Device Class templates: {}'.format(len(dc_templates)))
    print('Local templates: {}'.format(len(local_templates)))

    if len(templates_uid) != len(dc_templates) + len(local_templates):
        print('Some templates will not be exported')
    else:
        print('Total number of templates is OK')

    device_classes = group_templates_by_dc(dc_templates, templates_uid)
    export_dc_templates(device_classes, output)
    export_local_templates(local_templates)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='List templates definition')
    # TODO: Order of graphs and graphpoints: setGraphDefinitionSequence & setGraphPointSequence
    parser.add_argument('-s', dest='environ', action='store', default='z6_test')
    parser.add_argument('-f', dest='output', action='store', default='templates_output.yaml')
    parser.add_argument('-d', dest='dc', action='store', default='')
    parser.add_argument('-n', dest='template_name', action='store', default='')
    options = parser.parse_args()
    environ = options.environ
    output = options.output
    device_class = options.dc
    template_name = options.template_name

    log = logging.getLogger('templates_export')
    log.setLevel(logging.DEBUG)
    # File handler
    fh = logging.FileHandler('templates_export.log')
    fh.setLevel(logging.DEBUG)
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)
    # Formatter
    fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    ch.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    # Add handlers
    log.addHandler(fh)
    log.addHandler(ch)

    log.info('#'*80)
    log.info('Starting template export')
    log.info('Environment: {}'.format(environ))
    log.info('Output file: {}'.format(output))
    log.info('Device Class: {}'.format(device_class))
    log.info('Template name: {}'.format(template_name))

    try:
        template_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='TemplateRouter')
        properties_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='PropertiesRouter')
    except Exception as e:
        log.error('Could not connect to Zenoss: {}'.format(e.args))
        exit(1)

    routers = {
        'Template': template_router,
        'Properties': properties_router,
    }

    # yaml_print(key='device_classes', indent=0)
    print('Connecting to Zenoss')
    parse_templates(routers, output, device_class, template_name)
    logging.info('Exiting template export')

# TODO: separate outputs: stdout for progress, log for errors and file output
# TODO: protect all calls
# TODO: migrate to Python3
# TODO: Re-order output (no group of local templates at the end)
# TODO: Stream JSON output on-the-fly ?
# TODO: Resume an export (based on previous run?)