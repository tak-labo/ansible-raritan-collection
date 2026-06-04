DOCUMENTATION = r"""
---
module: dns_config
short_description: Configure DNS settings on a Raritan PDU
description:
  - Manages DNS server addresses, search suffixes, and IPv6 resolver preference.
  - Idempotent - only applies changes when current settings differ.
  - Server address and search suffix lists are order-insensitive for comparison.
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
  servers:
    description: List of DNS server IP addresses.
    type: list
    elements: str
  search_suffixes:
    description: List of DNS search domain suffixes.
    type: list
    elements: str
  prefer_ipv6:
    description: Prefer IPv6 DNS resolver.
    type: bool
"""

EXAMPLES = r"""
- name: Configure DNS servers
  tak_labo.raritan_xerus.dns_config:
    host: 192.168.1.100
    username: admin
    password: secret
    validate_certs: false
    servers:
      - 8.8.8.8
      - 8.8.4.4
    search_suffixes:
      - example.com
    prefer_ipv6: false
"""

RETURN = r"""# """

import sys
import os

try:
    from ansible.module_utils.basic import AnsibleModule
    from ansible_collections.tak_labo.raritan_xerus.plugins.module_utils.raritan_client import get_agent, RaritanClientError
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../module_utils'))
    from raritan_client import get_agent, RaritanClientError

from raritan.rpc import net

NET_TARGET = '/net'

_DNS_ERROR_MSGS = {
    net.Net.ERR_DNS_TOO_MANY_SERVERS:        'too many DNS servers',
    net.Net.ERR_DNS_INVALID_SERVER:          'invalid DNS server address',
    net.Net.ERR_DNS_TOO_MANY_SEARCH_SUFFIXES: 'too many search suffixes',
    net.Net.ERR_DNS_INVALID_SEARCH_SUFFIX:   'invalid search suffix',
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

    net_mgr = net.Net(NET_TARGET, agent)

    try:
        settings = net_mgr.getSettings()
    except Exception as e:
        module.fail_json(msg='Failed to get network settings: {}'.format(e))
        return

    dns = settings.common.dns
    changed = False

    desired_servers = p.get('servers')
    if desired_servers is not None and sorted(dns.serverAddrs) != sorted(desired_servers):
        dns.serverAddrs = desired_servers
        changed = True

    desired_suffixes = p.get('search_suffixes')
    if desired_suffixes is not None and sorted(dns.searchSuffixes) != sorted(desired_suffixes):
        dns.searchSuffixes = desired_suffixes
        changed = True

    desired_ipv6 = p.get('prefer_ipv6')
    if desired_ipv6 is not None and dns.resolverPrefersIPv6 != desired_ipv6:
        dns.resolverPrefersIPv6 = desired_ipv6
        changed = True

    if changed and not module.check_mode:
        try:
            rc = net_mgr.setSettings(settings)
            if rc != 0:
                msg = _DNS_ERROR_MSGS.get(rc, 'error code {}'.format(rc))
                module.fail_json(msg='Failed to set DNS settings: {}'.format(msg))
                return
        except Exception as e:
            module.fail_json(msg='Failed to set DNS settings: {}'.format(e))
            return

    module.exit_json(changed=changed)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            host=dict(type='str', required=True),
            username=dict(type='str', required=True),
            password=dict(type='str', required=True, no_log=True),
            validate_certs=dict(type='bool', default=True),
            servers=dict(type='list', elements='str'),
            search_suffixes=dict(type='list', elements='str'),
            prefer_ipv6=dict(type='bool'),
        ),
        supports_check_mode=True,
    )
    run_module(module)


if __name__ == '__main__':
    main()
