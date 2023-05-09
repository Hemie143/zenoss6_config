import zenAPI.zenApiLib
import argparse
import logging
import yaml
from tqdm import tqdm


def get_properties(routers, uid):
    properties_router = routers['Properties']
    response = properties_router.callMethod('getZenProperties', uid=uid)
    properties = response['result']['data']
    properties = sorted(properties, key=lambda i: i['id'])
    prop_data = {}
    for property in properties:
        if property['islocal'] == 1:
            if 'zProperties' not in prop_data:
                prop_data['zProperties'] = {}
            prop_data['zProperties'][property['id']] = property['value']
    return prop_data


def get_processzprop(process):
    zprop_keys = sorted([k for k in process if k.startswith('z')])
    prop_data = {}
    for k in zprop_keys:
        prop = process[k]
        if not prop['isAcquired']:
            if 'zProperties' not in prop_data:
                prop_data['zProperties'] = {}
            prop_data['zProperties'][k] = prop['localValue']
    return prop_data

def get_processinstances(routers, uid, progress_disable):
    process_router = routers['Process']
    response = process_router.callMethod('query', uid=uid)
    process_list = response['result']['processes']
    process_list = filter(lambda x: x['uid'].startswith('{}/osProcessClasses/'.format(uid)), process_list)
    process_list = sorted(process_list, key=lambda i: i['name'])
    fields = ['includeRegex', 'excludeRegex', 'replaceRegex', 'replacement']

    process_json = {}
    for process in tqdm(process_list, desc='    Processes', ascii=True, disable=progress_disable):
        if 'process_class' not in process_json:
            process_json['process_class'] = {}
        process_name = process['name']
        process_json['process_class'][process_name] = {}
        p_desc = process.get('description', '')
        if p_desc:
            process_json['process_class'][process_name]['description'] = p_desc
        p_props = get_processzprop(process)
        process_json['process_class'][process_name].update(p_props)
        for k in fields:
            v = process[k]
            if v:
                process_json['process_class'][process_name][k] = v
    return process_json


def list_organizers(routers, uids=[]):
    process_router = routers['Process']
    organizers_uids = []
    if not uids:
        process_tree = process_router.callMethod('getTree', id='/zport/dmd/Processes')
        uids = process_tree['result']
    for branch in sorted(uids, key=lambda i: i['uid']):
        branch_uid = branch['uid']
        organizers_uids.append(branch_uid)
        branch_children = sorted(branch.get('children', []))
        if branch_children:
            children = list_organizers(routers, branch_children)
            organizers_uids.extend(children)
    return organizers_uids


def parse_processtree(routers, output, progress_disable):
    process_router = routers['Process']

    logging.info('Retrieving all organizers')
    org_list = list_organizers(routers)
    logging.info('Retrieved {} organizers'.format(len(org_list)))

    process_json = {'process_class_organizers': {}}
    for organizer_uid in tqdm(org_list, desc='Organizers ', ascii=True, disable=progress_disable):
        response = process_router.callMethod('getTree', id=organizer_uid)
        organizer = response['result'][0]

        organizer_path = '/' + organizer['path']
        process_json['process_class_organizers'][organizer_path] = {}
        organizer_desc = organizer['text']['description']
        process_json['process_class_organizers'][organizer_path]['description'] = organizer_desc

        # Properties
        organizer_props = get_properties(routers, organizer_uid)
        process_json['process_class_organizers'][organizer_path].update(organizer_props)
        # Instances
        organizer_processes = get_processinstances(routers, organizer_uid, progress_disable)
        process_json['process_class_organizers'][organizer_path].update(organizer_processes)
    yaml.safe_dump(process_json, file(output, 'w'), encoding='utf-8', allow_unicode=True, sort_keys=True)

def export(environ, output, progress_disable=False):
    try:
        process_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='ProcessRouter')
        properties_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='PropertiesRouter')
    except Exception as e:
        logging.error('Could not connect to Zenoss: {}'.format(e.args))
        exit(1)

    routers = {
        'Process': process_router,
        'Properties': properties_router,
    }

    parse_processtree(routers, output, progress_disable)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='List processes definition')
    parser.add_argument('-s', dest='environ', action='store', default='z6_test')
    parser.add_argument('-f', dest='output', action='store', default='processes_output.yaml')
    options = parser.parse_args()
    environ = options.environ
    output = options.output

    export(environ, output)

# TODO: Check attribute zAlertOnRestart
# TODO: Check attribute zFailSeverity
# TODO: Check attribute zModelerLock
# TODO: Check attribute zSendEventWhenBlockedFlag