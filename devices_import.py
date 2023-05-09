# coding=utf-8
import zenAPI.zenApiLib
import argparse
import yaml
import sys
import time
from tqdm import tqdm
from cryptography.fernet import Fernet

# TODO: Import locks on components

def get_trigger(routers, trigger_name):
    trigger_router = routers['Triggers']
    response = trigger_router.callMethod('getTriggers')
    result = response['result']
    data = result['data']
    for trigger_data in data:
        if trigger_data.get('name', '') == trigger_name:
            break
    else:
        trigger_data = {}
    return trigger_data


def get_notification(routers, notification_name):
    trigger_router = routers['Triggers']
    response = trigger_router.callMethod('getNotifications')
    result = response['result']
    print(result)
    return


def add_deviceclass(routers, dc_path):
    device_router = routers['Device']
    dc_branches = dc_path.split('/')
    contextUid = '/zport/dmd/Devices{}'.format('/'.join(dc_branches[:-1]))
    response = device_router.callMethod('objectExists', uid=contextUid)
    if response['result']['exists']:
        id = dc_branches[-1]
        response = device_router.callMethod('addDeviceClassNode', type='organizer',
                                            contextUid=contextUid, id=id)
        if not response['result']['success']:
            print(response)
            exit()
    else:
        parentuid = '/zport/dmd/Devices{}'.format('/'.join(dc_branches[:-2]))
        add_deviceclass(routers, parentuid)
    return


