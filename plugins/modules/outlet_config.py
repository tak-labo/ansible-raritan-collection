DOCUMENTATION = r"""
---
module: outlet_config
short_description: Configure a Raritan PDU outlet and control its power state
description:
  - Manages individual outlet settings (name, startup state, cycle delay).
  - Controls outlet power state (on/off/cycle).
  - Settings management is idempotent. state=cycle always triggers a power cycle.
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
  outlet:
    description: Outlet number (1-based).
    required: true
    type: int
  name:
    description: Outlet label name.
    type: str
  state:
    description: Desired power state. unchanged leaves current state alone.
    type: str
    choices: [on, off, cycle, unchanged]
    default: unchanged
  startup_state:
    description: Power state when PDU starts up.
    type: str
    choices: [on, off, last_known]
  cycle_delay:
    description: Power cycle delay in seconds.
    type: int
  non_critical:
    description: Exclude outlet from load shedding.
    type: bool
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
    'on': 0,
    'off': 1,
    'last_known': 2,
}


def run_module(module):
    p = module.params
    outlet_num = p['outlet']  # 1始まり

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
        outlets = pdu.getOutlets()
    except Exception as e:
        module.fail_json(msg='Failed to get outlets: {}'.format(e))
        return

    idx = outlet_num - 1  # 0始まりインデックスに変換
    if idx < 0 or idx >= len(outlets):
        module.fail_json(msg='Outlet {} not found (PDU has {} outlets)'.format(
            outlet_num, len(outlets)))
        return

    outlet = outlets[idx]

    try:
        settings = outlet.getSettings()
    except Exception as e:
        module.fail_json(msg='Failed to get outlet settings: {}'.format(e))
        return

    settings_changed = False

    if p.get('name') is not None and settings.name != p['name']:
        settings.name = p['name']
        settings_changed = True

    if p.get('cycle_delay') is not None and settings.cycleDelay != p['cycle_delay']:
        settings.cycleDelay = p['cycle_delay']
        settings_changed = True

    if p.get('startup_state') is not None:
        desired_ss = STARTUP_STATE_MAP[p['startup_state']]
        if settings.startupState != desired_ss:
            settings.startupState = desired_ss
            settings_changed = True

    if p.get('non_critical') is not None and settings.nonCritical != p['non_critical']:
        settings.nonCritical = p['non_critical']
        settings_changed = True

    if settings_changed and not module.check_mode:
        try:
            outlet.setSettings(settings)
        except Exception as e:
            module.fail_json(msg='Failed to set outlet settings: {}'.format(e))
            return

    power_changed = False
    state = p.get('state', 'unchanged')

    if state == 'cycle':
        if not module.check_mode:
            try:
                outlet.cyclePowerState()
            except Exception as e:
                module.fail_json(msg='Failed to cycle outlet: {}'.format(e))
                return
        power_changed = True

    elif state in ('on', 'off'):
        try:
            current_state = outlet.getState()
        except Exception as e:
            module.fail_json(msg='Failed to get outlet state: {}'.format(e))
            return

        desired_ps = pdumodel.Outlet.PowerState.PS_ON if state == 'on' \
            else pdumodel.Outlet.PowerState.PS_OFF

        if current_state.powerState != desired_ps:
            if not module.check_mode:
                try:
                    outlet.setPowerState(desired_ps)
                except Exception as e:
                    module.fail_json(msg='Failed to set power state: {}'.format(e))
                    return
            power_changed = True

    module.exit_json(changed=settings_changed or power_changed)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            host=dict(type='str', required=True),
            username=dict(type='str', required=True),
            password=dict(type='str', required=True, no_log=True),
            validate_certs=dict(type='bool', default=True),
            outlet=dict(type='int', required=True),
            name=dict(type='str'),
            state=dict(type='str', choices=['on', 'off', 'cycle', 'unchanged'],
                       default='unchanged'),
            startup_state=dict(type='str', choices=['on', 'off', 'last_known']),
            cycle_delay=dict(type='int'),
            non_critical=dict(type='bool'),
        ),
        supports_check_mode=True,
    )
    run_module(module)


if __name__ == '__main__':
    main()
