import pytest
from unittest.mock import patch, MagicMock
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/modules'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/module_utils'))

import user_account


def make_module(params, check_mode=False):
    m = MagicMock()
    m.params = params
    m.check_mode = check_mode
    return m


def base_params(**overrides):
    p = {
        'host': '192.168.1.1', 'username': 'admin', 'password': 'pw',
        'validate_certs': True,
        'target_user': 'admin',
        'state': 'present',
        'new_password': 'NewPassw0rd!',
        'snmp_v3_enabled': True,
        'sec_level': 'auth_priv',
        'auth_protocol': 'sha256',
        'priv_protocol': 'aes128',
        'use_password_as_auth_passphrase': True,
        'auth_passphrase': None,
        'use_auth_passphrase_as_priv_passphrase': True,
        'priv_passphrase': None,
    }
    p.update(overrides)
    return p


def make_snmp_settings(enabled=False, sec_level=None, auth_proto=None,
                       priv_proto=None, use_pw_as_auth=True, use_auth_as_priv=True):
    s = MagicMock()
    s.enabled = enabled
    s.secLevel = sec_level or 'AUTH_PRIV'
    s.authProtocol = auth_proto or 'SHA1'
    s.privProtocol = priv_proto or 'AES128'
    s.usePasswordAsAuthPassphrase = use_pw_as_auth
    s.useAuthPassphraseAsPrivPassphrase = use_auth_as_priv
    s.authPassphrase = ''
    s.privPassphrase = ''
    return s


def make_user_info(snmp_settings=None):
    info = MagicMock()
    info.snmpV3Settings = snmp_settings or make_snmp_settings()
    return info