def add_device(routers, dc_uid, device_data, collectors, devices_fulllist, key):
    # TODO: to enhance, cut in multiple functions
    device_router = routers['Device']
    properties_router = routers['Properties']
    device, new_data = device_data.items()[0]

    collector = new_data.get('collector', 'localhost')
    if collector not in collectors:
        collector = 'localhost'

    device_uid = '/zport/dmd/Devices{}/devices/{}'.format(dc_uid, device)
    # print('device_id: {}'.format(device_uid))

    response = device_router.callMethod('objectExists', uid=device_uid)
    if response['result']['exists']:
        # print('Device is present')
        # Device is already present with same uid
        pass

        # Check cProperties

    else:
        # print('Device is absent')
        device_elsewhere = [d for d in devices_fulllist if d['name'] == device]
        # print(device_elsewhere)
        if device_elsewhere:
            # move it
            response = device_router.callMethod('moveDevices',
                                                uids=[device_elsewhere[0]['uid']],
                                                target='/zport/dmd/Devices{}'.format(dc_uid),
                                                )
            # print(response)
            time.sleep(6)
        else:
            cprop = [(k, v['value']) for k, v in new_data.get('cProperties', {}).items()]

            # TODO: ipAddress, comments
            # TODO: if -1, keep -1
            # TODO: switch to apply value from input file or 400
            productionState = 400
            response = device_router.callMethod('addDevice', deviceName=device,
                                                deviceClass=dc_uid,
                                                manageIp=new_data.get('ipAddressString', ''),
                                                model=False,
                                                title=new_data.get('name', None),
                                                collector=collector,
                                                locationPath=new_data.get('location', ''),
                                                systemPaths=new_data.get('systems', ''),
                                                groupPaths=new_data.get('groups', ''),
                                                productionState=400,
                                                priority=new_data.get('priority', ''),
                                                zProperties=new_data.get('zProperties', {}),
                                                cProperties=cprop,
                                                )

            # id already present ? Move ?
            if not response['result']['success']:
                print(response)
                # exit()
            time.sleep(10)

    # Properties
    # Check variables
    response = device_router.callMethod('getInfo', uid=device_uid)
    if response['result']['success']:
        current_data = response['result']['data']
        # print(response)
        device_fields = ['priority', 'comments']
        for k in device_fields:
            if not k in new_data:
                continue
            if new_data[k] != current_data[k]:
                info_data = {'uid': device_uid, k: new_data[k]}
                response = device_router.callMethod('setInfo', **info_data)
                if not response['result']['success']:
                    print(response)
                    print(current_data)
                    print(new_data[k])
                    print(current_data[k])
                    exit()
        if 'ipAddressString' in new_data and current_data['ipAddressString'] != new_data['ipAddressString']:
            response = device_router.callMethod('resetIp', hashcheck=None, uids=[device_uid],
                                                ip=new_data['ipAddressString'])
            if not response['result']['success']:
                print(response)
                exit()
        if 'groups' in new_data:
            current_groups = sorted([s['path'] for s in current_data['groups']])
            if current_groups != sorted(new_data['groups']):
                # TODO: delete other groups : removeDevices, uids=[device_uid], uid=group
                for group in new_data['groups']:
                    target = '/zport/dmd{}'.format(group)
                    response = device_router.callMethod('moveDevices', uids=[device_uid], ranges=[], target=target)
                    if not response['result']['success']:
                        print(response)
                        exit()
        if 'systems' in new_data:
            current_systems = sorted([s['path'] for s in current_data['systems']])
            if current_systems != sorted(new_data['systems']):
                # TODO: delete other systems : removeDevices, uids=[device_uid], uid=system
                for system in new_data['systems']:
                    target = '/zport/dmd{}'.format(system)
                    response = device_router.callMethod('moveDevices', uids=[device_uid], ranges=[], target=target)
                    if not response['result']['success']:
                        print(response)
                        exit()
        if 'location' in new_data:
            current_location = current_data['location']
            if current_location:
                current_location = current_location.get('name', None)
            if current_location != new_data['location']:
                target = 'zport/dmd/Locations{}'.format(new_data['location'])
                response = device_router.callMethod('moveDevices', uids=[device_uid], target=target)
                if not response['result']['success']:
                    print(response)
                    exit()

    # Check cProperties
    device_cprop = new_data.get('cProperties', [])
    if device_cprop:
        response = properties_router.callMethod('query', uid=device_uid, constraints={'idPrefix': 'c'})
        if response['result']['success']:
            cprop_data = response['result']['data']
            # print(cprop_data)
            # print(device_cprop)
            for k, v in device_cprop.items():
                current_prop = [p for p in cprop_data if p['id'] == k][0]
                # print(current_prop)
                if v['value'] != current_prop['value']:
                    response = properties_router.callMethod('setZenProperty', uid=device_uid,
                                                            zProperty=k, value=v['value'])
                    if not response['result']['success']:
                        print(response)
                        print('uid: {}'.format(uid))
                        print('zprop: {} = {}'.format(k, v['value']))
                        exit()


    # Check zProperties
    # TODO: replace with import_properties ????
    device_zprop = new_data.get('zProperties', [])
    if device_zprop:
        response = properties_router.callMethod('query', uid=device_uid, constraints={'idPrefix': 'z'})
        # print(response)
        # response2 = properties_router.callMethod('getZenProperties', uid=device_uid)
        # print(response2)

        if response['result']['success']:
            zprop_data = response['result']['data']
            for k, v in device_zprop.items():
                print(k)
                current_prop = [p for p in zprop_data if p['id'] == k][0]
                # print(current_prop)
                # print(current_prop['value'])
                # print(v)

                if current_prop['type'] == 'password' or v != current_prop['value']:
                    # print('Different values')
                    if current_prop['type'] == 'lines':
                        v = '\n'.join(v)
                    elif current_prop['type'] == 'password':
                        f = Fernet(key)
                        v = f.decrypt(v)
                        print(v)

                    response = properties_router.callMethod('setZenProperty', uid=device_uid,
                                                            zProperty=k, value=v)
                    if not response['result']['success']:
                        print(response)
                        print('uid: {}'.format(uid))
                        print('zprop: {} = {}'.format(k, v['value']))
                        exit()
                elif not (current_prop['islocal'] and current_prop['uid'] == device_uid):
                    valuemap = {'lines': [], 'boolean': None, 'int': 0, 'float': 0.0, 'string': None}
                    nullvalue = valuemap[current_prop['type']]
                    # print(current_prop)
                    response = properties_router.callMethod('setZenProperty', uid=device_uid, zProperty=k,
                                                            value=nullvalue)
                    if not response['result']['success']:
                        print(response)
                        print('uid: {}'.format(uid))
                        print('zprop: {} = {}'.format(k, v['value']))
                        exit()
                    response = properties_router.callMethod('setZenProperty', uid=device_uid, zProperty=k, value=v)
                    if not response['result']['success']:
                        print(response)
                        print('uid: {}'.format(uid))
                        print('zprop: {} = {}'.format(k, v['value']))
                        exit()


    '''
    # Templates
    # To manage with zDeviceTemplates ???
    if 'templates' in new_data:
        # new_templates = sorted(new_data['templates'])
        new_templates = new_data['templates']
        print(new_templates)
        response = device_router.callMethod('getBoundTemplates', uid=device_uid)
        if response['result']['success']:
            bound_templates = [t[0] for t in response['result']['data']]
            print(bound_templates)
            if new_templates != bound_templates:
                response = device_router.callMethod('setBoundTemplates', uid=device_uid, templateIds=new_templates)
                if not response['result']['success']:
                    print(response)
                    exit()
    '''

    '''
    addDevice(self, deviceName, deviceClass, title=None, snmpCommunity="", snmpPort=161, manageIp="", 
    model=False, collector='localhost', rackSlot=0, locationPath="", systemPaths=[], groupPaths=[], 
    productionState=1000, comments="", hwManufacturer="", hwProductName="", 
    osManufacturer="", osProductName="", priority=3, tag="", serialNumber="", zCommandUsername="", 
    zCommandPassword="", zWinUser="", zWinPassword="", zProperties={}, cProperties={})
    '''

    return


