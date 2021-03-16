import zenAPI.zenApiLib
import argparse
from tools import yaml_print


def parse_userlist(routers):
    users_router = routers['Users']
    # list = sorted(list, key=lambda i: i['id'])

    fields = ['email', 'pager', 'defaultPageSize', 'netMapStartObject']
    for entry in users_router.pagingMethodCall('getUsers'):
        user_list = entry['result']['data']
        print(len(user_list))
        for user in user_list:
            yaml_print(key=user['name'], indent=2)
            for k in fields:
                v = user.get(k, None)
                if v:
                    yaml_print(key=k, value=v, indent=4)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Manage Users')
    parser.add_argument('-s', dest='environ', action='store', default='z6_test')
    # parser.add_argument('-f', dest='filename', action='store', default='local_templates.xlsx')
    options = parser.parse_args()
    environ = options.environ
    # filename = options.filename

    # Routers
    users_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='UsersRouter')
    properties_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='PropertiesRouter')

    routers = {
        'Users': users_router,
        'Properties': properties_router,
    }

    response = users_router.callMethod('getUsers')
    data = response['result']['data']
    yaml_print(key='users')
    parse_userlist(routers)

