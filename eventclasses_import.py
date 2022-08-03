import zenAPI.zenApiLib
import argparse
import yaml
import sys
from tqdm import tqdm


def import_properties(routers, uid, prop_data):
    properties_router = routers['Properties']
    response = properties_router.callMethod('getZenProperties', uid=uid)
    if not response['result']['success']:
        print(response)
        exit()
    current_props = response['result']['data']
    for k, v in prop_data.items():
        current_prop = [p for p in current_props if p['id'] == k][0]
        # print(current_prop)
        if not current_prop['islocal']:
            # print('Resetting {}'.format(k))
            if current_prop['type'] == 'int':
                reset = v + 1
            elif current_prop['type'] == 'lines':
                reset = ['reset_magic']
            elif current_prop['type'] == 'string':
                reset = 'reset_magic'
            else:
                print('Unknown type of zProp to reset')
                print(current_prop)
                exit()
            response = properties_router.callMethod('setZenProperty', uid=uid,
                                                    zProperty=k, value=reset)
            # print(response)
            if not response['result']['success']:
                print(response)
                exit()

        if v != current_prop['value'] or not current_prop['islocal']:
            # print('Changing {}'.format(k))
            response = properties_router.callMethod('setZenProperty', uid=uid,
                                                    zProperty=k, value=v)
            # print(response)
            if not response['result']['success']:
                print(response)
                exit()
    return


def import_transform(routers, uid, transform_data):
    eventclass_router = routers['EventClasses']
    response = eventclass_router.callMethod('getTransformTree', uid=uid)
    if not response['result']['success']:
        print(response)
        exit()
    data = response['result']['data']
    if len(data) > 1:
        data = [t for t in data if t['transid'] == uid[10:]][0]
        # print('More than one transform ? ')
        # print(data)
        # exit()
    else:
        # TODO: What if no transform ? Is it possible ?
        data = data[0]
    if data == [] or data['trans'] != transform_data:
        response = eventclass_router.callMethod('setTransform', uid=uid, transform=transform_data)
        if not response['result']['success']:
            print(response)
            exit()
    return


def import_mappings(routers, uid, mappings_data):
    eventclass_router = routers['EventClasses']
    response = eventclass_router.callMethod('getInstances', uid=uid)
    current_data = response['result']['data']
    # print(current_data)
    # print(mappings_data)
    # TODO: Is it evaluation or explanation ???
    mapping_fields = ['evaluation', 'eventClassKey', 'example', 'explanation', 'regex', 'rule', 'resolution',
                      'transform']

    mappings_loop = tqdm(mappings_data, desc='    Mappings', ascii=True, file=sys.stdout)
    for mapping in mappings_loop:
        mappings_loop.set_description('    Mapping ({})'.format(mapping))
        mappings_loop.refresh()
        current_mapping = [m for m in current_data if m['id'] == mapping]
        # print('*****')
        # print(current_mapping)
        # print('*****')
        if len(current_mapping) > 1:
            print('Too many mappings?')
            print(current_mapping)
            exit()
        elif len(current_mapping) == 1:
            current_mapping = current_mapping[0]
        mapping_data = mappings_data[mapping]
        if current_mapping:
            # print('Mapping is present')
            # print(current_mapping)
            mapping_uid = '{}/instances/{}'.format(uid, mapping)
            # print('***{}***'.format(mapping_data.get('rule', '')))
            # TODO: resequence if needed
            params = {'evclass': uid,
                      'uid':  mapping_uid,
                      'instanceName': mapping,
                      'newName': mapping,
                      }
            for k in mapping_fields:
                if k in mapping_data:
                    if mapping_data[k] != current_mapping.get(k, ''):
                        params[k] = mapping_data[k]
                    else:
                        params[k] = current_mapping[k]
                else:
                    if k in current_mapping:
                        params[k] = current_mapping[k]
                    else:
                        params[k] = ''
            print('params: {}'.format(params))
            response = eventclass_router.callMethod('editInstance', params=params)
            print('response: {}'.format(response))
            if not response['result']['success']:
                print(response)
                exit()


        else:
            # print('Mapping is absent')
            '''
            action: "EventClassesRouter"
            method: "addNewInstance"
            params: {evclass: "/zport/dmd/Events/TEST1234", instanceName: "", newName: "mapping_name", ...}
            evclass: "/zport/dmd/Events/TEST1234"
            instanceName: ""
            newName: "mapping_name"
            eventClassKey: "mapping_key"
            example: "mapping exmaple"
            explanation: "mapping_explanation"
            regex: ".*"
            rule: ""
            resolution: "mapping_resolution"
            '''
            # print(mapping_data)
            params = {'evclass': uid, 'instanceName': '', 'newName': mapping,
                      'eventClassKey': mapping_data.get('eventClassKey', ''),
                      'example': mapping_data.get('example', ''),
                      'explanation': mapping_data.get('explanation', ''),
                      'regex': mapping_data.get('regex', ''),
                      'rule': mapping_data.get('rule', ''),
                      'resolution': mapping_data.get('resolution', ''),
                     }
            response = eventclass_router.callMethod('addNewInstance', params=params)
            if not response['result']['success']:
                print(response)
                exit()

        if 'zProperties' in mapping_data:
            mapping_uid = '{}/instances/{}'.format(uid, mapping)
            import_properties(routers, mapping_uid, mapping_data['zProperties'])

        '''
        if 'sequence' in mapping_data:
            print(mapping_data)
            mapping_uid = '{}/instances/{}'.format(uid, mapping)
            print(mapping_uid)
            response = eventclass_router.callMethod('getSequence', uid=mapping_uid)
            print(response)
            exit()
        '''

    return


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


