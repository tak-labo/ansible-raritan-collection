DOCUMENTATION = r"""
---
module: inlet_config
short_description: Configure a Raritan PDU inlet name
description:
  - Manages the inlet name. Settings management is idempotent.
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
  inlet:
    description: Inlet number (1-based).
    required: true
    type: int
  name:
    description: Inlet label name.
    type: str
"""

EXAMPLES = r"""
- name: Rename inlet 1
  taklabo.raritan_xerus.inlet_config:
    host: 192.168.1.100
    username: admin
    password: secret
    validate_certs: false
    inlet: 1
    name: "Main Feed"
"""

RETURN = r"""# """

import sys
import os

try:
    from ansible.module_utils.basic import AnsibleModule
    from ansible_collections.taklabo.raritan_xerus.plugins.module_utils.raritan_client import get_agent, RaritanClientError
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../module_utils'))
    from raritan_client import get_agent, RaritanClientError

from raritan.rpc import pdumodel

PDU_TARGET = '/model/pdu/0'


def run_module(module):
    p = module.params
    inlet_num = p['inlet']

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
        inlets = pdu.getInlets()
    except Exception as e:
        module.fail_json(msg='Failed to get inlets: {}'.format(e))
        return

    idx = inlet_num - 1
    if idx < 0 or idx >= len(inlets):
        module.fail_json(msg='Inlet {} not found (PDU has {} inlets)'.format(
            inlet_num, len(inlets)))
        return

    inlet = inlets[idx]

    try:
        settings = inlet.getSettings()
    except Exception as e:
        module.fail_json(msg='Failed to get inlet settings: {}'.format(e))
        return

    settings_changed = False

    if p.get('name') is not None and settings.name != p['name']:
        settings.name = p['name']
        settings_changed = True

    if settings_changed and not module.check_mode:
        try:
            inlet.setSettings(settings)
        except Exception as e:
            module.fail_json(msg='Failed to set inlet settings: {}'.format(e))
            return

    module.exit_json(changed=settings_changed)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            host=dict(type='str', required=True),
            username=dict(type='str', required=True),
            password=dict(type='str', required=True, no_log=True),
            validate_certs=dict(type='bool', default=True),
            inlet=dict(type='int', required=True),
            name=dict(type='str'),
        ),
        supports_check_mode=True,
    )
    run_module(module)


if __name__ == '__main__':
    main()