def import_properties(routers, uid, new_data, key):
    properties_router = routers['Properties']
    # cProperties
    response = properties_router.callMethod('query', uid=uid, constraints={'idPrefix': 'c'})
    current_prop_data = sorted(response['result']['data'], key=lambda i: i['id'])
    for k, v in new_data.get('cProperties', {}).items():
        # TODO: Check if islocal shouldn't be a check
        current_prop = [p for p in current_prop_data if p['id'] == k]
        if current_prop:
            current_prop = current_prop[0]
            prop_type = current_prop['type']
            if prop_type == 'string':
                new_value = str(v.get('value', ''))
            elif prop_type == 'int':
                new_value = int(v.get('value', ''))
            elif prop_type == 'date':
                new_value = str(v.get('value', ''))
            else:
                print('cProperty {} of unknown type: {}'.format(k, prop_type))
                exit()
            if new_value != current_prop['value']:
                # TODO: Value depends on type !!
                response = properties_router.callMethod('setZenProperty', uid=uid,
                                                        zProperty=k, value=new_value)
        else:
            response = properties_router.callMethod('addCustomProperty', id=k,
                                                    value=v.get('value', ''),
                                                    label=v.get('label', ''),
                                                    uid=uid,
                                                    type=v.get('type', 'string'))
            if not response['result']['success']:
                print(response)
                print('k:{} - value:{} - uid:{} - type:{}'.format(k, v.get('value', ''), uid, v.get('type', 'string')))
                print(current_prop_data)
                exit()

    # zProperties
    response = properties_router.callMethod('query', uid=uid, constraints={'idPrefix': 'z'})
    current_prop_data = sorted(response['result']['data'], key=lambda i: i['id'])
    for k, v in new_data.get('zProperties', {}).items():
        current_prop = [p for p in current_prop_data if p['id'] == k]
        if current_prop:
            prop_type = current_prop[0]['type']
            if prop_type == 'boolean':
                pass
            elif prop_type == 'int':
                v = int(v)
            elif prop_type == 'float':
                pass
            elif prop_type == 'lines':
                pass  # v is a string
            elif prop_type == 'string':
                pass
            elif prop_type == 'password':
                f = Fernet(key)
                v = f.decrypt(v)
            else:
                print('zProperty {} of unknown type: {}'.format(k, prop_type))
                exit()
            if prop_type == 'password' or v != current_prop[0]['value']:
                response = properties_router.callMethod('setZenProperty', uid=uid, zProperty=k, value=v)
                if not response['result']['success']:
                    print(response)
                    print('uid: {}'.format(uid))
                    print('zprop: {} = {}'.format(k, v['value']))
                    exit()
            if not current_prop[0]['islocal']:
                valuemap = {'lines': [], 'boolean': None, 'int': 1, 'float': 1.0, 'string': '',
                            'password': ''}
                nullvalue = valuemap[current_prop[0]['type']]
                response = properties_router.callMethod('setZenProperty', uid=uid, zProperty=k, value=nullvalue)
                if not response['result']['success']:
                    print(response)
                    print('uid: {}'.format(uid))
                    print('zprop: {} = {}'.format(k, v))
                    print('nullvalue: {}'.format(nullvalue))
                    exit()
                response = properties_router.callMethod('setZenProperty', uid=uid, zProperty=k, value=v)
                if not response['result']['success']:
                    print(response)
                    print('uid: {}'.format(uid))
                    print('zprop: {} = {}'.format(k, v))
                    exit()
    return


