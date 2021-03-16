import zenAPI.zenApiLib
import argparse
from tools import yaml_print


def parse_triggerlist(routers, list):
    list = sorted(list, key=lambda i: i['name'])
    for trigger in list:
        yaml_print(key=trigger['name'], indent=2)
        fields = ['enabled']
        for k in fields:
            v = trigger.get(k, '')
            if v:
                yaml_print(key=k, value=v, indent=4)
        trigger_rule = trigger.get('rule', {})
        if trigger_rule:
            yaml_print(key='rule', indent=4)
            yaml_print(key='source', value=trigger_rule['source'], indent=6)
            yaml_print(key='type', value=trigger_rule['type'], indent=6)


def parse_reporttree(routers, tree):
    tree = sorted(tree, key=lambda i: i['uid'])
    report_router = routers['Reports']

    # print('********: {}'.format(len(tree)))

    header = False

    for branch in tree:

        # print(branch)

        branch_path = branch['path']
        branch_leaf = branch['leaf']
        branch_uid = branch['uid']


        if branch_leaf:
            if not header:
                yaml_print(key='reports', indent=4)
                header = True
            yaml_print(key=branch['text'], indent=6)
            yaml_print(key='label', value=branch['text'], indent=8)
            edit = branch.get('edit_url', None)
            if edit:
                yaml_print(key=edit, value=edit, indent=8)
        else:
            yaml_print(key=branch_path, indent=2)
            yaml_print(key='label', value=branch['text']['text'], indent=4)

        '''
        {u'menuText': [u'Custom Device Report', u'Graph Report', u'Multi-Graph Report'], 
        u'reportTypes': [u'customDeviceReport', u'graphReport', u'multiGraphReport'], u'success': True}
        '''

        # Properties
        #get_properties(routers, branch_uid, 4)
        # Transforms
        # if branch['text']['hasTransform']:
        #    get_transforms(routers, branch_uid)
        # Mappings
        # get_mappings(routers, branch_uid)

        children = branch.get('children', [])
        if not branch_leaf and not children:
            response = report_router.callMethod('asyncGetTree', id=branch_uid)
            children = response['result']
        parse_reporttree(routers, children)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Manage Reports')
    parser.add_argument('-s', dest='environ', action='store', default='z6_test')
    options = parser.parse_args()
    environ = options.environ

    # Routers
    report_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='ReportRouter')
    properties_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='PropertiesRouter')

    routers = {
        'Reports': report_router,
        'Properties': properties_router,
    }

    response = report_router.callMethod('asyncGetTree', id='/zport/dmd/Reports')
    root_tree = response['result']
    yaml_print(key='reports_organizers', indent=0)
    parse_reporttree(routers, root_tree)

    response = report_router.callMethod('getReportTypes')
    root_tree = response['result']
    print(root_tree)

