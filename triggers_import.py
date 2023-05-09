# coding=utf-8
import zenAPI.zenApiLib
import argparse
import re
import sys
import yaml
from tqdm import tqdm


def get_trigger(routers, trigger_name):
    trigger_router = routers['Triggers']
    response = trigger_router.callMethod('getTriggers')
    result = response['result']
    data = result['data']
    for trigger_data in data:
        if trigger_data.get('name', '') == trigger_name:
            break
    else:
        trigger_data = {}
    return trigger_data


def get_notification(routers, notification_name):
    trigger_router = routers['Triggers']
    response = trigger_router.callMethod('getNotifications')
    result = response['result']
    print(result)
    return


def import_trigger(routers, data):
    trigger_router = routers['Triggers']
    trigger, new_data = data.items()[0]
    trigger_data = get_trigger(routers, trigger)
    if not trigger_data:
        # Process is absent
        response = trigger_router.callMethod('addTrigger', newId=trigger)
        if not response['result']['success']:
            tqdm.write('Failed to create {}'.format(trigger))
            print(response)
            exit()
        trigger_data = get_trigger(routers, trigger)

    if trigger_data['enabled'] != new_data.get('enabled', False):
        data = {'uuid': trigger_data['uuid'], 'name': trigger_data['name'], 'enabled': new_data.get('enabled', False),
                'rule': trigger_data['rule']}
        response = trigger_router.callMethod('updateTrigger', **data)
        result = response['result']
    for k, v in new_data.get('rule', {}).items():
        if trigger_data['rule'][k] != v:
            new_rule = trigger_data['rule']
            new_rule[k] = v
            data = {'uuid': trigger_data['uuid'], 'name': trigger_data['name'], 'rule': new_rule}
            response = trigger_router.callMethod('updateTrigger', **data)
            result = response['result']
    return


def compact_data(data):
    fields = ['action', 'action_timeout', 'uid', 'enabled', 'send_clear', 'send_initial_occurrence', 'delay_seconds',
              'repeat_seconds', 'recipients', 'subscriptions']
    xfields = ['body_content_type', 'subject_format', 'body_format', 'clear_subject_format', 'clear_body_format',
               'skipfails', 'email_from', 'host', 'port', 'useTls', 'user', 'password']

    output = {k: data[k] for k in fields if data.get(k, '') != ''}

    output['subscriptions'] = [t['uuid'] for t in data['subscriptions']]
    content_items = data['content']['items'][0]['items']
    for k in xfields:
        for item in content_items:
            if item['name'] == k:
                content_items.remove(item)
                break
        else:
            item = {'value': None}
        output[k] = item['value']
    return output


