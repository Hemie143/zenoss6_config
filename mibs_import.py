# coding: utf-8
import zenAPI.zenApiLib
import argparse
import yaml
import sys
from tqdm import tqdm

# TODO: handle UTF-8 characters in YAML ?
#       LNSUSvc:
#         description: 'Service de mise à niveau intelligente IBM Notes       '
#         monitoredStartModes:
#         - Auto
#         serviceKeys: LNSUSvc


def import_organizer(routers, organizer, data):
    properties_router = routers['Properties']
    mib_router = routers['Mib']
    uid = '/zport/dmd{}'.format(organizer)
    response = mib_router.callMethod('getInfo', uid=uid)
    if not response['result']['success']:
        id = organizer.split('/')[-1]
        contextUid = '/zport/dmd{}'.format('/'.join(organizer.split('/')[:-1]))
        response = mib_router.callMethod('addNode', type='organizer', contextUid=contextUid, id=id)
        if not response['result']['success']:
            print(response)
            exit()
    return


def import_mib_settings(routers, mib_uid, mib_data, current_data):
    mib_router = routers['Mib']
    for k, new_value in mib_data.items():
        if k not in ['name', 'language', 'description', 'contact']:
            continue
        if k in current_data and current_data[k] != new_value:
            info_data = {'uid': mib_uid, k: new_value}
            response = mib_router.callMethod('setInfo', **info_data)
            if not response['result']['success']:
                print(response)
                exit()


def import_mib_oids(routers, mib_uid, oids_data):
    mib_router = routers['Mib']
    current_oids = []
    for response in mib_router.pagingMethodCall('getOidMappings', uid=mib_uid):
        current_oids.extend(response['result']['data'])

    # print('current_oids: {}'.format(len(current_oids)))
    # oids_loop = tqdm(oids_data, desc='OIDs', ascii=True, file=sys.stdout)
    for id, oid_data in oids_data.items():
        # print('id: {}'.format(id))
        for current in current_oids:
            if current['name'] == id:
                break
        else:
            current = None
        # print('current: {}'.format(current))
        if not current:
            response = mib_router.callMethod('addOidMapping', uid=mib_uid, id=id, oid=oid_data['oid'],
                                             nodetype=oid_data['nodetype'])
            if not response['result']['success']:
                print(response)
                exit()
            current = dict(access='', description='', status='')
        fields = ['access', 'description', 'status', 'objects']
        for k in fields:
            if k not in oid_data:
                continue
            if oid_data[k] != current[k]:
                oid_uid = '{}/nodes/{}'.format(mib_uid, id)
                info_data = {'uid': oid_uid, k: oid_data[k]}
                response = mib_router.callMethod('setInfo', **info_data)
                if not response['result']['success']:
                    print(response)
                    exit()
    return


def import_mib_traps(routers, mib_uid, traps_data):
    mib_router = routers['Mib']
    current_traps = []
    for response in mib_router.pagingMethodCall('getTraps', uid=mib_uid):
        current_traps.extend(response['result']['data'])

    # oids_loop = tqdm(oids_data, desc='OIDs', ascii=True, file=sys.stdout)
    for id, trap_data in traps_data.items():
        # current = None
        for current in current_traps:
            if current['name'] == id:
                break
        else:
            current = None
        if not current:
            response = mib_router.callMethod('addTrap', uid=mib_uid, id=id, oid=trap_data['oid'],
                                             nodetype=trap_data['nodetype'])
            if not response['result']['success']:
                print(response)
                exit()
            current = dict(access='', description='', status='')
        fields = ['description', 'objects', 'status']
        # fields = ['description', 'status']
        for k in fields:
            if k not in trap_data:
                continue
            if trap_data[k] != current[k]:

                print('ID: {} - Attribute: {}'.format(id, k))
                print('Current: {}'.format(current[k]))
                print('Data   : {}'.format(trap_data[k]))

                if k == 'objects':
                    # trap_data[k] = 'test'
                    # trap_data[k] = [unicode(x) for x in trap_data[k]]

                    response = mib_router.callMethod('addTrap', uid=mib_uid, id='librarySerialNumber',
                                                     oid=trap_data['oid'],
                                                     nodetype='object')

                    print(response)
                    exit()

                    trap_data[k] = {
                                    "librarySerialNumber" : {
                                            "nodetype" : "object",
                                            "module" : "ADIC-TAPE-LIBRARY-MIB"
                                        },
                                        "coolingStatus" : {
                                            "nodetype" : "object",
                                            "module" : "ADIC-TAPE-LIBRARY-MIB"
                                        }
                    }


                    print('Data   : {}'.format(trap_data[k]))


                trap_uid = '{}/notifications/{}'.format(mib_uid, id)
                info_data = {'uid': trap_uid, k: trap_data[k]}

                print(info_data)

                response = mib_router.callMethod('setInfo', **info_data)
                if not response['result']['success']:
                    print(response)
                    exit()
                print(response)
                exit()
    return


