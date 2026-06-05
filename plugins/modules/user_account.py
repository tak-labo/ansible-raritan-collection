DOCUMENTATION = r"""
---
module: user_account
short_description: Manage Raritan PDU user accounts and their SNMPv3 settings
description:
  - Creates, deletes, and configures user accounts on a Raritan PDU.
  - When state is present, creates the user if it does not exist and configures
    SNMPv3 settings idempotently.
  - When state is absent, deletes the user if it exists.
  - Passphrases are write-only and are not included in the idempotency check.
  - Due to Raritan API design, applying changes also sets the target user's
    password via new_password. If no settings change is detected, new_password
    is never sent to the PDU.
version_added: "1.0.0"
author:
  - Takahiro Nagafuchi (@tak)
options:
  host:
    description: PDU hostname or IP address.
    required: true
    type: str
  username:
    description: Authentication username (PDU admin).
    required: true
    type: str
  password:
    description: Authentication password (PDU admin).
    required: true
    type: str
    no_log: true
  validate_certs:
    description: Validate TLS certificate.
    type: bool
    default: true
  target_user:
    description: Username of the account to manage.
    required: true
    type: str
  state:
    description: Desired state of the user account.
    type: str
    choices: [present, absent]
    default: present
  new_password:
    description: >
      Password for the target user account.
      Required when creating a new user (state: present, user does not exist).
      Required when any SNMPv3 setting change is needed on an existing user
      (the Raritan PDU API requires a new password whenever account info is
      updated). Not used when settings are already in the desired state.
    type: str
    no_log: true
  snmp_v3_enabled:
    description: Enable SNMPv3 for this user.
    type: bool
  sec_level:
    description: SNMPv3 security level.
    type: str
    choices: [no_auth_no_priv, auth_no_priv, auth_priv]
  auth_protocol:
    description: Authentication protocol.
    type: str
    choices: [md5, sha1, sha224, sha256, sha384, sha512]
  priv_protocol:
    description: Privacy protocol.
    type: str
    choices: [des, aes128, aes192, aes256, aes192_3des, aes256_3des]
  use_password_as_auth_passphrase:
    description: Use the account password as the authentication passphrase.
    type: bool
  auth_passphrase:
    description: Authentication passphrase. Only used when use_password_as_auth_passphrase is false.
    type: str
    no_log: true
  use_auth_passphrase_as_priv_passphrase:
    description: Use the authentication passphrase as the privacy passphrase.
    type: bool
  priv_passphrase:
    description: Privacy passphrase. Only used when use_auth_passphrase_as_priv_passphrase is false.
    type: str
    no_log: true
"""

EXAMPLES = r"""
- name: Create user with SNMPv3
  tak_55.raritan_xerus.user_account:
    host: 192.168.1.100
    username: admin
    password: secret
    validate_certs: false
    target_user: snmpuser
    new_password: Passw0rd!
    snmp_v3_enabled: true
    sec_level: auth_priv
    auth_protocol: sha256
    priv_protocol: aes128
    use_password_as_auth_passphrase: true
    use_auth_passphrase_as_priv_passphrase: true
    state: present

- name: Delete user
  tak_55.raritan_xerus.user_account:
    host: 192.168.1.100
    username: admin
    password: secret
    validate_certs: false
    target_user: snmpuser
    state: absent
"""

RETURN = r"""# """

import sys
import os
import uuid

try:
    from ansible.module_utils.basic import AnsibleModule
    from ansible_collections.tak_55.raritan_xerus.plugins.module_utils.raritan_client import get_agent, RaritanClientError
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../module_utils'))
    from raritan_client import get_agent, RaritanClientError

from raritan.rpc import usermgmt

USER_MANAGER_TARGET = '/auth/user'
USER_TARGET_TEMPLATE = '/auth/user/{}'

SEC_LEVEL_MAP = {
    'no_auth_no_priv': usermgmt.SnmpV3SecLevel.NO_AUTH_NO_PRIV,
    'auth_no_priv':    usermgmt.SnmpV3SecLevel.AUTH_NO_PRIV,
    'auth_priv':       usermgmt.SnmpV3SecLevel.AUTH_PRIV,
}

AUTH_PROTO_MAP = {
    'md5':    usermgmt.SnmpV3AuthProto.MD5,
    'sha1':   usermgmt.SnmpV3AuthProto.SHA1,
    'sha224': usermgmt.SnmpV3AuthProto.SHA224,
    'sha256': usermgmt.SnmpV3AuthProto.SHA256,
    'sha384': usermgmt.SnmpV3AuthProto.SHA384,
    'sha512': usermgmt.SnmpV3AuthProto.SHA512,
}

PRIV_PROTO_MAP = {
    'des':         usermgmt.SnmpV3PrivProto.DES,
    'aes128':      usermgmt.SnmpV3PrivProto.AES128,
    'aes192':      usermgmt.SnmpV3PrivProto.AES192,
    'aes256':      usermgmt.SnmpV3PrivProto.AES256,
    'aes192_3des': usermgmt.SnmpV3PrivProto.AES192_3DES,
    'aes256_3des': usermgmt.SnmpV3PrivProto.AES256_3DES,
}

_IDEMPOTENCY_FIELDS = [
    ('snmp_v3_enabled',                        'enabled'),
    ('use_password_as_auth_passphrase',        'usePasswordAsAuthPassphrase'),
    ('use_auth_passphrase_as_priv_passphrase', 'useAuthPassphraseAsPrivPassphrase'),
]