def import_notification(routers, data, current_notifications):
    trigger_router = routers['Triggers']
    notification, new_data = data.items()[0]
    notification_uid = '/zport/dmd/NotificationSubscriptions/{}'.format(notification)
    current_data = [n for n in current_notifications if n['uid'] == notification_uid]
    if current_data:
        current_data = current_data[0]
    else:
        response = trigger_router.callMethod('addNotification', newId=notification,
                                             action=new_data.get('action', 'email'))
        if not response['result']['success']:
            tqdm.write('Failed to create {}'.format(uid))
            exit()
        response = trigger_router.callMethod('getNotification', uid=notification_uid)
        result = response['result']
        current_data = result['data']

    # Fields
    fields = ['action', 'action_timeout', 'enabled', 'send_clear', 'send_initial_occurrence', 'delay_seconds',
              'repeat_seconds', 'body_content_type', 'subject_format', 'body_format', 'clear_subject_format',
              'clear_body_format', 'skipfails', 'email_from', 'host', 'port', 'useTls', 'user', 'password'
              ]
    current_c_data = compact_data(current_data)
    data_changed = False
    for k in fields:
        if k in new_data and new_data[k] != current_c_data.get(k, ''):
            current_c_data[k] = new_data[k]
            data_changed = True

    # Recipients
    if 'recipients' in new_data:
        response = trigger_router.callMethod('getRecipientOptions')
        result = response['result']
        recipient_options = result['data']

        recipients = new_data['recipients']
        current_recipients_label = [r['label'] for r in current_c_data['recipients']]
        for recipient in recipients:
            for r_value in recipient_options:
                if r_value['label'] == recipient:
                    recipient_options.remove(r_value)
                    break
            else:
                recipient = recipient.lower()
                r = re.match(r'^[a-z0-9\-]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$', recipient)
                if r:
                    r_value = {
                        "type": "manual",
                        "label": recipient,
                        "value": recipient,
                        "write": False,
                        "manage": False
                    }
                else:
                    r_value = None
            if r_value and r_value['label'] not in current_recipients_label:
                # TODO : preserver the order as in data read from yaml. The value could be insert instead of being appended
                current_c_data['recipients'].append(r_value)
                data_changed = True

    # Triggers / subscriptions
    if 'triggers' in new_data:
        response = trigger_router.callMethod('getTriggerList')
        result = response['result']
        trigger_list = result['data']
        triggers = new_data['triggers']
        for trigger in triggers:
            for t_value in trigger_list:
                if t_value['name'] == trigger:
                    trigger_list.remove(t_value)
                    break
            else:
                t_value = None
            if t_value and t_value['uuid'] not in current_c_data['subscriptions']:
                current_c_data['subscriptions'].append(t_value['uuid'])
                data_changed = True
    if data_changed:
        response = trigger_router.callMethod('updateNotification', **current_c_data)
        print(response)
    return

def parse_triggerlist(routers, input):
    print('Loading input file')
    data = yaml.safe_load(file(input, 'r'))         # dict
    print('Loaded input file')
    if 'triggers' not in data:
        print('No trigger found. Skipping.')
        return
    triggers = sorted(data['triggers'])
    print('Found {} triggers'.format(len(triggers)))

    trigger_loop = tqdm(triggers, desc='Trigger', ascii=True, file=sys.stdout)
    for trigger in trigger_loop:
        desc = 'Trigger ({})'.format(trigger)
        trigger_loop.set_description(desc)
        trigger_loop.refresh()
        trigger_data = {trigger: data['triggers'][trigger]}
        import_trigger(routers, trigger_data)
    return


def parse_notificationlist(routers, input):
    trigger_router = routers['Triggers']
    print('Loading input file')
    data = yaml.safe_load(file(input, 'r'))         # dict
    print('Loaded input file')
    if 'notifications' not in data:
        print('No notification found. Skipping.')
        return
    notifications = sorted(data['notifications'])
    print('Found {} notifications'.format(len(notifications)))

    # Load notifications data. getNotification method doesn't load the "subscriptions" field.
    print('Loading current notifications')
    response = trigger_router.callMethod('getNotifications')
    current_notifications = response['result']['data']
    print('Loaded current notifications')

    notification_loop = tqdm(notifications, desc='Notification', ascii=True, file=sys.stdout)
    for notification in notification_loop:
        desc = 'Notification ({})'.format(notification)
        notification_loop.set_description(desc)
        notification_loop.refresh()
        notification_data = {notification: data['notifications'][notification]}
        import_notification(routers, notification_data, current_notifications)
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Manage Triggers')
    parser.add_argument('-s', dest='environ', action='store', default='z6_test')
    parser.add_argument('-f', dest='output', action='store', default='triggers_input.yaml')
    options = parser.parse_args()
    environ = options.environ
    input = options.output

    # Routers
    trigger_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='TriggersRouter')
    properties_router = zenAPI.zenApiLib.zenConnector(section=environ, routerName='PropertiesRouter')

    routers = {
        'Triggers': trigger_router,
        'Properties': properties_router,
    }

    print('Connecting to Zenoss')
    parse_triggerlist(routers, input)
    parse_notificationlist(routers, input)
    # TODO : Import Notification schedules