def import_group(routers, current_groups, data):
    device_router = routers['Device']
    group, new_data = data.items()[0]
    if group not in current_groups:
        group_br = group.split('/')
        id = group_br[-1]
        contextUid = '/zport/dmd/Groups{}'.format('/'.join(group_br[:-1]))
        response = device_router.callMethod('addNode',
                                            id=id,
                                            description=new_data.get('description', ''),
                                            type='organizer', contextUid=contextUid)
        if not response['result']['success']:
            tqdm.write('Failed to create {}'.format(group))
            print(response)
            exit()
    return


def import_system(routers, current_systems, data):
    device_router = routers['Device']
    system, new_data = data.items()[0]
    if system not in current_systems:
        system_br = system.split('/')
        id = system_br[-1]
        contextUid = '/zport/dmd/Systems{}'.format('/'.join(system_br[:-1]))
        response = device_router.callMethod('addNode',
                                            id=id,
                                            description=new_data.get('description', ''),
                                            type='organizer', contextUid=contextUid)
        if not response['result']['success']:
            tqdm.write('Failed to create {}'.format(system))
            print(response)
            exit()
    return


def import_location(routers, current_locations, data):
    device_router = routers['Device']
    location, new_data = data.items()[0]
    if location not in current_locations:
        location_br = location.split('/')
        id = location_br[-1]
        contextUid = '/zport/dmd/Locations{}'.format('/'.join(location_br[:-1]))
        response = device_router.callMethod('addNode',
                                            id=id,
                                            description=new_data.get('description', ''),
                                            type='organizer', contextUid=contextUid)
        if not response['result']['success']:
            tqdm.write('Failed to create {}'.format(location))
            print(response)
            exit()
    # TODO: check fields for existing location
    return


def import_deviceclass(routers, device_classes_list, dc_data, key):
    device_router = routers['Device']
    device_class, new_data = dc_data.items()[0]
    if device_class not in device_classes_list:
        # Device class absent
        add_deviceclass(routers, device_class)
    dc_uid = '/zport/dmd/Devices{}'.format(device_class)
    # Properties
    import_properties(routers, dc_uid, new_data, key)
    # Devices

    return


def compact_data(data):
    fields = ['action', 'action_timeout', 'uid', 'enabled', 'send_clear', 'send_initial_occurrence', 'delay_seconds',
              'repeat_seconds', 'recipients', 'subscriptions']
    xfields = ['body_content_type', 'subject_format', 'body_format', 'clear_subject_format', 'clear_body_format',
               'skipfails', 'email_from', 'host', 'port', 'useTls', 'user', 'password']

    output = {k: data[k] for k in fields if data.get(k, '') != ''}

    output['subscriptions'] = [t['uuid'] for t in data['subscriptions']]
    content_items = data['content']['items'][0]['items']
    for k in xfields:
        for item in content_items:
            if item['name'] == k:
                content_items.remove(item)
                break
        else:
            item = {'value': None}
        output[k] = item['value']
    return output


def parse_groups(routers, input):
    print('Loading input file')
    data = yaml.safe_load(file(input, 'r'))         # dict
    print('Loaded input file')
    if 'groups' not in data:
        print('No group found. Skipping.')
        return
    groups = sorted(data['groups'])
    print('Found {} groups in input.'.format(len(groups)))

    print('Loading existing groups')
    response = device_router.callMethod('getGroups', uid='/zport/dmd/Devices')
    groups_list = response['result']['groups']
    groups_list = [g['name'] for g in groups_list]
    print('Found {} existing groups'.format(len(groups_list)))

    group_loop = tqdm(groups, desc='Group', ascii=True, file=sys.stdout)
    for group in group_loop:
        desc = 'Group ({})'.format(group)
        group_loop.set_description(desc)
        group_loop.refresh()
        group_data = {group: data['groups'][group]}
        import_group(routers, groups_list, group_data)
    return


