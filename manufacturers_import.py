import zenAPI.zenApiLib
import argparse
import yaml
import sys
from tqdm import tqdm


def import_manufacturer(routers, manufacturer, m_data, current_manufs):
    manufacturer_router = routers['Manufacturers']
    m_uid = '/zport/dmd{}'.format(manufacturer)
    m_id = manufacturer[15:]
    current_manuf = [m for m in current_manufs if m['uid'] == m_uid]
    # Create manufacturer ?
    if not current_manuf:
        response = manufacturer_router.callMethod('addManufacturer', id=m_id)
        if not response['result']['success']:
            print(response)
            exit()
    # Compare data
    response = manufacturer_router.callMethod('getManufacturerData', uid=m_uid)
    if not response['result']['success']:
        print(response)
        exit()
    current_data = response['result']['data'][0]
    edit_manuf = False
    for k, v in m_data.items():
        if k in ['products']:
            continue
        if k == 'URL':
            current_value = current_data.get('url', '')
        else:
            current_value = current_data.get(k, '')
        if v != current_value:
            edit_manuf = True
            break

    # Edit manufacturer only if there's a difference
    if edit_manuf:
        fields = ['phone', 'URL', 'address1', 'address2', 'city', 'state', 'zip', 'country', 'regexes']
        params = {'name': m_id}
        for f in fields:
            value = m_data.get(f, current_data.get(f, ''))
            params[f] = value
        response = manufacturer_router.callMethod('editManufacturer', params=params)
        if not response['result']['success']:
            print(response)
            exit()
    return


def import_product(routers, manufacturer, prod_data, current_products):
    manufacturer_router = routers['Manufacturers']
    m_uid = '/zport/dmd{}'.format(manufacturer)
    product = prod_data.keys()[0]
    current_prod = [p for p in current_products if p['id'] == product]

    fields = ['partno', 'prodkeys', 'os', 'type', 'description']
    params = {'uid': m_uid, 'prodname': product, 'oldname': ''}
    if not current_prod:
        for f in fields:
            fvalue = prod_data.values()[0].get(f, '')
            if f == 'prodkeys':
                fvalue = ', '.join(fvalue)
            params[f] = fvalue
        response = manufacturer_router.callMethod('addNewProduct', params=params)
        if not response['result']['success']:
            print(response)
            exit()
    else:
        # current_prod = current_prod[0]
        product_uid = '{}/products/{}'.format(m_uid, product)
        response = manufacturer_router.callMethod('getProductData', uid=product_uid, prodname=product)
        if not response['result']['success']:
            print(response)
            exit()
        current_data = response['result']['data'][0]
        edit_product = False

        for f in fields:
            if f == 'prodkeys':
                current_value = ', '.join(sorted(current_data['prodKeys']))
            elif f == 'description':
                current_value = current_data['desc']
            else:
                current_value = current_data[f]
            new_value = prod_data.values()[0].get(f, '')
            if f == 'prodkeys':
                new_value = ', '.join(new_value)
            if new_value != current_value:
                edit_product = True
            params[f] = new_value

        if edit_product:
            params['oldname'] = product
            response = manufacturer_router.callMethod('editProduct', params=params)
            if not response['result']['success']:
                print(response)
                exit()
    return


def get_manufacturerproducts(routers, uid):
    manufacturer_router = routers['Manufacturers']
    response = manufacturer_router.callMethod('getProductsByManufacturer', uid=uid)
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
    data = response['result']['data'][0]
    fields = ['name', 'partno', 'prodKeys', 'desc', 'os']
    data_json = {}
    for k in fields:
        v = data.get(k, '')
        if v:
            data_json[k] = v
    return data_json


def parse_manufacturerlist(routers, filename):
    manufacturer_router = routers['Manufacturers']

    print('Retrieving all manufacturers')
    response = manufacturer_router.callMethod('getManufacturerList')
    current_manufs = response['result']['data']
    print('Found {} current manufacturers'.format(len(current_manufs)))

    print('Loading input file')
    data = yaml.safe_load(file(filename, 'r'))         # dict
    print('Loaded input file')
    if 'manufacturers' not in data:
        print('No manufacturer found. Skipping.')
        return
    manufacturers = sorted(data['manufacturers'])
    print('Found {} manufacturers in input'.format(len(manufacturers)))

    m_loop = tqdm(manufacturers, desc='Manufacturers', ascii=True, file=sys.stdout)
    for manufacturer in m_loop:
        m_loop.set_description('Manufacturer ({})'.format(manufacturer))
        m_loop.refresh()
        m_data = data['manufacturers'][manufacturer]
        # Data
        import_manufacturer(routers, manufacturer, m_data, current_manufs)
        # Products
        if 'products' in m_data:
            m_prods = sorted(m_data['products'])
            m_uid = '/zport/dmd{}'.format(manufacturer)
            response = manufacturer_router.callMethod('getProductsByManufacturer', uid=m_uid)
            if not response['result']['success']:
                print(response)
                exit()
            current_products = response['result']['data']
            # print(current_products)


            prod_loop = tqdm(m_prods, desc='Products', ascii=True, file=sys.stdout)
            for product in prod_loop:
                prod_loop.set_description('Product ({})'.format(product))
                prod_loop.refresh()
                prod_data = {product: m_data['products'][product]}
                import_product(routers, manufacturer, prod_data, current_products)

        '''
        manufacturer_path = '/' + manufacturer['path']
        manufacturer_uid = manufacturer['uid']
        manufacturer_json['manufacturers'][manufacturer_path] = {}
        man_data = get_manufacturerdata(routers, manufacturer_uid)
        manufacturer_json['manufacturers'][manufacturer_path].update(man_data)
        man_products = get_manufacturerproducts(routers, manufacturer_uid)
        manufacturer_json['manufacturers'][manufacturer_path].update(man_products)
        '''

    exit()



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Manage Manufacturers')
    parser.add_argument('-s', dest='environ', action='store', default='z6_test')
    parser.add_argument('-f', dest='input', action='store', default='manufacturers_input.yaml')
    options = parser.parse_args()
    environ = options.environ
    filename = options.input

    # Routers
    manufacturer_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='ManufacturersRouter')
    properties_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='PropertiesRouter')

    routers = {
        'Manufacturers': manufacturer_router,
        'Properties': properties_router,
    }

    print('Connecting to Zenoss')
    parse_manufacturerlist(routers, filename)
