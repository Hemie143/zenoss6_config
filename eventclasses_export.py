import zenAPI.zenApiLib
import argparse
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


def get_transforms(routers, uid):
    eventclass_router = routers['EventClasses']
    response = eventclass_router.callMethod('getTransformTree', uid=uid)
    if not response['result']['success']:
        print('get_transforms - response: {}'.format(response))
        return {}
    data = response['result']['data']
    id = uid[10:]
    transform_data = {}
    for transform in data:
        if transform['transid'] == id:
            transform_code = transform['trans']
            if transform_code:
                transform_data = dict(transform=transform_code)
            break
    return transform_data


def get_mappings(routers, uid):
    eventclass_router = routers['EventClasses']
    response = eventclass_router.callMethod('getInstances', uid=uid)
    data = response['result']['data']
    fields = ['eventClassKey', 'rule', 'regex', 'example', 'sequence', 'evaluation', 'resolution', 'transform']

    mapping_json = {}

    for mapping in sorted(data, key=lambda i: i['id']):
        # Only mappings within same uid
        if not mapping['uid'].startswith('{}/instances/'.format(uid)):
            continue
        if 'mappings' not in mapping_json:
            mapping_json['mappings'] = {}
        mapping_id = mapping['id']
        mapping_json['mappings'][mapping_id] = {}
        response = eventclass_router.callMethod('getInstanceData', uid=mapping['uid'])
        mapping_data = response['result']['data'][0]
        for k in fields:
            v = mapping_data[k]
            if v:
                mapping_json['mappings'][mapping_id][k] = v
        mapping_props = get_properties(routers, mapping['uid'])
        mapping_json['mappings'][mapping_id].update(mapping_props)
    return mapping_json


def list_eventclasses(routers, uid='/zport/dmd/Events'):
    eventclass_router = routers['EventClasses']
    eventclass_uids = []
    response = eventclass_router.callMethod('asyncGetTree', id=uid)
    result = response['result']
    for branch in sorted(result, key=lambda i: i['uid']):
        branch_uid = branch['uid']
        eventclass_uids.append(branch_uid)
        branch_children = sorted(branch.get('children', []))
        if not branch_children:
            response = eventclass_router.callMethod('asyncGetTree', id=branch_uid)
            branch_children = response['result']
        for child in sorted(branch_children, key=lambda i: i['uid']):
            eventclass_uids.append(child['uid'])
            children = list_eventclasses(routers, uid=child['uid'])
            eventclass_uids.extend(children)
    return eventclass_uids


def parse_eventclasses(routers, output):

    print('Retrieving all event classes')
    eventclasses_list = list_eventclasses(routers)
    print('Retrieved {} event classes'.format(len(eventclasses_list)))

    eventclass_data = {'event_classes': {}}
    ec_loop = tqdm(eventclasses_list, desc='Event Classes ', ascii=True)
    for uid in ec_loop:
        branch_path = uid[10:]
        ec_loop.set_description('Event Class ({})'.format(branch_path))
        ec_loop.refresh()

        eventclass_data['event_classes'][branch_path] = {}
        # Properties
        ec_props = get_properties(routers, uid)
        eventclass_data['event_classes'][branch_path].update(ec_props)
        # Transforms
        ec_transforms = get_transforms(routers, uid)
        eventclass_data['event_classes'][branch_path].update(ec_transforms)
        # Mappings
        ec_mappings = get_mappings(routers, uid)
        eventclass_data['event_classes'][branch_path].update(ec_mappings)
        try:
            yaml.safe_dump(eventclass_data, file(output, 'w'), encoding='utf-8', allow_unicode=True, sort_keys=True)
        except:
            pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='List event classes definition')
    parser.add_argument('-s', dest='environ', action='store', default='z6_test')
    parser.add_argument('-f', dest='output', action='store', default='eventclasses_output.yaml')
    options = parser.parse_args()
    environ = options.environ
    output = options.output

    print('Connecting to Zenoss')
    try:
        eventclass_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='EventClassesRouter')
        properties_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='PropertiesRouter')
    except Exception as e:
        print('Could not connect to Zenoss: {}'.format(e.args))
        exit(1)

    routers = {
        'EventClasses': eventclass_router,
        'Properties': properties_router,
    }

    parse_eventclasses(routers, output)