def create_eventclass(routers, uid):
    eventclass_router = routers['EventClasses']
    parent_uid = '/'.join(uid.split('/')[:-1])
    response = eventclass_router.callMethod('objectExists', uid=parent_uid)
    if not response['result']['success']:
        print(response)
        exit()
    if not response['result']['exists']:
        create_eventclass(routers, parent_uid)
    id = uid.split('/')[-1]
    response = eventclass_router.callMethod('addNode', type='organizer', contextUid=parent_uid, id=id)
    if not response['result']['success']:
        print(response)
        exit()
    return


def import_eventclass(routers, eventclass, data, current_ecs):
    eventclass_router = routers['EventClasses']
    ec_uid = '/zport/dmd{}'.format(eventclass)
    '''
    response = eventclass_router.callMethod('objectExists', uid=ec_uid)
    if not response['result']['success']:
        print(response)
        exit()
    if not response['result']['exists']:
        create_eventclass(routers, ec_uid)
    '''

    if ec_uid not in current_ecs:
        create_eventclass(routers, ec_uid)

    ec_data = data['event_classes'][eventclass]
    # Properties
    if 'zProperties' in ec_data:
        zprop_data = ec_data['zProperties']
        import_properties(routers, ec_uid, zprop_data)
    # Transform
    if 'transform' in ec_data:
        transform_data = ec_data['transform']
        import_transform(routers, ec_uid, transform_data)
    # Mappings
    if 'mappings' in ec_data:
        mappings_data = ec_data['mappings']
        import_mappings(routers, ec_uid, mappings_data)

    return



def parse_eventclasses(routers, output):

    print('Retrieving all event classes')
    eventclasses_list = list_eventclasses(routers)
    print('Found {} existing event classes'.format(len(eventclasses_list)))

    print('Loading input file')
    data = yaml.safe_load(file(finput, 'r'))         # dict
    print('Loaded input file')
    if 'event_classes' not in data:
        print('No event class found. Skipping.')
        return
    event_classes = sorted(data['event_classes'])
    print('Found {} event classes in input'.format(len(event_classes)))

    ec_loop = tqdm(event_classes, desc='Event Classes', ascii=True, file=sys.stdout)
    for eventclass in ec_loop:
        ec_loop.set_description('Event Class ({})'.format(eventclass))
        ec_loop.refresh()

        # ec_data = data['event_classes'][eventclass]
        # print(ec_data)

        import_eventclass(routers, eventclass, data, eventclasses_list)

        continue

        branch_path = uid[10:]
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

    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='List event classes definition')
    parser.add_argument('-s', dest='environ', action='store', default='z6_test')
    parser.add_argument('-f', dest='input', action='store', default='eventclasses_input.yaml')
    options = parser.parse_args()
    environ = options.environ
    finput = options.input

    print('Connecting to Zenoss')
    eventclass_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='EventClassesRouter')
    properties_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='PropertiesRouter')

    routers = {
        'EventClasses': eventclass_router,
        'Properties': properties_router,
    }

    parse_eventclasses(routers, finput)
