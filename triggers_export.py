import zenAPI.zenApiLib
import argparse
from tools import yaml_print
import yaml
from tqdm import tqdm


def parse_triggerlist(routers, output):
    trigger_router = routers['Triggers']
    response = trigger_router.callMethod('getTriggers')
    # print(response)
    triggers = response['result']['data']
    # yaml_print(key='triggers', indent=0)

    triggers = sorted(triggers, key=lambda i: i['name'])

    triggers_json = {}
    for trigger in tqdm(triggers, desc='Triggers     ', ascii=True):
        if 'triggers' not in triggers_json:
            triggers_json['triggers'] = {}
        trigger_name = trigger['name']
        triggers_json['triggers'][trigger_name] = {}
        for k in ['enabled']:
            v = trigger.get(k, '')
            if v:
                triggers_json['triggers'][trigger_name][k] = v
        trigger_rule = trigger.get('rule', {})
        if trigger_rule:
            triggers_json['triggers'][trigger_name]['rule'] = {}
            triggers_json['triggers'][trigger_name]['rule']['source'] = trigger_rule['source']
            triggers_json['triggers'][trigger_name]['rule']['type'] = trigger_rule['type']
    yaml.safe_dump(triggers_json, file(output, 'w'), encoding='utf-8', allow_unicode=True, sort_keys=True)

def parse_notificationlist(routers, output):
    trigger_router = routers['Triggers']
    response = trigger_router.callMethod('getNotifications')
    notifications = response['result']['data']
    notifications = sorted(notifications, key=lambda i: i['name'])

    fields = ['action', 'enabled', 'send_clear', 'send_initial_occurrence', 'delay_seconds', 'repeat_seconds']
    content_fields = ['body_content_type', 'subject_format', 'action_timeout', 'body_format',
                      'clear_subject_format', 'clear_body_format', 'user_env_format'
                      'skipfails', 'email_from', 'host', 'port', 'useTls', 'user', 'password']

    notification_json = {}
    for notification in tqdm(notifications, desc='Notifications', ascii=True):
        if 'notifications' not in notification_json:
            notification_json['notifications'] = {}
        notification_name = notification['name']
        notification_json['notifications'][notification_name] = {}

        for k in fields:
            v = notification.get(k, '')
            if v:
                notification_json['notifications'][notification_name][k] = v
        notification_subs = notification.get('subscriptions', [])
        if notification_subs:
            trigger_list = [t['name'] for t in notification_subs]
            notification_json['notifications'][notification_name]['triggers'] = trigger_list
        notification_content = notification.get('content', {})
        if notification_content:
            items = notification_content['items'][0]['items']
            for k in content_fields:
                for item in items:
                    if item['name'] == k:
                        items.remove(item)
                        break
                else:
                    item = None
                if item:
                    value = item.get('value', None)
                    if value:
                        notification_json['notifications'][notification_name][item['name']] = value
        notification_recipients = notification.get('recipients', [])
        if notification_recipients:
            recipient_list = [r['label'] for r in notification_recipients]
            # yaml_print(key='recipients', value=recipient_list, indent=4)
            notification_json['notifications'][notification_name]['recipients'] = recipient_list
    yaml.safe_dump(notification_json, file(output, 'a'), encoding='utf-8', allow_unicode=True, sort_keys=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Manage Triggers')
    parser.add_argument('-s', dest='environ', action='store', default='z6_test')
    parser.add_argument('-f', dest='output', action='store', default='triggers_output.yaml')
    options = parser.parse_args()
    environ = options.environ
    output = options.output

    # Routers
    try:
        trigger_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='TriggersRouter')
        properties_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='PropertiesRouter')
    except Exception as e:
        print('Could not connect to Zenoss: {}'.format(e.args))
        exit(1)

    routers = {
        'Triggers': trigger_router,
        'Properties': properties_router,
    }

    print('Connecting to Zenoss')
    parse_triggerlist(routers, output)
    parse_notificationlist(routers, output)
    #TODO : Export Notification schedules
