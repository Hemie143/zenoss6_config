import zenAPI.zenApiLib
import argparse
import yaml
from tqdm import tqdm


def get_mibinfo(routers, uid):
    mib_fields = ['name', 'contact', 'language', 'description']
    info_json = {}
    mib_router = routers['Mib']
    response = mib_router.callMethod('getInfo', uid=uid)
    if not response['result']['success']:
        print('No info collector for uid: {}'.format(uid))
        return {}
    data = response['result']['data']
    for k in mib_fields:
        v = data.get(k, '')
        if v:
            info_json[k] = v
    return info_json


def get_miboids(routers, uid):
    mib_router = routers['Mib']
    response = mib_router.callMethod('getOidMappings', uid=uid)
    if not response['result']['success']:
        print('No OID found for uid: {}'.format(uid))
        return
    data = sorted(response['result']['data'], key=lambda i: i['name'])
    oid_fields = ['name', 'oid', 'access', 'nodetype', 'status', 'description']
    oids_json = {}
    for oid in data:
        if 'oids' not in oids_json:
            oids_json['oids'] = {}
        oid_id = oid['id']
        oids_json['oids'][oid_id] = {}
        for k in oid_fields:
            v = oid.get(k, '')
            if v:
                oids_json['oids'][oid_id][k] = v
    return oids_json


def get_mibtraps(routers, uid):
    mib_router = routers['Mib']
    response = mib_router.callMethod('getTraps', uid=uid)
    if not response['result']['success']:
        print('No trap found for uid: {}'.format(uid))
        return
    data = sorted(response['result']['data'], key=lambda i: i['name'])
    # traps_fields = ['name', 'oid', 'objects', 'nodetype', 'status', 'description']
    traps_fields = ['name', 'oid', 'nodetype', 'status', 'description']
    # TODO: Sort objects list
    traps_json = {}
    for oid in data:
        if 'traps' not in traps_json:
            traps_json['traps'] = {}
        oid_id = oid['id']
        traps_json['traps'][oid_id] = {}
        for k in traps_fields:
            v = oid.get(k, '')
            if v:
                traps_json['traps'][oid_id][k] = v
    return traps_json


def list_organizers(routers, branches=[]):
    mib_router = routers['Mib']
    organizers = []
    if not branches:
        mib_tree = mib_router.callMethod('getOrganizerTree', id='/zport/dmd/Mibs')
        result = mib_tree['result']
        branches = [i for i in result if not i['leaf']]

    for branch in sorted(branches, key=lambda i: i['uid']):
        branch_uid = branch['uid']
        organizers.append(branch_uid)
        branch_children = sorted(branch.get('children', []))
        branch_children = [i for i in branch_children if not i['leaf']]
        if branch_children:
            children = list_organizers(routers, branch_children)
            organizers.extend(children)
    return organizers


def parse_mibtree(routers, output):
    mib_router = routers['Mib']
    print('Retrieving Organizers')
    organizers = list_organizers(routers)
    print('Retrieved {} Organizers'.format(len(organizers)))

    mib_json = {'mibs_organizers': {}}
    for organizer in tqdm(organizers, desc='MIBs Organizers', ascii=True):
        response = mib_router.callMethod('getOrganizerTree', id=organizer)
        # print(response)
        if not response['result']:
            print('getOrganizerTree response: {}'.format(response))
            continue
        result = response['result'][0]
        org_path = '/{}'.format(result['path'])
        mib_json['mibs_organizers'][org_path] = {}
        children = result['children']
        mibs = sorted([i for i in children if i['leaf']], key=lambda i: i['path'])
        for mib in tqdm(mibs, desc='    MIBs', ascii=True):
            if 'mibs' not in mib_json['mibs_organizers'][org_path]:
                mib_json['mibs_organizers'][org_path]['mibs'] = {}
            mib_uid = mib['uid']
            mib_name = mib['text']
            mib_json['mibs_organizers'][org_path]['mibs'][mib_name] = {}
            mib_info = get_mibinfo(routers, mib_uid)
            mib_json['mibs_organizers'][org_path]['mibs'][mib_name].update(mib_info)
            mib_oids = get_miboids(routers, mib_uid)
            if mib_oids:
                mib_json['mibs_organizers'][org_path]['mibs'][mib_name].update(mib_oids)
            mib_traps = get_mibtraps(routers, mib_uid)
            if mib_traps:
                mib_json['mibs_organizers'][org_path]['mibs'][mib_name].update(mib_traps)

    yaml.safe_dump(mib_json, file(output, 'w'), encoding='utf-8', allow_unicode=True, sort_keys=True)
    return

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Manage Manufacturers')
    parser.add_argument('-s', dest='environ', action='store', default='z6_test')
    parser.add_argument('-f', dest='output', action='store', default='mibs_output.yaml')
    options = parser.parse_args()
    environ = options.environ
    output = options.output

    # TODO: argument to select enable/disable of objects in traps

    # Routers
    try:
        mib_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='MibRouter')
        properties_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='PropertiesRouter')
    except Exception as e:
        print('Could not connect to Zenoss: {}'.format(e.args))
        exit(1)

    routers = {
        'Mib': mib_router,
        'Properties': properties_router,
    }

    print('Connecting to Zenoss')
    parse_mibtree(routers, output)
