# coding: utf-8
import zenAPI.zenApiLib
import argparse
import yaml
import sys
from tqdm import tqdm

# TODO: handle UTF-8 characters in YAML ?
#       LNSUSvc:
#         description: 'Service de mise à niveau intelligente IBM Notes       '
#         monitoredStartModes:
#         - Auto
#         serviceKeys: LNSUSvc


def get_serviceinstances(routers, uid):
    service_router = routers['Service']
    response = service_router.callMethod('query', uid=uid, sort='name', dir='ASC')
    service_list = response['result']['services']
    service_list = filter(lambda x: x['uid'].startswith('{}/serviceclasses/'.format(uid)), service_list)
    fields = ['port', 'serviceKeys', 'sendString', 'expectRegex', 'monitoredStartModes']

    service_json = {}
    for service in tqdm(service_list, desc='    Services'):
        if 'service_class' not in service_json:
            service_json['service_class'] = {}
        service_name = service['name']
        service_json['service_class'][service_name] = {}
        p_desc = service.get('description', '')
        if p_desc:
            service_json['service_class'][service_name]['description'] = p_desc
        response = service_router.callMethod('getInfo', uid=service['uid'])
        service_info = response['result']['data']
        service_props = get_servicezprop(service_info)
        service_json['service_class'][service_name].update(service_props)
        for k in fields:
            v = service_info.get(k, '')
            if v:
                service_json['service_class'][service_name][k] = v
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


def import_organizer(routers, organizer, data):
    properties_router = routers['Properties']
    # TODO: add organizer, if missing
    org_data = data['service_organizers'][organizer]
    if not 'zProperties' in org_data:
        return
    organizer_uid = '/zport/dmd{}'.format(organizer)
    response = properties_router.callMethod('getZenProperties', uid=organizer_uid)
    current_properties = response['result']['data']
    for zprop, new_value in org_data['zProperties'].items():
        current_prop = [p for p in current_properties if p['id'] == zprop][0]
        if current_prop['value'] != new_value:
            response = properties_router.callMethod('setZenProperty', uid=organizer_uid,
                                                    zProperty=zprop, value=new_value)
            if not response['result']['success']:
                print(response)
                exit()
    return

def import_service(routers, organizer, service, data):
    service_router = routers['Service']
    service_data = data['service_organizers'][organizer]['service_class'][service]
    # print(service_data)
    organizer_uid = '/zport/dmd{}'.format(organizer)
    service_uid = '{}/serviceclasses/{}'.format(organizer_uid, service)
    print(service_uid)
    response = service_router.callMethod('query', uid=service_uid)
    print(response)
    if not response['result']['success'] or response['result']['services'] == []:
        print('Create service')
        '''
        action: "ServiceRouter"
        method: "addClass"
        data: [{contextUid: "/zport/dmd/Services/IpService", id: "test", posQuery: {}}]
        0: {contextUid: "/zport/dmd/Services/IpService", id: "test", posQuery: {}}
        contextUid: "/zport/dmd/Services/IpService"
        id: "test"
        posQuery: {}
        '''
        response = service_router.callMethod('addClass', contextUid=organizer_uid, id=service)
        if not response['result']['success']:
            print(response)
            exit()
    else:
        print('Service is present')
        pass
    response = service_router.callMethod('getInfo', uid=service_uid)
    if not response['result']['success']:
        print(response)
        exit()
    # print(response)
    current_data = response['result']['data']
    # print(current_data)

    for k, new_value in service_data.items():
        # print(k)
        if k in current_data and current_data[k] != new_value:
            # print('Change value')
            # print(current_data[k])
            # print(new_value)
            info_data = {'uid': service_uid, k: new_value}
            response = service_router.callMethod('setInfo', **info_data)
            if not response['result']['success']:
                print(response)
                exit()

    if not 'zProperties' in service_data:
        return
    # organizer_uid = '/zport/dmd{}'.format(organizer)
    response = properties_router.callMethod('getZenProperties', uid=service_uid)
    if not response['result']['success']:
        print(response)
        exit()

    current_properties = response['result']['data']
    for zprop, new_value in service_data['zProperties'].items():
        current_prop = [p for p in current_properties if p['id'] == zprop][0]
        if current_prop['value'] != new_value:
            response = properties_router.callMethod('setZenProperty', uid=service_uid,
                                                    zProperty=zprop, value=new_value)
            if not response['result']['success']:
                print(response)
                exit()

    '''
    service_info = response['result']['data']
    service_props = get_servicezprop(service_info)
    service_json['service_class'][service_name].update(service_props)
    for k in fields:
        v = service_info.get(k, '')
        if v:
            service_json['service_class'][service_name][k] = v
    '''


    return
    response = service_router.callMethod('query', uid=uid, sort='name', dir='ASC')
    service_list = response['result']['services']
    service_list = filter(lambda x: x['uid'].startswith('{}/serviceclasses/'.format(uid)), service_list)
    fields = ['port', 'serviceKeys', 'sendString', 'expectRegex', 'monitoredStartModes']

    service_json = {}
    for service in tqdm(service_list, desc='    Services'):
        if 'service_class' not in service_json:
            service_json['service_class'] = {}
        service_name = service['name']
        service_json['service_class'][service_name] = {}
        p_desc = service.get('description', '')
        if p_desc:
            service_json['service_class'][service_name]['description'] = p_desc
        response = service_router.callMethod('getInfo', uid=service['uid'])
        service_info = response['result']['data']
        service_props = get_servicezprop(service_info)
        service_json['service_class'][service_name].update(service_props)
        for k in fields:
            v = service_info.get(k, '')
            if v:
                service_json['service_class'][service_name][k] = v
    return service_json

