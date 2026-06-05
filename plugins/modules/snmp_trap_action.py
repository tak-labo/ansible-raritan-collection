DOCUMENTATION = r"""
---
module: snmp_trap_action
short_description: Manage a Raritan PDU SNMP trap event action
description:
  - Creates, updates, or deletes a SendSnmpTrap event action in the PDU event engine.
  - Identified by action name. Idempotent for present/absent states.
  - state=present creates the action if missing or updates it if arguments differ.
  - state=absent removes the action if it exists.
  - Supports up to 3 trap destinations.
version_added: "1.0.0"
author:
  - Takahiro Nagafuchi (@tak)
options:
  host:
    description: PDU hostname or IP address.
    required: true
    type: str
  username:
    description: Authentication username.
    required: true
    type: str
  password:
    description: Authentication password.
    required: true
    type: str
    no_log: true
  validate_certs:
    description: Validate TLS certificate.
    type: bool
    default: true
  name:
    description: Action name used as the idempotency key.
    required: true
    type: str
  notification_type:
    description: SNMP notification type.
    type: str
    choices: [v2Trap, v3Trap, v2Inform]
    default: v2Trap
  destinations:
    description:
      - List of SNMP trap destinations (up to 3).
      - Each entry must have host, and optionally port (default 162) and community.
    type: list
    elements: dict
    suboptions:
      host:
        description: Trap receiver hostname or IP address.
        type: str
        required: true
      port:
        description: UDP port.
        type: int
        default: 162
      community:
        description: SNMP community string.
        type: str
        default: ""
  state:
    description: Whether the action should exist.
    type: str
    choices: [present, absent]
    default: present
"""

EXAMPLES = r"""
- name: Add SNMP trap action
  tak_55.raritan_xerus.snmp_trap_action:
    host: 192.168.1.100
    username: admin
    password: secret
    validate_certs: false
    name: "SNMP trap to NMS"
    notification_type: v2Trap
    destinations:
      - host: 192.168.1.200
        port: 162
        community: public
    state: present

- name: Delete SNMP trap action
  tak_55.raritan_xerus.snmp_trap_action:
    host: 192.168.1.100
    username: admin
    password: secret
    validate_certs: false
    name: "SNMP trap to NMS"
    state: absent
"""

RETURN = r"""# """

import sys
import os

try:
    from ansible.module_utils.basic import AnsibleModule
    from ansible_collections.tak_55.raritan_xerus.plugins.module_utils.raritan_client import get_agent, RaritanClientError
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../module_utils'))
    from raritan_client import get_agent, RaritanClientError

from raritan.rpc import event

ENGINE_TARGET = '/event_engine'
ACTION_TYPE = 'SendSnmpTrap'
MAX_DESTINATIONS = 3


def _dest_to_str(dest):
    host = dest.get('host', '')
    port = dest.get('port', 162)
    community = dest.get('community', '')
    return '{}:{}:{}'.format(host, port, community)


def _build_arguments(p, kv_class):
    args = [kv_class(key='SnmpNotfType', value=p.get('notification_type', 'v2Trap'))]
    destinations = p.get('destinations') or []
    for i in range(MAX_DESTINATIONS):
        key = 'SnmpTrapDest{}'.format(i + 1)
        if i < len(destinations):
            value = _dest_to_str(destinations[i])
        else:
            value = ':162:'
        args.append(kv_class(key=key, value=value))
    return args


def _args_match(existing_action, desired_args):
    existing = {kv.key: kv.value for kv in existing_action.arguments}
    desired = {kv.key: kv.value for kv in desired_args}
    return all(existing.get(k) == v for k, v in desired.items())


def run_module(module):
    p = module.params

    try:
        agent = get_agent(
            host=p['host'],
            username=p['username'],
            password=p['password'],
            validate_certs=p.get('validate_certs', True),
        )
    except Exception as e:
        module.fail_json(msg=str(e))
        return

    engine = event.Engine(ENGINE_TARGET, agent)

    try:
        actions = engine.listActions()
    except Exception as e:
        module.fail_json(msg='Failed to list actions: {}'.format(e))
        return

    existing = next((a for a in actions if a.name == p['name']), None)
    state = p.get('state', 'present')

    if state == 'absent':
        if existing is None:
            module.exit_json(changed=False)
            return
        if not module.check_mode:
            try:
                engine.deleteAction(existing.id)
            except Exception as e:
                module.fail_json(msg='Failed to delete action: {}'.format(e))
                return
        module.exit_json(changed=True)
        return

    # state == 'present'
    desired_args = _build_arguments(p, event.KeyValue)

    if existing is None:
        if not module.check_mode:
            new_action = event.Engine.Action(
                id='',
                name=p['name'],
                isSystem=False,
                type=ACTION_TYPE,
                arguments=desired_args,
            )
            try:
                engine.addAction(new_action)
            except Exception as e:
                module.fail_json(msg='Failed to add action: {}'.format(e))
                return
        module.exit_json(changed=True)
        return

    if _args_match(existing, desired_args):
        module.exit_json(changed=False)
        return

    updated = event.Engine.Action(
        id=existing.id,
        name=existing.name,
        isSystem=existing.isSystem,
        type=existing.type,
        arguments=desired_args,
    )
    if not module.check_mode:
        try:
            engine.modifyAction(updated)
        except Exception as e:
            module.fail_json(msg='Failed to modify action: {}'.format(e))
            return
    module.exit_json(changed=True)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            host=dict(type='str', required=True),
            username=dict(type='str', required=True),
            password=dict(type='str', required=True, no_log=True),
            validate_certs=dict(type='bool', default=True),
            name=dict(type='str', required=True),
            notification_type=dict(type='str', choices=['v2Trap', 'v3Trap', 'v2Inform'], default='v2Trap'),
            destinations=dict(type='list', elements='dict', options=dict(
                host=dict(type='str', required=True),
                port=dict(type='int', default=162),
                community=dict(type='str', default=''),
            )),
            state=dict(type='str', choices=['present', 'absent'], default='present'),
        ),
        supports_check_mode=True,
    )
    run_module(module)


if __name__ == '__main__':
    main()