def parse_systems(routers, input):
    print('Loading input file')
    data = yaml.safe_load(file(input, 'r'))         # dict
    print('Loaded input file')
    if 'systems' not in data:
        print('No system found. Skipping.')
        return
    systems = sorted(data['systems'])
    print('Found {} systems in input.'.format(len(systems)))

    print('Loading existing systems')
    response = device_router.callMethod('getSystems', uid='/zport/dmd/Devices')
    systems_list = response['result']['systems']
    systems_list = [g['name'] for g in systems_list]
    print('Found {} existing systems'.format(len(systems_list)))

    system_loop = tqdm(systems, desc='System', ascii=True, file=sys.stdout)
    for system in system_loop:
        desc = 'System ({})'.format(system)
        system_loop.set_description(desc)
        system_loop.refresh()
        system_data = {system: data['systems'][system]}
        import_system(routers, systems_list, system_data)
    return


def parse_locations(routers, input):
    print('Loading input file')
    data = yaml.safe_load(file(input, 'r'))         # dict
    print('Loaded input file')
    if 'locations' not in data:
        print('No location found. Skipping.')
        return
    locations = sorted(data['locations'])
    print('Found {} locations in input.'.format(len(locations)))

    print('Loading existing locations')
    response = device_router.callMethod('getLocations', uid='/zport/dmd/Devices')
    locations_list = response['result']['locations']
    locations_list = [g['name'] for g in locations_list]
    print('Found {} existing locations'.format(len(locations_list)))

    location_loop = tqdm(locations, desc='Location', ascii=True, file=sys.stdout)
    for location in location_loop:
        desc = 'Location ({})'.format(location)
        location_loop.set_description(desc)
        location_loop.refresh()
        location_data = {location: data['locations'][location]}
        import_location(routers, locations_list, location_data)
    return


def parse_deviceclasses(routers, input, key):
    print('Loading input file')
    data = yaml.safe_load(file(input, 'r'))         # dict
    print('Loaded input file')
    if 'device_classes' not in data:
        print('No Device Class found. Skipping.')
        return
    device_classes = sorted(data['device_classes'])
    # device_classes = device_classes[:10]
    print('Found {} Device Classes in input.'.format(len(device_classes)))

    print('Loading existing device_classes')
    response = device_router.callMethod('getDeviceClasses', uid='/zport/dmd/Devices')
    device_classes_list = sorted(response['result']['deviceClasses'], key=lambda i: i['name'])
    device_classes_list = [dc['name'] for dc in device_classes_list if dc['name']]
    print('Found {} existing Device Classes'.format(len(device_classes_list)))


    print('Loading existing devices')
    response = device_router.callMethod('getCollectors')
    collectors = response['result']

    devices_fulllist = []
    for batch in device_router.pagingMethodCall('getDevices', keys=['name']):
        # print(response)
        devices_fulllist.extend(batch['result']['devices'])
    print('Found {} existing devices'.format(len(devices_fulllist)))

    dc_loop = tqdm(device_classes, desc='Device Class', ascii=True, file=sys.stdout)
    for dc in dc_loop:
        desc = 'Device Class ({})'.format(dc)
        dc_loop.set_description(desc)
        dc_loop.refresh()
        dc_data = {dc: data['device_classes'][dc]}
        import_deviceclass(routers, device_classes_list, dc_data, key)
        dc_devices = sorted(data['device_classes'][dc].get('devices', []))
        if dc_devices:
            dc_uid = dc
            dev_loop = tqdm(dc_devices, desc='Device ', ascii=True, file=sys.stdout)
            for device in dev_loop:
                desc = 'Device ({})'.format(device)
                dev_loop.set_description(desc)
                dev_loop.refresh()
                device_data = {device: data['device_classes'][dc]['devices'][device]}
                add_device(routers, dc_uid, device_data, collectors, devices_fulllist, key)

    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Manage Devices')
    parser.add_argument('-s', dest='environ', action='store', default='z6_test')
    parser.add_argument('-f', dest='input', action='store', default='devices_input.yaml')
    parser.add_argument('-k', dest='key', action='store', default='')
    options = parser.parse_args()
    environ = options.environ
    input = options.input
    key = options.key

    print('Connecting to Zenoss')
    # Routers
    device_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='DeviceRouter')
    properties_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='PropertiesRouter')

    routers = {
        'Device': device_router,
        'Properties': properties_router,
    }

    # TODO: The following functions do not edit the item if already present
    parse_groups(routers, input)
    parse_systems(routers, input)
    parse_locations(routers, input)
    parse_deviceclasses(routers, input, key)