def import_mib(routers, organizer, mib, data):
    mib_router = routers['Mib']
    mib_data = data['mibs_organizers'][organizer]['mibs'][mib]
    organizer_uid = '/zport/dmd{}'.format(organizer)
    mib_uid = '{}/mibs/{}'.format(organizer_uid, mib)
    response = mib_router.callMethod('getInfo', uid=mib_uid)
    if not response['result']['success']:
        response = mib_router.callMethod('addNode', type='MIB', contextUid=organizer_uid, id=mib)
        if not response['result']['success']:
            print(response)
            exit()
        response = mib_router.callMethod('getInfo', uid=mib_uid)
    current_data = response['result']['data']

    import_mib_settings(routers, mib_uid, mib_data, current_data)
    if 'oids' in mib_data:
        import_mib_oids(routers, mib_uid, mib_data['oids'])
    if 'traps' in mib_data:
        import_mib_traps(routers, mib_uid, mib_data['traps'])

    return


def parse_mibstree(routers, finput):
    print('Loading input file')
    data = yaml.safe_load(file(finput, 'r'))         # dict
    print('Loaded input file')
    if 'mibs_organizers' not in data:
        print('No MIB organizer found. Skipping.')
        return
    mibs_organizers = sorted(data['mibs_organizers'])
    mibs_count = 0
    for mibs_organizer in mibs_organizers:
        org_data = data['mibs_organizers'][mibs_organizer]
        if 'mibs' in org_data:
            mibs_count += len(org_data['mibs'])
    print('Found {} MIB organizers in input'.format(len(mibs_organizers)))
    print('Found {} MIBs in input'.format(mibs_count))

    organizers_loop = tqdm(mibs_organizers, desc='Organizers', ascii=True, file=sys.stdout)
    for organizer in organizers_loop:
        desc = 'Organizer ({})'.format(organizer)
        organizers_loop.set_description(desc)
        organizers_loop.refresh()
        import_organizer(routers, organizer, data)
        if not 'mibs' in data['mibs_organizers'][organizer]:
            continue
        mibs = sorted(data['mibs_organizers'][organizer]['mibs'])
        mibs_loop = tqdm(mibs, desc='MIBs', ascii=True, file=sys.stdout)
        for mib in mibs_loop:
            mibs_loop.set_description('    MIB ({})'.format(mib))
            mibs_loop.refresh()
            import_mib(routers, organizer, mib, data)
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='List services definition')
    parser.add_argument('-s', dest='environ', action='store', default='z6_test')
    parser.add_argument('-f', dest='input', action='store', default='mibs_input.yaml')
    options = parser.parse_args()
    environ = options.environ
    finput = options.input

    # Routers
    mib_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='MibRouter')
    properties_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='PropertiesRouter')

    routers = {
        'Mib': mib_router,
        'Properties': properties_router,
    }

    print('Connecting to Zenoss')
    parse_mibstree(routers, finput)
