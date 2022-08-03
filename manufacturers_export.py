import zenAPI.zenApiLib
import argparse
import yaml
import sys
from tqdm import tqdm


def get_manufacturerdata(routers, uid):
    manufacturer_router = routers['Manufacturers']
    response = manufacturer_router.callMethod('getManufacturerData', uid=uid)
    if not response['result']['success']:
        print('get_manufacturerdata - {} = {}'.format(uid, response))
    data = response['result']['data'][0]
    fields = ['phone', 'url', 'address1', 'address2', 'city', 'state', 'zip', 'country', 'regexes']
    data_json = {}
    for k in fields:
        v = data.get(k, '')
        if v:
            if k == 'url':
                data_json['URL'] = v
            else:
                data_json[k] = v
    return data_json


def get_manufacturerproducts(routers, uid):
    manufacturer_router = routers['Manufacturers']
    response = manufacturer_router.callMethod('getProductsByManufacturer', uid=uid)
    if not response['result']['success']:
        print('get_manufacturerproducts - Could not get products: {}'.format(response))
        return {}
    data = response['result']['data']
    data = sorted(data, key=lambda i: i['id'])
    products_json = {}
    for product in tqdm(data, desc='    Products', ascii=True):
        if 'products' not in products_json:
            products_json['products'] = {}
        product_id = product['id']
        products_json['products'][product_id] = {}
        products_json['products'][product_id]['type'] = product['type']
        product_data = get_productdata(routers, uid, product['id'])
        products_json['products'][product_id].update(product_data)
    return products_json


def get_productdata(routers, uid, name):
    manufacturer_router = routers['Manufacturers']
    response = manufacturer_router.callMethod('getProductData', uid=uid, prodname=name)
    if not response['result']['success']:
        print('get_productdata - Could not get product data: {}'.format(response))
        return {}
    data = response['result']['data'][0]
    fields = ['name', 'partno', 'prodKeys', 'desc', 'os', 'type']
    data_json = {}
    for k in fields:
        v = data.get(k, '')
        if v:
            if k == 'prodKeys':
                data_json['prodkeys'] = v
            elif k == 'desc':
                data_json['description'] = v
            else:
                data_json[k] = v
    # TODO: zProperties ?
    return data_json


def parse_manufacturerlist(routers, output):
    manufacturer_router = routers['Manufacturers']

    print('Retrieving all manufacturers')
    response = manufacturer_router.callMethod('getManufacturerList')
    data = response['result']['data']
    print('Retrieving {} manufacturers'.format(len(data)))

    manufacturers = sorted(data, key=lambda i: i['uid'])
    manufacturer_json = {}
    man_loop = tqdm(manufacturers, desc='Manufacturers', ascii=True, file=sys.stdout)
    for manufacturer in man_loop:
        man_loop.set_description('Manufacturer ({})'.format(manufacturer['path']))
        man_loop.refresh()

        if 'manufacturers' not in manufacturer_json:
            manufacturer_json['manufacturers'] = {}
        manufacturer_path = '/' + manufacturer['path']
        manufacturer_uid = manufacturer['uid']
        manufacturer_json['manufacturers'][manufacturer_path] = {}
        man_data = get_manufacturerdata(routers, manufacturer_uid)
        manufacturer_json['manufacturers'][manufacturer_path].update(man_data)
        man_products = get_manufacturerproducts(routers, manufacturer_uid)
        manufacturer_json['manufacturers'][manufacturer_path].update(man_products)
        yaml.safe_dump(manufacturer_json, file(output, 'w'), encoding='utf-8', allow_unicode=True, sort_keys=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Manage Manufacturers')
    parser.add_argument('-s', dest='environ', action='store', default='z6_test')
    parser.add_argument('-f', dest='output', action='store', default='manufacturers_output.yaml')
    options = parser.parse_args()
    environ = options.environ
    output = options.output

    # Routers
    try:
        manufacturer_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='ManufacturersRouter')
        properties_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='PropertiesRouter')
    except Exception as e:
        print('Could not connect to Zenoss: {}'.format(e.args))
        exit(1)

    routers = {
        'Manufacturers': manufacturer_router,
        'Properties': properties_router,
    }

    print('Connecting to Zenoss')
    parse_manufacturerlist(routers, output)
