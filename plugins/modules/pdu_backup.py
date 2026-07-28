DOCUMENTATION = r"""
---
module: pdu_backup
short_description: Download and save a Raritan PDU configuration backup locally
description:
  - Downloads the PDU's raw or bulk configuration file and saves it to a local path.
  - Unlike settings modules, there is no getSettings/setSettings diff step - this
    performs a raw HTTP file transfer (not JSON-RPC).
  - When C(filename) is omitted, a timestamped filename is generated and the task
    always reports C(changed=true) (each run creates a new backup file).
  - When C(filename) is set explicitly, the downloaded content is compared against
    the existing file (if any) and C(changed=false) is reported when unchanged.
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
  backup_path:
    description: Local directory to save the backup file into. Created if missing.
    type: str
    default: ./backup
  filename:
    description: >-
      Backup filename. If omitted, a timestamped filename ("<host>_<timestamp>.cfg")
      is generated and every run is treated as a new backup (always changed).
    type: str
  method:
    description: >-
      C(raw) downloads the device's raw configuration file. C(bulk) uses the bulk
      configuration mechanism in backup mode, which supports password encryption
      and filter profiles.
    type: str
    choices: [raw, bulk]
    default: raw
  bulk_password:
    description: Password to encrypt the bulk config file with. Only used when C(method=bulk).
    type: str
    no_log: true
  bulk_filter_profile:
    description: Bulk configuration filter profile name to apply. Only used when C(method=bulk).
    type: str
"""

EXAMPLES = r"""
- name: Back up PDU configuration (timestamped, always changed)
  taklabo.raritan_xerus.pdu_backup:
    host: 192.168.1.100
    username: admin
    password: secret
    validate_certs: false
    backup_path: ./backup

- name: Back up to a fixed filename (idempotent, only changed on drift)
  taklabo.raritan_xerus.pdu_backup:
    host: 192.168.1.100
    username: admin
    password: secret
    validate_certs: false
    backup_path: ./backup
    filename: pdu01.cfg

- name: Back up using the bulk config mechanism with encryption
  taklabo.raritan_xerus.pdu_backup:
    host: 192.168.1.100
    username: admin
    password: secret
    validate_certs: false
    method: bulk
    bulk_password: "{{ bulk_backup_password }}"
"""

RETURN = r"""
backup_file:
  description: Full local path the backup was (or would be) written to.
  returned: always
  type: str
size:
  description: Size in bytes of the downloaded configuration data.
  returned: always
  type: int
"""

import sys
import os
import re
import datetime

try:
    from ansible.module_utils.basic import AnsibleModule
    from ansible_collections.taklabo.raritan_xerus.plugins.module_utils.raritan_client import get_agent, RaritanClientError
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../module_utils'))
    from raritan_client import get_agent, RaritanClientError

from raritan.rpc import rawcfg, bulkcfg


def _default_filename(host):
    safe_host = re.sub(r'[^\w.-]', '_', host)
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    return '{}_{}.cfg'.format(safe_host, timestamp)


def _content_matches(dest_path, data):
    if not os.path.isfile(dest_path):
        return False
    with open(dest_path, 'rb') as f:
        return f.read() == data


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

    try:
        if p['method'] == 'bulk':
            data = bulkcfg.download(
                agent, backup=True,
                password=p.get('bulk_password'),
                clear_text=(p.get('bulk_password') is None),
                filter_profile=p.get('bulk_filter_profile') or '',
            )
        else:
            data = rawcfg.download(agent)
    except Exception as e:
        module.fail_json(msg='Failed to download config: {}'.format(e))
        return

    if isinstance(data, str):
        data = data.encode('utf-8')

    fixed_filename = p.get('filename')
    filename = fixed_filename or _default_filename(p['host'])
    dest_path = os.path.join(p['backup_path'], filename)

    if fixed_filename and _content_matches(dest_path, data):
        changed = False
    else:
        changed = True

    if changed and not module.check_mode:
        if not os.path.isdir(p['backup_path']):
            if os.path.exists(p['backup_path']):
                module.fail_json(msg='backup_path exists and is not a directory: {}'.format(p['backup_path']))
                return
            try:
                os.makedirs(p['backup_path'])
            except OSError as e:
                module.fail_json(msg='Failed to create backup_path: {}'.format(e))
                return

        try:
            with open(dest_path, 'wb') as f:
                f.write(data)
        except OSError as e:
            module.fail_json(msg='Failed to write backup file: {}'.format(e))
            return

    module.exit_json(changed=changed, backup_file=dest_path, size=len(data))


def main():
    module = AnsibleModule(
        argument_spec=dict(
            host=dict(type='str', required=True),
            username=dict(type='str', required=True),
            password=dict(type='str', required=True, no_log=True),
            validate_certs=dict(type='bool', default=True),
            backup_path=dict(type='str', default='./backup'),
            filename=dict(type='str'),
            method=dict(type='str', choices=['raw', 'bulk'], default='raw'),
            bulk_password=dict(type='str', no_log=True),
            bulk_filter_profile=dict(type='str'),
        ),
        supports_check_mode=True,
    )
    run_module(module)


if __name__ == '__main__':
    main()
