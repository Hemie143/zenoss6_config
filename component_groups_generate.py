import zenAPI.zenApiLib
import argparse
import re
import yaml
import sys
from tqdm import tqdm


def parse_component_groups(routers, inputfile):
    device_router = routers['Device']
    component_groups_router = routers['ComponentGroup']
    print('Loading input file')
    # TODO: In a try
    data = yaml.safe_load(file(inputfile, 'r'))         # dict
    print('Loaded input file')
    if 'componentgroups' not in data:
        print('No Component Group found. Skipping.')
        return
    component_groups = sorted(data['componentgroups'])
    print('Found {} Component Groups in input.'.format(len(component_groups)))

    for cgroup in component_groups:
        print(cgroup)
        uid = '/zport/dmd/ComponentGroups{}'.format(cgroup)
        response = device_router.callMethod("objectExists", uid=uid)
        uid_exists = response['result']['exists']
        if not uid_exists:
            start = len('/zport/dmd/ComponentGroups')
            path = uid[start:]
            response = device_router.callMethod("addNode", contextUid="/zport/dmd/ComponentGroups", id=path,
                                                type="organizer")
            if not response['result']['success']:
                print(response)
        comps = data['componentgroups'][cgroup]
        valid_comps = []
        for comp in comps:
            response = device_router.callMethod("objectExists", uid=comp)
            if response['result']['exists']:
                valid_comps.append(comp)
        if valid_comps:
            response = component_groups_router.callMethod("addComponentsToGroup", targetUid=uid, uids=valid_comps)
            if not response['result']['success']:
                print(response)
            # print(response)




if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate Component Groups')
    parser.add_argument('-s', dest='environ', action='store', default='z6_test')
    parser.add_argument('-f', dest='input', action='store', default='component_groups_input.yaml')
    options = parser.parse_args()
    environ = options.environ
    inputfile = options.input

    device_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='DeviceRouter')
    component_groups_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='ComponentGroupRouter')
    properties_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='PropertiesRouter')

    routers = {
        'Device': device_router,
        'ComponentGroup': component_groups_router,
        'Properties': properties_router,
    }

    # TODO: This tool should generate and fill in component groups, based on rules. This is to add components that are
    # being replaced by a similar component with a different uid (regularly seen in K8s environments, for example).
    parse_component_groups(routers, inputfile)
