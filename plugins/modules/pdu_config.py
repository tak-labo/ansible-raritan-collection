DOCUMENTATION = r"""
---
module: pdu_config
short_description: Configure Raritan PDU settings
description:
  - Manages PDU-wide settings such as name, startup state, and cycle delay.
  - Idempotent: only applies changes when current settings differ.
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
    description: PDU name.
    type: str
  startup_state:
    description: Power state on PDU startup.
    type: str
    choices: [on, off, last_known]
  cycle_delay:
    description: Outlet power cycle delay in seconds.
    type: int
"""

import sys
import os

try:
    from ansible.module_utils.basic import AnsibleModule
    from ansible_collections.raritan.xerus.plugins.module_utils.raritan_client import get_agent, RaritanClientError
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../module_utils'))
    from raritan_client import get_agent, RaritanClientError

from raritan.rpc import pdumodel

PDU_TARGET = '/model/pdu/0'

STARTUP_STATE_MAP = {
    'on': 0,        # SS_ON
    'off': 1,       # SS_OFF
    'last_known': 2,  # SS_LAST_KNOWN_STATE
}


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

    pdu = pdumodel.Pdu(PDU_TARGET, agent)

    try:
        settings = pdu.getSettings()
    except Exception as e:
        module.fail_json(msg='Failed to get PDU settings: {}'.format(e))
        return

    changed = False

    if p.get('name') is not None and settings.name != p['name']:
        settings.name = p['name']
        changed = True

    if p.get('cycle_delay') is not None and settings.cycleDelay != p['cycle_delay']:
        settings.cycleDelay = p['cycle_delay']
        changed = True

    if p.get('startup_state') is not None:
        desired = STARTUP_STATE_MAP[p['startup_state']]
        if settings.startupState != desired:
            settings.startupState = desired
            changed = True

    if changed and not module.check_mode:
        try:
            pdu.setSettings(settings)
        except Exception as e:
            module.fail_json(msg='Failed to set PDU settings: {}'.format(e))
            return

    module.exit_json(changed=changed)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            host=dict(type='str', required=True),
            username=dict(type='str', required=True),
            password=dict(type='str', required=True, no_log=True),
            validate_certs=dict(type='bool', default=True),
            name=dict(type='str'),
            startup_state=dict(type='str', choices=['on', 'off', 'last_known']),
            cycle_delay=dict(type='int'),
        ),
        supports_check_mode=True,
    )
    run_module(module)


if __name__ == '__main__':
    main()
