import zenAPI.zenApiLib
import argparse
import logging
import re
import sys
import yaml
from tqdm import tqdm


def get_dcdevices(routers, uid):
    device_router = routers['Device']

    device_fields = ['name', 'collector', 'ipAddressString', 'productionState', 'priority', 'comments',
                     'systems', 'groups', 'location']

    dc_devices = []
    for page in device_router.pagingMethodCall('getDevices', uid=uid, keys=['uid'], sort='name', dir='ASC'):
        if not page['result']['success']:
            print('getdcdevices - getDevices - {} = {}'.format(uid, response))
            continue
        page_devices = page['result']['devices']
        for d in page_devices:
            if d['uid'].startswith('{}/devices/'.format(uid)):
                dc_devices.append(d['uid'])
    devices_data = {}
    for device in dc_devices:
        device_data = {}
        # monitored: monitored flag in grid. Defines whether the component is monitored or not.
        # monitor: ?
        # usesMonitorAttribute
        response = device_router.callMethod('getComponents', uid=device, keys=["uid", "meta_type", "monitored",
                                                                               "monitor", "locking",
                                                                               "usesMonitorAttribute"])
        data = response['result']['data']
        for component in data:
            comp_data = {}
            if 'monitor' in component and not component['monitor']:
                comp_uid = component['uid']
                if comp_data == {} or comp_uid not in comp_data:
                    comp_data.update({comp_uid: {}})
                comp_data[comp_uid]['monitor'] = component['monitor']
                # comp_data[comp_uid].update({'monitor': component['monitor']})
            if any(component['locking'].values()):
                comp_uid = component['uid']
                print(device)
                print(comp_uid)
                if comp_data == {} or comp_uid not in comp_data:
                    comp_data.update({comp_uid: {}})
                comp_data[comp_uid]['locking'] = component['locking']
            if comp_data:
                device_data.update({'components':comp_data})
        if device_data:
            if 'devices' not in devices_data:
                devices_data['devices'] = {}
            devices_data['devices'].update({device: device_data})
        # response = device_router.callMethod('getComponentTree', uid=device)
        # print(device)
        # print(response)

        # if not response['result']['success']:
        #     print('getdcdevices - getInfo - {} = {}'.format(device, response))
        #     continue
        # data = response['result']['data']



    return devices_data



def get_components(routers, output, full_data):
    device_router = routers['Device']
    response = device_router.callMethod('getDeviceClasses', uid='/zport/dmd/Devices')
    device_classes = sorted(response['result']['deviceClasses'], key=lambda i: i['name'])
    # device_classes = device_classes[:10]
    devices_data = {'components': {}}
    # with open(output, 'a') as f:
    #     f.write('device_classes:\r\n')

    dc_loop = tqdm(device_classes, desc='Device Class', ascii=True, file=sys.stdout)
    for device_class in dc_loop:
        dc_name = device_class['name']
        if not dc_name:
            continue
        desc = 'Device Class ({})'.format(dc_name)
        dc_loop.set_description(desc)
        dc_loop.refresh()

        devices_data['components'][dc_name] = {}
        if dc_name == '/':
            dc_uid = '/zport/dmd/Devices'
        else:
            dc_uid = '/zport/dmd/Devices{}'.format(dc_name)

        devices = get_dcdevices(routers, dc_uid)
        devices_data['components'][dc_name].update(devices)

        full_data.update(devices_data)
        yaml.safe_dump(full_data, file(output, 'w'), encoding='utf-8', allow_unicode=True, sort_keys=True)
    return

def export(environ, output):
    device_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='DeviceRouter')
    properties_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='PropertiesRouter')

    routers = {
        'Device': device_router,
        'Properties': properties_router,
    }

    data = {}
    get_components(routers, output, data)

def parse_components(routers, inputfile):
    device_router = routers['Device']
    print('Loading input file')
    # TODO: In a try
    data = yaml.safe_load(file(inputfile, 'r'))         # dict
    print('Loaded input file')
    if 'devices' not in data:
        print('No Device found. Skipping.')
        return
    comp_data = sorted(data['devices'])
    print('Found {} Devices in input.'.format(len(comp_data)))

    # TODO: process alphabetically
    devices_list = sorted(data['devices'])
    # print(devices_list)
    # for name, n_data in data['devices'].items():
    for name in devices_list:
        # Look for device
        print('Processing device {}'.format(name))
        params = {'name': name}
        keys = ['name', 'uid']
        response = device_router.callMethod("getDevices", uid='/zport/dmd/', params=params, keys=keys)
        if not response['result']['success']:
            print('Could not find device {}'.format(name))
            continue
        if response['result']['totalCount'] > 1:
            print('Found {:d} devices - Name {} is too ambiguous'.format(response['result']['totalCount'], name))
            print(response)
            continue
        # print(response['result']['devices'])
        device_data = response['result']['devices'][0]

        device_name = device_data['name']

        device_uid = device_data['uid']
        keys = ['id', 'monitored', 'locking']
        response = device_router.callMethod("getComponents", uid=device_uid, meta_type='IpService', keys=keys)
        if not response['result']['success']:
            print('Could not list IPServices for device {}'.format(device_name))
            continue
        device_ipservices = response['result']['data']
        config_ipservices = data['devices'][name]
        # print(config_ipservices)
        for config_ipservice, config_data in config_ipservices.items():
            print('   IPService: {}'.format(config_ipservice))
            for comp in device_ipservices:
                if comp['id'] == config_ipservice:
                    # print('Found ipservice {}'.format(config_ipservice))
                    # print('Found ipservice {} - Monitored= {}'.format(config_ipservice, comp['monitored']))
                    # print('Found ipservice {} - {}'.format(config_ipservice, config_data))
                    # TODO: Check field monitored
                    if comp['monitored'] != config_data['monitored']:
                        response = device_router.callMethod("setComponentsMonitored", uids=[comp['uid']],
                                                            monitor=config_data['monitored'], hashcheck=None)
                        # print(response)
                        if not response['result']['success']:
                            print('Could not list change monitored status for component on device {}'.
                                  format(comp['id'], device_name))
                            continue
                    # TODO: Check validity of keys
                    # TODO: replace following with comprehension ?
                    correct_lock = False
                    for k, v in config_data['locking'].items():
                        if k not in comp['locking']:
                            print('comp:  {}'.format(comp))
                            exit()

                        if comp['locking'][k] != v:
                            correct_lock = True
                            break
                    if correct_lock:
                        response = device_router.callMethod("lockComponents", uids=[comp['uid']], hashcheck=None,
                                                            deletion=config_data['locking']['deletion'],
                                                            sendEvent=config_data['locking']['events'],
                                                            updates=config_data['locking']['updates'],
                                                            )
                        # print(response)
                        if not response['result']['success']:
                            print('Could not list change locking status for component on device {}'.
                                  format(comp['id'], device_name))
                            continue
                    break
            else:
                print('   IPService NOT FOUND: {}'.format(config_ipservice))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import Component settings')
    parser.add_argument('-s', dest='environ', action='store', default='z6_test')
    parser.add_argument('-f', dest='input', action='store', default='components_ipservices_input.yaml')
    options = parser.parse_args()
    environ = options.environ
    inputfile = options.input

    device_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='DeviceRouter')
    properties_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='PropertiesRouter')

    routers = {
        'Device': device_router,
        'Properties': properties_router,
    }

    parse_components(routers, inputfile)