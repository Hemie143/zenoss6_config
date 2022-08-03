import zenAPI.zenApiLib

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

def get_mibtraps(routers, uid):
    mib_router = routers['Mib']
    response = mib_router.callMethod('getTraps', uid=uid)
    if not response['result']['success']:
        return
    data = sorted(response['result']['data'], key=lambda i: i['name'])
    traps_fields = ['name', 'oid', 'objects', 'nodetype', 'status', 'description']
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




environ = 'z6_test'
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

# organizers = list_organizers(routers)
# print(organizers)

mib_uid = u'/zport/dmd/Mibs/mibs/ADIC-TAPE-LIBRARY-MIB'
mib_name = u'ADIC-TAPE-LIBRARY-MIB',

mib_traps = get_mibtraps(routers, mib_uid)

my_trap = mib_traps['traps']['controlStatusChange']
print(my_trap)

n_uid = '/zport/dmd/Mibs/mibs/ADIC-TAPE-LIBRARY-MIB/notifications/controlStatusChange'
# response = mib_router.callMethod('getInfo', uid=n_uid)
# print(response)

data = {
    'uid': n_uid,
    'description': 'XXNotify when control health status changed.',
    'objects': ["object1"],
    }
print('-' * 40)
response = mib_router.callMethod('setInfo',**data)
print(response)