class TestUserAccount:
    def _setup(self, mock_get_agent, mock_usermgmt, info=None,
               existing_users=None):
        mock_get_agent.return_value = MagicMock()

        mock_mgr = MagicMock()
        mock_usermgmt.UserManager.return_value = mock_mgr
        mock_mgr.getAccountNames.return_value = existing_users if existing_users is not None else ['admin']
        mock_mgr.deleteAccount.return_value = 0
        mock_mgr.createAccountFull.return_value = 0

        mock_user = MagicMock()
        mock_usermgmt.User.return_value = mock_user
        mock_user.getInfo.return_value = info or make_user_info()
        mock_user.updateAccountFull.return_value = 0

        mock_usermgmt.UserInfo.return_value = make_user_info()

        mock_usermgmt.SnmpV3SecLevel.NO_AUTH_NO_PRIV = 'NO_AUTH_NO_PRIV'
        mock_usermgmt.SnmpV3SecLevel.AUTH_NO_PRIV = 'AUTH_NO_PRIV'
        mock_usermgmt.SnmpV3SecLevel.AUTH_PRIV = 'AUTH_PRIV'
        mock_usermgmt.SnmpV3AuthProto.MD5 = 'MD5'
        mock_usermgmt.SnmpV3AuthProto.SHA1 = 'SHA1'
        mock_usermgmt.SnmpV3AuthProto.SHA224 = 'SHA224'
        mock_usermgmt.SnmpV3AuthProto.SHA256 = 'SHA256'
        mock_usermgmt.SnmpV3AuthProto.SHA384 = 'SHA384'
        mock_usermgmt.SnmpV3AuthProto.SHA512 = 'SHA512'
        mock_usermgmt.SnmpV3PrivProto.DES = 'DES'
        mock_usermgmt.SnmpV3PrivProto.AES128 = 'AES128'
        mock_usermgmt.SnmpV3PrivProto.AES192 = 'AES192'
        mock_usermgmt.SnmpV3PrivProto.AES256 = 'AES256'
        mock_usermgmt.SnmpV3PrivProto.AES192_3DES = 'AES192_3DES'
        mock_usermgmt.SnmpV3PrivProto.AES256_3DES = 'AES256_3DES'

        return mock_mgr, mock_user

    # ------------------------------------------------------------------
    # state: present — user exists (update path)
    # ------------------------------------------------------------------

    def test_enable_snmpv3(self):
        info = make_user_info(make_snmp_settings(enabled=False))
        module = make_module(base_params(snmp_v3_enabled=True))
        with patch('user_account.get_agent') as mga, \
             patch('user_account.usermgmt') as mum:
            mgr, user = self._setup(mga, mum, info)
            user_account.run_module(module)
        user.updateAccountFull.assert_called_once_with('NewPassw0rd!', info)
        module.exit_json.assert_called_once_with(changed=True)

    def test_no_change_when_matches(self):
        s = make_snmp_settings(
            enabled=True, sec_level='AUTH_PRIV',
            auth_proto='SHA256', priv_proto='AES128',
            use_pw_as_auth=True, use_auth_as_priv=True,
        )
        info = make_user_info(s)
        module = make_module(base_params())
        with patch('user_account.get_agent') as mga, \
             patch('user_account.usermgmt') as mum, \
             patch.dict(user_account.SEC_LEVEL_MAP, {'auth_priv': 'AUTH_PRIV'}), \
             patch.dict(user_account.AUTH_PROTO_MAP, {'sha256': 'SHA256'}), \
             patch.dict(user_account.PRIV_PROTO_MAP, {'aes128': 'AES128'}):
            mgr, user = self._setup(mga, mum, info)
            user_account.run_module(module)
        user.updateAccountFull.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    def test_change_auth_protocol(self):
        s = make_snmp_settings(enabled=True, sec_level='AUTH_PRIV',
                               auth_proto='SHA256', priv_proto='AES128')
        info = make_user_info(s)
        module = make_module(base_params(auth_protocol='sha512'))
        with patch('user_account.get_agent') as mga, \
             patch('user_account.usermgmt') as mum, \
             patch.dict(user_account.SEC_LEVEL_MAP, {'auth_priv': 'AUTH_PRIV'}), \
             patch.dict(user_account.AUTH_PROTO_MAP, {'sha512': 'SHA512'}), \
             patch.dict(user_account.PRIV_PROTO_MAP, {'aes128': 'AES128'}):
            mgr, user = self._setup(mga, mum, info)
            user_account.run_module(module)
        user.updateAccountFull.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_passphrase_always_triggers_change(self):
        s = make_snmp_settings(enabled=True, use_pw_as_auth=False)
        info = make_user_info(s)
        module = make_module(base_params(
            use_password_as_auth_passphrase=False,
            auth_passphrase='mysecret',
        ))
        with patch('user_account.get_agent') as mga, \
             patch('user_account.usermgmt') as mum, \
             patch.dict(user_account.SEC_LEVEL_MAP, {'auth_priv': 'AUTH_PRIV'}), \
             patch.dict(user_account.AUTH_PROTO_MAP, {'sha256': 'SHA256'}), \
             patch.dict(user_account.PRIV_PROTO_MAP, {'aes128': 'AES128'}):
            mgr, user = self._setup(mga, mum, info)
            user_account.run_module(module)
        user.updateAccountFull.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_check_mode_does_not_call_update(self):
        info = make_user_info(make_snmp_settings(enabled=False))
        module = make_module(base_params(), check_mode=True)
        with patch('user_account.get_agent') as mga, \
             patch('user_account.usermgmt') as mum:
            mgr, user = self._setup(mga, mum, info)
            user_account.run_module(module)
        user.updateAccountFull.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)

    def test_user_target_path(self):
        info = make_user_info(make_snmp_settings(enabled=False))
        module = make_module(base_params(target_user='testuser'))
        with patch('user_account.get_agent') as mga, \
             patch('user_account.usermgmt') as mum:
            mgr, user = self._setup(mga, mum, info, existing_users=['testuser'])
            user_account.run_module(module)
        mum.User.assert_called_once_with('/auth/user/testuser', mga.return_value)

    def test_fail_on_getinfo_error(self):
        module = make_module(base_params())
        with patch('user_account.get_agent') as mga, \
             patch('user_account.usermgmt') as mum:
            mgr, user = self._setup(mga, mum)
            user.getInfo.side_effect = Exception('not found')
            user_account.run_module(module)
        module.fail_json.assert_called_once()
        assert 'admin' in module.fail_json.call_args[1]['msg']

    def test_fail_on_connection_error(self):
        module = make_module(base_params())
        with patch('user_account.get_agent', side_effect=Exception('timeout')):
            user_account.run_module(module)
        module.fail_json.assert_called_once()
        assert 'timeout' in module.fail_json.call_args[1]['msg']

    # ------------------------------------------------------------------
    # state: present — user does not exist (create path)
    # ------------------------------------------------------------------

    def test_create_user_when_not_exists(self):
        module = make_module(base_params(target_user='newuser'))
        with patch('user_account.get_agent') as mga, \
             patch('user_account.usermgmt') as mum:
            mgr, user = self._setup(mga, mum, existing_users=[])
            user_account.run_module(module)
        # Two-step creation: createAccountFull(temp_pw) then updateAccountFull(new_pw)
        mgr.createAccountFull.assert_called_once()
        user.updateAccountFull.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_create_fails_without_new_password(self):
        module = make_module(base_params(target_user='newuser', new_password=None))
        with patch('user_account.get_agent') as mga, \
             patch('user_account.usermgmt') as mum:
            self._setup(mga, mum, existing_users=[])
            user_account.run_module(module)
        module.fail_json.assert_called_once()
        assert 'new_password' in module.fail_json.call_args[1]['msg']

    def test_create_check_mode_does_not_call_create(self):
        module = make_module(base_params(target_user='newuser'), check_mode=True)
        with patch('user_account.get_agent') as mga, \
             patch('user_account.usermgmt') as mum:
            mgr, user = self._setup(mga, mum, existing_users=[])
            user_account.run_module(module)
        mgr.createAccountFull.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)

    # ------------------------------------------------------------------
    # state: absent
    # ------------------------------------------------------------------

    def test_absent_deletes_existing_user(self):
        module = make_module(base_params(state='absent', target_user='admin'))
        with patch('user_account.get_agent') as mga, \
             patch('user_account.usermgmt') as mum:
            mgr, user = self._setup(mga, mum, existing_users=['admin'])
            user_account.run_module(module)
        mgr.deleteAccount.assert_called_once_with('admin')
        module.exit_json.assert_called_once_with(changed=True)

    def test_absent_no_change_when_user_missing(self):
        module = make_module(base_params(state='absent', target_user='ghost'))
        with patch('user_account.get_agent') as mga, \
             patch('user_account.usermgmt') as mum:
            mgr, user = self._setup(mga, mum, existing_users=['admin'])
            user_account.run_module(module)
        mgr.deleteAccount.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    def test_absent_check_mode_does_not_delete(self):
        module = make_module(base_params(state='absent', target_user='admin'), check_mode=True)
        with patch('user_account.get_agent') as mga, \
             patch('user_account.usermgmt') as mum:
            mgr, user = self._setup(mga, mum, existing_users=['admin'])
            user_account.run_module(module)
        mgr.deleteAccount.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)
