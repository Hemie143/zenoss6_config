

def yaml_print(key='', value='', indent=0):
    head = indent*' '
    debug_stop = False
    if key:
        key = '{}: '.format(key)
    if isinstance(value, list):
        if len(value) == 0:
            print('{}{}: []'.format(head, key))
        else:
            print('{}{}'.format(head, key))
            for i in value:
                print(u'{}  - {}'.format(head, i))
                # print('{}  - {}'.format(head, str(i).decode('ascii').encode('utf-8')))
        return
    elif isinstance(value, int):
        value = str(value).decode('utf-8')
    elif isinstance(value, float):
        value = str(value).decode('utf-8')
    elif isinstance(value, str):
        value = value.decode('utf-8')
    elif isinstance(value, unicode):
        pass
    else:
        print('value is of type: {}'.format(type(value)))
        print(key)
        print(value)
        exit()
    # value = value.decode('utf-8')

    multiline = len(value.splitlines()) > 1
    if multiline:
        print('{}{}|+'.format(head, key))
        for l in value.splitlines():
            print('  {}{}'.format(head, l.encode('utf-8')))
    else:
        if value.startswith('{') and value.endswith('}'):
            print('{}{}{}'.format(head, key, value.encode('utf-8')))
        elif value.startswith('[') and value.endswith(']'):
            print('{}{}{}'.format(head, key, value.encode('utf-8')))
        elif ':' in value or '%' in value or '#' in value:
            print('{}{}{!r}'.format(head, key, value.encode('utf-8')))
        elif value.startswith("'") or value.startswith("["):
            print('{}{}{!r}'.format(head, key, value.encode('utf-8')))
        else:
            print('{}{}{}'.format(head, key, value.encode('utf-8')))

def get_properties(routers, uid, indent):
    properties_router = routers['Properties']
    response = properties_router.callMethod('getZenProperties', uid=uid)
    properties = response['result']['data']
    properties = sorted(properties, key=lambda i: i['id'])
    header = False
    for property in properties:
        if property['islocal'] == 1:
            if not header:
                yaml_print(key='zProperties', indent=indent)
                header = True
            yaml_print(key=property['id'], value=property['value'], indent=indent+2)
    return