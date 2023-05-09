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
    if 'components' not in data:
        print('No Component found. Skipping.')
        return
    comp_data = sorted(data['components'])
    print('Found {} Device classes in input.'.format(len(comp_data)))

    # TODO: Code is dirty
    # TODO: Process with sorted data
    for dev_class in comp_data:
        dc_uid = '/zport/dmd/Devices{}'.format(dev_class)
        response = device_router.callMethod("objectExists", uid=dc_uid)
        dc_exists = response['result']['exists']
        if not dc_exists:
            print('Device class {} is missing. Skipping.'.format(dev_class))
            continue
        dc_devices = data['components'][dev_class]
        if 'devices' not in dc_devices:
            continue
        for dev, dev_data in dc_devices['devices'].items():
            print(dev)
            for comp, comp_data in dev_data['components'].items():
                print(comp)
                response = device_router.callMethod("objectExists", uid=comp)
                comp_exists = response['result']['exists']
                if not comp_exists:
                    print('Component {} is missing. Skipping.'.format(comp))
                    continue

                if 'monitor' in comp_data:
                    response = device_router.callMethod("setComponentsMonitored", uids=[comp],
                                                        monitor=comp_data['monitor'], ranges=[], hashcheck=None)
                    if not response['result']['success']:
                        print(response)
                if 'locking' in comp_data:
                    print('LOCKING')
                    print(comp_data['locking'])
                    response = device_router.callMethod("lockComponents", uids=[comp],
                                                        updates=comp_data['locking']['updates'],
                                                        deletion=comp_data['locking']['deletion'],
                                                        sendEvent=comp_data['locking']['events'],
                                                        ranges=[], hashcheck=None)
                    if not response['result']['success']:
                        print(response)
                        exit()

        # exit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import Component settings')
    parser.add_argument('-s', dest='environ', action='store', default='z6_test')
    parser.add_argument('-f', dest='input', action='store', default='components_input.yaml')
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