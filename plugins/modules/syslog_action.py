DOCUMENTATION = r"""
---
module: syslog_action
short_description: Manage a Raritan PDU syslog event action
description:
  - Creates, updates, or deletes a syslog event action in the PDU event engine.
  - Identified by action name. Idempotent for present/absent states.
  - state=present creates the action if missing or updates it if arguments differ.
  - state=absent removes the action if it exists.
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
  server:
    description: Syslog server hostname or IP address.
    type: str
  port:
    description: Syslog server UDP port.
    type: int
    default: 514
  message_format:
    description: Syslog message format string.
    type: str
  state:
    description: Whether the action should exist.
    type: str
    choices: [present, absent]
    default: present
"""

import sys
import os

try:
    from ansible.module_utils.basic import AnsibleModule
    from ansible_collections.raritan.xerus.plugins.module_utils.raritan_client import get_agent, RaritanClientError
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../module_utils'))
    from raritan_client import get_agent, RaritanClientError

from raritan.rpc import event

ENGINE_TARGET = '/engine'
ACTION_TYPE = 'syslog'

# Argument key names passed to the PDU — verify via engine.listActionTypes() on a real device.
# If keys differ, update this mapping (syslog_action.py is the only place to change).
SYSLOG_ARG_KEYS = {
    'server':         'serverName',
    'port':           'serverPort',
    'message_format': 'messageFormat',
}


def _build_arguments(p, kv_class):
    args = []
    for param_key, arg_key in SYSLOG_ARG_KEYS.items():
        val = p.get(param_key)
        if val is not None:
            args.append(kv_class(key=arg_key, value=str(val)))
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
            server=dict(type='str'),
            port=dict(type='int', default=514),
            message_format=dict(type='str'),
            state=dict(type='str', choices=['present', 'absent'], default='present'),
        ),
        supports_check_mode=True,
    )
    run_module(module)


if __name__ == '__main__':
    main()