def _configure_snmp(s, p):
    """Apply SNMPv3 params to settings object. Returns True if any field was changed."""
    changed = False

    for param_key, field in _IDEMPOTENCY_FIELDS:
        val = p.get(param_key)
        if val is not None and getattr(s, field) != val:
            setattr(s, field, val)
            changed = True

    if p.get('sec_level') is not None:
        desired = SEC_LEVEL_MAP[p['sec_level']]
        if s.secLevel != desired:
            s.secLevel = desired
            changed = True

    if p.get('auth_protocol') is not None:
        desired = AUTH_PROTO_MAP[p['auth_protocol']]
        if s.authProtocol != desired:
            s.authProtocol = desired
            changed = True

    if p.get('priv_protocol') is not None:
        desired = PRIV_PROTO_MAP[p['priv_protocol']]
        if s.privProtocol != desired:
            s.privProtocol = desired
            changed = True

    # Passphrases: always apply if provided (write-only — PDU does not return current value)
    if p.get('auth_passphrase') is not None:
        s.authPassphrase = p['auth_passphrase']
        changed = True

    if p.get('priv_passphrase') is not None:
        s.privPassphrase = p['priv_passphrase']
        changed = True

    return changed


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

    state = p.get('state', 'present')
    target_user = p['target_user']

    try:
        mgr = usermgmt.UserManager(USER_MANAGER_TARGET, agent)
        account_names = mgr.getAccountNames()
    except Exception as e:
        module.fail_json(msg='Failed to get account list: {}'.format(e))
        return

    if state == 'absent':
        if target_user not in account_names:
            module.exit_json(changed=False)
            return
        if not module.check_mode:
            try:
                rc = mgr.deleteAccount(target_user)
                if rc != 0:
                    module.fail_json(msg='Failed to delete user {!r}: error code {}'.format(target_user, rc))
                    return
            except Exception as e:
                module.fail_json(msg='Failed to delete user {!r}: {}'.format(target_user, e))
                return
        module.exit_json(changed=True)
        return

    # state: present
    if target_user not in account_names:
        new_pw = p.get('new_password')
        if not new_pw:
            module.fail_json(msg='new_password is required when creating a new user.')
            return
        if not module.check_mode:
            try:
                # createAccountFull does not support high security levels (AUTH_PRIV/AUTH_NO_PRIV).
                # Use a random temporary password so updateAccountFull can set the final
                # password and all SNMPv3 settings in one subsequent call.
                temp_pw = 'Tmp' + uuid.uuid4().hex
                rc = mgr.createAccountFull(target_user, temp_pw, usermgmt.UserInfo())
                if rc != 0:
                    module.fail_json(msg='Failed to create user {!r}: error code {}'.format(target_user, rc))
                    return
                user = usermgmt.User(USER_TARGET_TEMPLATE.format(target_user), agent)
                info = user.getInfo()
                _configure_snmp(info.snmpV3Settings, p)
                rc2 = user.updateAccountFull(new_pw, info)
                if rc2 != 0:
                    module.fail_json(msg='Failed to configure user {!r} after creation: error code {}'.format(target_user, rc2))
                    return
            except Exception as e:
                module.fail_json(msg='Failed to create user {!r}: {}'.format(target_user, e))
                return
        module.exit_json(changed=True)
        return

    # User exists — update SNMPv3 settings if needed
    target = USER_TARGET_TEMPLATE.format(target_user)
    user = usermgmt.User(target, agent)

    try:
        info = user.getInfo()
    except Exception as e:
        module.fail_json(msg='Failed to get user info for {!r}: {}'.format(target_user, e))
        return

    changed = _configure_snmp(info.snmpV3Settings, p)

    if changed:
        new_pw = p.get('new_password')
        if not new_pw:
            module.fail_json(msg=(
                'new_password is required when settings need to be changed. '
                'The Raritan PDU API requires a new password whenever account info is updated.'
            ))
            return

    if changed and not module.check_mode:
        try:
            rc = user.updateAccountFull(new_pw, info)
            if rc != 0:
                module.fail_json(msg='Failed to update user {!r}: error code {}'.format(target_user, rc))
                return
        except Exception as e:
            module.fail_json(msg='Failed to update user {!r}: {}'.format(target_user, e))
            return

    module.exit_json(changed=changed)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            host=dict(type='str', required=True),
            username=dict(type='str', required=True),
            password=dict(type='str', required=True, no_log=True),
            validate_certs=dict(type='bool', default=True),
            target_user=dict(type='str', required=True),
            state=dict(type='str', default='present', choices=['present', 'absent']),
            new_password=dict(type='str', no_log=True),
            snmp_v3_enabled=dict(type='bool'),
            sec_level=dict(type='str', choices=list(SEC_LEVEL_MAP)),
            auth_protocol=dict(type='str', choices=list(AUTH_PROTO_MAP)),
            priv_protocol=dict(type='str', choices=list(PRIV_PROTO_MAP)),
            use_password_as_auth_passphrase=dict(type='bool', no_log=False),
            auth_passphrase=dict(type='str', no_log=True),
            use_auth_passphrase_as_priv_passphrase=dict(type='bool', no_log=False),
            priv_passphrase=dict(type='str', no_log=True),
        ),
        supports_check_mode=True,
    )
    run_module(module)


if __name__ == '__main__':
    main()
