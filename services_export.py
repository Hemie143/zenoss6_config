import zenAPI.zenApiLib
import argparse
import yaml
import time
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


def get_servicezprop(service):
    zprop_keys = sorted([k for k in service if k.startswith('z')])
    prop_data = {}
    for k in zprop_keys:
        prop = service[k]
        if not prop['isAcquired']:
            if 'zProperties' not in prop_data:
                prop_data['zProperties'] = {}
            prop_data['zProperties'][k] = prop['localValue']
    return prop_data


def get_serviceinstances(routers, uid, full_data):
    service_router = routers['Service']
    response = service_router.callMethod('query', uid=uid, sort='name', dir='ASC')
    service_list = response['result']['services']
    service_list = filter(lambda x: x['uid'].startswith('{}/serviceclasses/'.format(uid)), service_list)
    fields = ['port', 'serviceKeys', 'sendString', 'expectRegex', 'monitoredStartModes']

    path = uid[10:]
    service_json = {}
    dump_count = 0
    for service in tqdm(service_list, desc='    Services', ascii=True):
        if 'service_class' not in service_json:
            service_json['service_class'] = {}
        service_name = service['name']
        service_json['service_class'][service_name] = {}
        p_desc = service.get('description', '')
        if p_desc:
            service_json['service_class'][service_name]['description'] = p_desc
        response = service_router.callMethod('getInfo', uid=service['uid'])
        if not response['result']['success']:
            print('Could not fetch service Info: {}'.format(response))
            continue
        service_info = response['result']['data']
        service_props = get_servicezprop(service_info)
        service_json['service_class'][service_name].update(service_props)
        for k in fields:
            v = service_info.get(k, '')
            if v:
                service_json['service_class'][service_name][k] = v
        full_data['service_organizers'][path].update(service_json)
        dump_count += 1
        if dump_count % 20 == 0:
            yaml.safe_dump(full_data, file(output, 'w'), encoding='utf-8', allow_unicode=True, sort_keys=True)
        try:
            yaml.safe_dump(full_data, file(output, 'w'), encoding='utf-8', allow_unicode=True, sort_keys=True)
        except:
            pass

    time.sleep(5)
    yaml.safe_dump(full_data, file(output, 'w'), encoding='utf-8', allow_unicode=True, sort_keys=True)
    return service_json


def list_organizers(routers, uids=[]):
    service_router = routers['Service']
    organizers_uids = []
    if not uids:
        service_tree = service_router.callMethod('getOrganizerTree', id='/zport/dmd/Services')
        uids = service_tree['result']

    for branch in sorted(uids, key=lambda i: i['uid']):
        branch_uid = branch['uid']
        organizers_uids.append(branch_uid)
        branch_children = sorted(branch.get('children', []))
        if branch_children:
            children = list_organizers(routers, branch_children)
            organizers_uids.extend(children)
    return organizers_uids


def parse_servicetree(routers, output, full_data):
    service_router = routers['Service']

    default_organizers = ['/zport/dmd/Services', '/zport/dmd/Services/IpService/Privileged',
                          '/zport/dmd/Services/IpService/Registered', '/zport/dmd/Services/WinService']

    print('Retrieving all organizers')
    org_list = list_organizers(routers)

    for org in default_organizers:
        if org not in org_list:
            org_list.append(org)
        org_list.sort()
    print('Retrieved {} organizers'.format(len(org_list)))

    full_data = {'service_organizers': {}}
    for organizer_uid in tqdm(org_list, desc='Organizers', ascii=True):
        if organizer_uid != '/zport/dmd/Services/WinService':
            continue

        response = service_router.callMethod('getOrganizerTree', id=organizer_uid)
        organizer = response['result'][0]

        organizer_path = '/' + organizer['path']
        full_data['service_organizers'][organizer_path] = {}
        # Properties
        organizer_props = get_properties(routers, organizer_uid)
        full_data['service_organizers'][organizer_path].update(organizer_props)
        # Instances
        organizer_services = get_serviceinstances(routers, organizer_uid, full_data)
        # full_data['service_organizers'][organizer_path].update(organizer_services)
        yaml.safe_dump(full_data, file(output, 'w'), encoding='utf-8', allow_unicode=True, sort_keys=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='List services definition')
    parser.add_argument('-s', dest='environ', action='store', default='z6_test')
    parser.add_argument('-f', dest='output', action='store', default='services_output.yaml')
    options = parser.parse_args()
    environ = options.environ
    output = options.output

    try:
        service_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='ServiceRouter')
        properties_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='PropertiesRouter')
    except Exception as e:
        print('Could not connect to Zenoss: {}'.format(e.args))
        exit(1)

    routers = {
        'Service': service_router,
        'Properties': properties_router,
    }

    print('Connecting to Zenoss')
    full_data = {}
    parse_servicetree(routers, output, full_data)


# TODO: Exports way too much, takes too much time