def parse_servicetree(routers, finput):
    service_router = routers['Service']

    default_organizers = ['/zport/dmd/Services', '/zport/dmd/Services/IpService/Privileged',
                          '/zport/dmd/Services/IpService/Registered', '/zport/dmd/Services/WinService']
    root_organizer = '/zport/dmd/Services'

    print('Retrieving all current organizers')
    org_list = list_organizers(routers)
    for org in default_organizers:
        if org not in org_list:
            org_list.append(org)
        org_list.sort()
    print('Found {} current organizers'.format(len(org_list)))

    response = service_router.callMethod('getOrganizerTree', id=root_organizer)
    count = [o for o in response['result'] if o['uid'] == root_organizer][0]['text']['count']
    print('Found {} current services'.format(count))

    print('Loading input file')
    data = yaml.safe_load(file(finput, 'r'))         # dict
    print('Loaded input file')
    if 'service_organizers' not in data:
        print('No service organizer found. Skipping.')
        return
    service_organizers = sorted(data['service_organizers'])
    services_count = 0
    for service_organizer in service_organizers:
        org_data = data['service_organizers'][service_organizer]
        if 'service_class' in org_data:
            services_count += len(org_data['service_class'])
    print('Found {} service organizer in input'.format(len(service_organizers)))
    print('Found {} services in input'.format(services_count))

    organizers_loop = tqdm(service_organizers, desc='Organizers', ascii=True, file=sys.stdout)
    for organizer in organizers_loop:
        desc = 'Organizer ({})'.format(organizer)
        organizers_loop.set_description(desc)
        organizers_loop.refresh()
        import_organizer(routers, organizer, data)
        if not 'service_class' in data['service_organizers'][organizer]:
            continue
        services = sorted(data['service_organizers'][organizer]['service_class'])
        services_loop = tqdm(services, desc='Services', ascii=True, file=sys.stdout)
        for service in services_loop:
            services_loop.set_description('Service ({})'.format(service))
            services_loop.refresh()
            import_service(routers, organizer, service, data)

        continue

        # Instances
        organizer_services = get_serviceinstances(routers, organizer_uid)
        service_json['service_organizers'][organizer_path].update(organizer_services)
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='List services definition')
    parser.add_argument('-s', dest='environ', action='store', default='z6_test')
    parser.add_argument('-f', dest='input', action='store', default='services_input.yaml')
    options = parser.parse_args()
    environ = options.environ
    finput = options.input

    service_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='ServiceRouter')
    properties_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='PropertiesRouter')

    routers = {
        'Service': service_router,
        'Properties': properties_router,
    }

    print('Connecting to Zenoss')
    parse_servicetree(routers, finput)
