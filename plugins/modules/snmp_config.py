DOCUMENTATION = r"""
---
module: snmp_config
short_description: Configure Raritan PDU SNMP settings
description:
  - Manages SNMP v2/v3 settings such as community strings and system information.
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
  v2_enabled:
    description: Enable SNMP v2.
    type: bool
  v3_enabled:
    description: Enable SNMP v3.
    type: bool
  read_community:
    description: SNMP v2 read community string.
    type: str
  write_community:
    description: SNMP v2 write community string.
    type: str
    no_log: true
  sys_contact:
    description: SNMP sysContact value.
    type: str
  sys_name:
    description: SNMP sysName value.
    type: str
  sys_location:
    description: SNMP sysLocation value.
    type: str
"""

import sys
import os

try:
    from ansible.module_utils.basic import AnsibleModule
    from ansible_collections.raritan.xerus.plugins.module_utils.raritan_client import get_agent, RaritanClientError
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../module_utils'))
    from raritan_client import get_agent, RaritanClientError

from raritan.rpc import devsettings

SNMP_TARGET = '/device/snmp'

FIELD_MAP = [
    ('v2_enabled',      'v2enable'),
    ('v3_enabled',      'v3enable'),
    ('read_community',  'readComm'),
    ('write_community', 'writeComm'),
    ('sys_contact',     'sysContact'),
    ('sys_name',        'sysName'),
    ('sys_location',    'sysLocation'),
]


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

    snmp = devsettings.Snmp(SNMP_TARGET, agent)

    try:
        cfg = snmp.getConfiguration()
    except Exception as e:
        module.fail_json(msg='Failed to get SNMP configuration: {}'.format(e))
        return

    changed = False

    for param_key, cfg_attr in FIELD_MAP:
        desired = p.get(param_key)
        if desired is not None and getattr(cfg, cfg_attr) != desired:
            setattr(cfg, cfg_attr, desired)
            changed = True

    if changed and not module.check_mode:
        try:
            snmp.setConfiguration(cfg)
        except Exception as e:
            module.fail_json(msg='Failed to set SNMP configuration: {}'.format(e))
            return

    module.exit_json(changed=changed)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            host=dict(type='str', required=True),
            username=dict(type='str', required=True),
            password=dict(type='str', required=True, no_log=True),
            validate_certs=dict(type='bool', default=True),
            v2_enabled=dict(type='bool'),
            v3_enabled=dict(type='bool'),
            read_community=dict(type='str'),
            write_community=dict(type='str', no_log=True),
            sys_contact=dict(type='str'),
            sys_name=dict(type='str'),
            sys_location=dict(type='str'),
        ),
        supports_check_mode=True,
    )
    run_module(module)


if __name__ == '__main__':
    main()
