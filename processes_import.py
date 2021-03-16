import zenAPI.zenApiLib
import argparse
import yaml
import sys
from tqdm import tqdm


def set_properties(routers, uid, prop_data):
    properties_router = routers['Properties']
    response = properties_router.callMethod('getZenProperties', uid=uid)
    current_props = response['result']['data']
    for k, v in prop_data.items():
        current_value = None
        for current_prop in current_props:
            if current_prop['label'] == k:
                current_value = current_prop['value']
                break
        if current_value != v:
            response = properties_router.callMethod('setZenProperty', uid=uid ,zProperty=k, value=v)
            if not response['result']['success']:
                print('Failed to set zProperty: {}'.format(response))
                exit()


def add_organizer(routers, uid):
    id = uid.split('/')[-1]
    contextUid = '/'.join(uid.split('/')[:-1])
    # Check that parent exists
    response = process_router.callMethod('objectExists', uid=contextUid)
    if not response['result']['exists']:
        add_organizer(routers, contextUid)
    else:
        response = process_router.callMethod('addNode', type='organizer', contextUid=contextUid, id=id)
        if not response['result']['success']:
            tqdm.write('Failed to create {}'.format(uid))
            exit()
    return


def import_organizer(routers, data):
    process_router = routers['Process']
    organizer, new_data = data.items()[0]
    org_uid = '/zport/dmd{}'.format(organizer)
    response = process_router.callMethod('getInfo', uid=org_uid)
    result = response['result']
    if result['success']:
        # Organizer is present
        pass
    else:
        add_organizer(routers, org_uid)
        response = process_router.callMethod('getInfo', uid=org_uid)
        result = response['result']
    current_data = result['data']
    # Description
    if 'description' in new_data:
        new_desc = new_data['description']
        if new_desc != current_data['description']:
            # TODO: hard to check whether this really works
            response = process_router.callMethod('setInfo', uid=org_uid, description=new_desc)
    # Properties
    if 'zProperties' in new_data:
        set_properties(routers, org_uid, new_data['zProperties'])
    return


def import_process(routers, org_data, process):
    process_router = routers['Process']
    organizer, new_data = org_data.items()[0]
    fields = ['includeRegex', 'excludeRegex', 'replaceRegex', 'replacement']
    process_data = new_data['process_class'][process]

    organizer_uid = '/zport/dmd{}'.format(organizer)
    process_uid = '/zport/dmd{}/osProcessClasses/{}'.format(organizer, process)
    response = process_router.callMethod('getInfo', uid=process_uid)
    result = response['result']
    if result['success'] and result['data']['uid'] == process_uid:
        # Process is present
        pass
    else:
        # Process is absent
        response = process_router.callMethod('addNode', type='class', contextUid=organizer_uid, id=process)
        if not response['result']['success']:
            tqdm.write('Failed to create {}'.format(uid))
            exit()
        response = process_router.callMethod('getInfo', uid=process_uid)
        result = response['result']

    current_data = result['data']

    # Description
    if 'description' in process_data:
        new_desc = process_data['description']
        if new_desc != current_data['description']:
            # TODO: hard to check whether this really works
            response = process_router.callMethod('setInfo', uid=process_uid, description=new_desc)
    # zProperties
    if 'zProperties' in process_data:
        for k, v in process_data['zProperties'].items():
            current_value = current_data.get('k', {}).get('localvalue', '')
            if current_value != v:
                response = properties_router.callMethod('setZenProperty', uid=process_uid, zProperty=k, value=v)
                if not response['result']['success']:
                    print('Failed to set zProperty: {}'.format(response))
    # Fields
    for k in fields:
        if k in process_data:
            new_value = process_data[k]
            current_value = current_data[k]
            if current_value != new_value:
                data = {u'uid': process_uid, k: new_value}
                response = process_router.callMethod('setInfo', **data)
    return


def parse_processtree(routers, input):
    process_router = routers['Process']

    print('Loading input file')
    data = yaml.safe_load(file(input, 'r'))         # dict
    print('Loaded input file')
    if 'process_class_organizers' not in data:
        print('Organizers not found. Exiting.')
    organizers = sorted(data['process_class_organizers'])
    print('Found {} organizers'.format(len(organizers)))

    org_loop = tqdm(organizers, desc='Organizer', ascii=True, file=sys.stdout)
    for organizer in org_loop:
        desc = 'Organizer ({})'.format(organizer)
        org_loop.set_description(desc)
        org_loop.refresh()
        organizer_data = {organizer: data['process_class_organizers'][organizer]}
        import_organizer(routers, organizer_data)
        # print(organizer_data)
        if 'process_class' in data['process_class_organizers'][organizer]:
            process_class = sorted(data['process_class_organizers'][organizer]['process_class'])
            proc_loop = tqdm(process_class, desc='    Process', ascii=True, file=sys.stdout)
            for process in proc_loop:
                desc = '    Process ({})'.format(process)
                proc_loop.set_description(desc)
                proc_loop.refresh()
                # proc_data = {process: data['process_class_organizers'][organizer]['process_class'][process]}
                import_process(routers, organizer_data, process)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='List processes definition')
    parser.add_argument('-s', dest='environ', action='store', default='z6_test')
    parser.add_argument('-f', dest='input', action='store', default='processes_input.yaml')
    options = parser.parse_args()
    environ = options.environ
    input = options.input

    process_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='ProcessRouter')
    properties_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='PropertiesRouter')

    routers = {
        'Process': process_router,
        'Properties': properties_router,
    }

    print('Connecting to Zenoss')
    parse_processtree(routers, input)
