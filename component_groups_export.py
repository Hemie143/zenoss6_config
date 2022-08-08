import zenAPI.zenApiLib
import argparse
import yaml

def parse_branch(routers, uid, data):
    device_router = routers['Device']
    component_groups_router = routers['ComponentGroup']

    response = device_router.callMethod('asyncGetTree', id=uid)
    for child in response['result']:
        print(child['uid'])
        parse_branch(routers, child['uid'], data)
    if len(response['result']) == 0:
        start = len('/zport/dmd/ComponentGroups')
        path = uid[start:]
        # TODO: should use pagingMethod
        response = component_groups_router.callMethod('getComponents', uid=uid, dir="ASC", params={},
                                                      sort="name", keys=["uid", "device"])
        components = response['result']['data']
        data["componentgroups"].update({path: []})
        data["componentgroups"][path] = sorted([c['uid'] for c in components])


def parse_tree(routers, id, cg_data):
    # The root level has children, deeper, the same query returns directly a list including the children
    device_router = routers['Device']
    response = device_router.callMethod('asyncGetTree', id=id)
    root = response['result'][0]
    for child in root['children']:
        print(child['uid'])
        # I don't expect any component directly under the root level
        parse_branch(routers, child['uid'], cg_data)

def get_component_groups(routers, output, full_data):
    full_data = {"componentgroups": {}}
    parse_tree(routers, '/zport/dmd/ComponentGroups', full_data)
    yaml.safe_dump(full_data, file(output, 'w'), encoding='utf-8', allow_unicode=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Export Component Groups')
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
