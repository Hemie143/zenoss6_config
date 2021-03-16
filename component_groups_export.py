import zenAPI.zenApiLib
import argparse
import re
import yaml
import sys
from tqdm import tqdm

def get_properties(routers, uid):
    properties_router = routers['Properties']
    # TODO: take into account the type of the values (string, int...)
    # TODO: for cProperties, also export the type, label and description
    # cProperties
    response = properties_router.callMethod('query', uid=uid, constraints={'idPrefix': 'c'})
    data = sorted(response['result']['data'], key=lambda i: i['id'])
    prop_data = {}
    for prop in data:
        if prop['islocal']:
            if prop['type'] == 'date':
                v = prop.get('valueAsString', '')
            elif prop['type'] == 'string' or prop['type'] is None:
                v = prop.get('value', '')
                prop['type'] = 'string'
            elif prop['type'] == 'int':
                v = prop.get('value', None)
            else:
                print(prop)
                exit()
            if v:
                if 'cProperties' not in prop_data:
                    prop_data['cProperties'] = {}
                prop_data['cProperties'][prop['id']] = {}
                prop_data['cProperties'][prop['id']]['value'] = v
                prop_data['cProperties'][prop['id']]['type'] = prop.get('type', 'string')
    # zProperties
    response = properties_router.callMethod('query', uid=uid, constraints={'idPrefix': 'z'})
    data = sorted(response['result']['data'], key=lambda i: i['id'])
    for prop in data:
        if prop['islocal'] and prop['uid'] == uid and prop['id'] not in ['zSnmpEngineId']:
            # print(prop)
            if prop['type'] == 'boolean':
                v = bool(prop['value'])
            elif prop['type'] == 'int':
                if prop['value'] is None:
                    v = None
                else:
                    v = int(prop['value'])
            elif prop['type'] == 'float':
                v = float(prop['value'])
            elif prop['type'] in ['password', 'instancecredentials', 'multilinecredentials']:
                v = None
            elif prop['type'] == 'string':
                v = str(prop['value'])
            elif prop['type'] == 'lines':
                v = prop['value']           # List
            else:
                print(prop)
                exit()
            # v = prop.get('valueAsString', '')
            # What if v is boolean False ?
            # TODO: next condition to enhance
            if not v is None:
                if 'zProperties' not in prop_data:
                    prop_data['zProperties'] = {}
                prop_data['zProperties'][prop['id']] = v
    return prop_data


def parse_tree(routers, id, cg_data={}):
    device_router = routers['Device']
    component_groups_router = routers['ComponentGroup']

    response = device_router.callMethod('asyncGetTree', id=id)
    results = response['result']
    for item in results:
        cg_data[item['path']] = {}
        print('CG: {}'.format(item['path']))
        print('leaf: {}'.format(item['leaf']))
        response = component_groups_router.callMethod('getComponents', uid=item['uid'])
        # print(response)
        print('Components -------------------------------------------------')
        components = response['result']['data']

        totalCount = response['result']['totalCount']
        print('totalCount: {}'.format(totalCount))

        # print('Components: {}'.format(len(components)))

        components = []
        for comp in components:
            # print(comp)
            pass
        if not item['leaf']:
            # print('Component Group -------------------------------------------------')
            # print(item)
            uid = item['uid']
            if not uid == '/zport/dmd/ComponentGroups':
                parse_tree(routers, item['uid'], cg_data)



        if 'children' in item:
            children = item['children']
            # print(children)
            for child in children:
                print('Child -------------------------------------------------')
                # print(child)
                parse_tree(routers, child['uid'], cg_data)
                pass


    """
    {action: "ComponentGroupRouter", method: "getComponents",}
    action: "ComponentGroupRouter"
    data: [{uid: "/zport/dmd/ComponentGroups/Applications/Production/Integrations", params: {},}]
    0: {uid: "/zport/dmd/ComponentGroups/Applications/Production/Integrations", params: {},}
    dir: "ASC"
    keys: ["icon", "name", "device", "meta_type", "monitored", "productionState", "locking", "events", "uid"]
    limit: 100
    page: 1
    params: {}
    sort: "name"
    start: 0
    uid: "/zport/dmd/ComponentGroups/Applications/Production/Integrations"
    method: "getComponents"
    """

    """
    {action: "ComponentGroupRouter", method: "addComponentsToGroup",}
    action: "ComponentGroupRouter"
    data: [{targetUid: "/zport/dmd/ComponentGroups/Applications/Production/Ereg", uids: [,]}]
    0: {targetUid: "/zport/dmd/ComponentGroups/Applications/Production/Ereg", uids: [,]}
    targetUid: "/zport/dmd/ComponentGroups/Applications/Production/Ereg"
    uids: [,]
    0: "/zport/dmd/Devices/Server/SSH/Linux/APP/devices/dvb-appstable-l02.dev.credoc.be/os/processes/zport_dmd_Processes_Linux_Tomcat_osProcessClasses_tcinstances_60d1d4e9c702fbc592dbfce7ba8cfb90"
    method: "addComponentsToGroup"
    tid: 32
    """

def get_component_groups(routers, output, full_data):
    parse_tree(routers, '/zport/dmd/ComponentGroups', full_data)
    yaml.safe_dump(full_data, file(output, 'w'), encoding='utf-8', allow_unicode=True)
    exit()


    component_groups_router = routers['ComponentGroup']
    dir = 'ASC'
    sort = 'name'
    keys = ["icon", "name", "device", "meta_type", "monitored", "productionState", "locking", "events", "uid"]
    response = component_groups_router.callMethod('getComponents', uid='/zport/dmd/ComponentGroups',
                                                  dir=dir, sort=sort, keys=keys)

    groups_data = response['result']['data']

    groups = sorted(response['result']['data'], key=lambda i: i['name'])
    # groups_data = {'groups': {}}
    for group in tqdm(groups_data, desc='Component Groups         ', ascii=True):

        print(group)
        continue

        g_uid = '/zport/dmd/Groups{}'.format(group['name'])
        response = device_router.callMethod('getInfo', uid=g_uid)
        data = response['result']['data']
        group_name = data['name']
        groups_data['groups'][group_name] = {}
        groups_data['groups'][group_name]['name'] = data['id']
        desc = data.get('description', '')
        if desc:
            groups_data['groups'][group_name]['description'] = desc
    full_data.update(groups_data)
    yaml.safe_dump(full_data, file(output, 'w'), encoding='utf-8', allow_unicode=True)
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='List devices')
    parser.add_argument('-s', dest='environ', action='store', default='z6_test')
    parser.add_argument('-f', dest='output', action='store', default='component_groups_output.yaml')
    options = parser.parse_args()
    environ = options.environ
    output = options.output

    device_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='DeviceRouter')
    component_groups_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='ComponentGroupRouter')
    properties_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='PropertiesRouter')

    routers = {
        'Device': device_router,
        'ComponentGroup': component_groups_router,
        'Properties': properties_router,
    }

    data = {}
    get_component_groups(routers, output, data)

