DOCUMENTATION = r"""
---
module: datetime_config
short_description: Configure NTP and timezone settings on a Raritan PDU
description:
  - Manages NTP server addresses, time synchronization protocol, and timezone.
  - Idempotent - only applies changes when current settings differ.
  - Timezone is specified by display name (e.g. "(UTC+09:00) Osaka, Sapporo, Tokyo").
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
  timezone:
    description: Timezone display name as returned by the PDU (e.g. "(UTC+09:00) Osaka, Sapporo, Tokyo").
    type: str
  protocol:
    description: Time synchronization protocol.
    type: str
    choices: [ntp, static]
  ntp_server1:
    description: Primary NTP server hostname or IP address.
    type: str
  ntp_server2:
    description: Secondary NTP server hostname or IP address.
    type: str
"""

EXAMPLES = r"""
- name: Configure NTP and timezone
  taklabo.raritan_xerus.datetime_config:
    host: 192.168.1.100
    username: admin
    password: secret
    validate_certs: false
    timezone: "(UTC+09:00) Osaka, Sapporo, Tokyo"
    protocol: ntp
    ntp_server1: ntp.example.com
    ntp_server2: ntp2.example.com
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

from raritan.rpc import datetime as dt_mod

DATETIME_TARGET = '/datetime'

_PROTOCOL_MAP = {
    'ntp': dt_mod.DateTime.Protocol.NTP,
    'static': dt_mod.DateTime.Protocol.STATIC,
}


def _resolve_timezone_id(dt_mgr, timezone_name):
    zones = dt_mgr.getZoneInfos(False)
    for z in zones:
        if z.name == timezone_name:
            return z.id
    names = [z.name for z in zones]
    raise ValueError('Unknown timezone "{}". Available: {}'.format(timezone_name, names))


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

    dt_mgr = dt_mod.DateTime(DATETIME_TARGET, agent)

    try:
        cfg = dt_mgr.getCfg()
    except Exception as e:
        module.fail_json(msg='Failed to get datetime config: {}'.format(e))
        return

    changed = False

    desired_timezone = p.get('timezone')
    if desired_timezone is not None:
        try:
            zone_id = _resolve_timezone_id(dt_mgr, desired_timezone)
        except ValueError as e:
            module.fail_json(msg=str(e))
            return
        if cfg.zoneCfg.id != zone_id:
            cfg.zoneCfg.id = zone_id
            cfg.zoneCfg.name = desired_timezone
            changed = True

    desired_protocol = p.get('protocol')
    if desired_protocol is not None:
        sdk_protocol = _PROTOCOL_MAP[desired_protocol]
        if cfg.protocol != sdk_protocol:
            cfg.protocol = sdk_protocol
            changed = True

    desired_server1 = p.get('ntp_server1')
    if desired_server1 is not None and cfg.ntpCfg.server1 != desired_server1:
        cfg.ntpCfg.server1 = desired_server1
        changed = True

    desired_server2 = p.get('ntp_server2')
    if desired_server2 is not None and cfg.ntpCfg.server2 != desired_server2:
        cfg.ntpCfg.server2 = desired_server2
        changed = True

    if changed and not module.check_mode:
        try:
            rc = dt_mgr.setCfg(cfg)
            if rc != 0:
                module.fail_json(msg='setCfg failed with error code: {}'.format(rc))
                return
        except Exception as e:
            module.fail_json(msg='Failed to set datetime config: {}'.format(e))
            return

    module.exit_json(changed=changed)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            host=dict(type='str', required=True),
            username=dict(type='str', required=True),
            password=dict(type='str', required=True, no_log=True),
            validate_certs=dict(type='bool', default=True),
            timezone=dict(type='str'),
            protocol=dict(type='str', choices=['ntp', 'static']),
            ntp_server1=dict(type='str'),
            ntp_server2=dict(type='str'),
        ),
        supports_check_mode=True,
    )
    run_module(module)


if __name__ == '__main__':
    main()
