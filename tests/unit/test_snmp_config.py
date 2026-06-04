import pytest
from unittest.mock import patch, MagicMock
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/modules'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/module_utils'))

import snmp_config


def make_module(params, check_mode=False):
    m = MagicMock()
    m.params = params
    m.check_mode = check_mode
    return m


def base_params(**overrides):
    p = {
        'host': '192.168.1.1', 'username': 'admin', 'password': 'pw',
        'validate_certs': True,
        'v2_enabled': None, 'v3_enabled': None,
        'read_community': None, 'write_community': None,
        'sys_contact': None, 'sys_name': None, 'sys_location': None,
    }
    p.update(overrides)
    return p


def make_cfg(v2enable=False, v3enable=False, readComm='public', writeComm='private',
             sysContact='', sysName='', sysLocation=''):
    c = MagicMock()
    c.v2enable = v2enable
    c.v3enable = v3enable
    c.readComm = readComm
    c.writeComm = writeComm
    c.sysContact = sysContact
    c.sysName = sysName
    c.sysLocation = sysLocation
    return c


class TestSnmpConfig:
    def _run(self, params, current_cfg):
        module = make_module(params)
        with patch('snmp_config.get_agent') as mga, \
             patch('snmp_config.devsettings') as mds:
            mga.return_value = MagicMock()
            mock_snmp = MagicMock()
            mds.Snmp.return_value = mock_snmp
            mock_snmp.getConfiguration.return_value = current_cfg
            snmp_config.run_module(module)
        return module, mock_snmp

    def test_no_change_when_all_match(self):
        params = base_params(v2_enabled=True, read_community='public', sys_name='PDU')
        cfg = make_cfg(v2enable=True, readComm='public', sysName='PDU')
        module, mock_snmp = self._run(params, cfg)
        mock_snmp.setConfiguration.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    def test_changed_when_v2_enabled_differs(self):
        params = base_params(v2_enabled=True)
        cfg = make_cfg(v2enable=False)
        module, mock_snmp = self._run(params, cfg)
        mock_snmp.setConfiguration.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_changed_when_read_community_differs(self):
        params = base_params(read_community='newpublic')
        cfg = make_cfg(readComm='public')
        module, mock_snmp = self._run(params, cfg)
        mock_snmp.setConfiguration.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_changed_when_sys_name_differs(self):
        params = base_params(sys_name='New-PDU')
        cfg = make_cfg(sysName='Old-PDU')
        module, mock_snmp = self._run(params, cfg)
        mock_snmp.setConfiguration.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_no_change_when_all_params_none(self):
        params = base_params()
        cfg = make_cfg()
        module, mock_snmp = self._run(params, cfg)
        mock_snmp.setConfiguration.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    def test_check_mode_does_not_call_set(self):
        module = make_module(base_params(v2_enabled=True), check_mode=True)
        cfg = make_cfg(v2enable=False)
        with patch('snmp_config.get_agent') as mga, \
             patch('snmp_config.devsettings') as mds:
            mga.return_value = MagicMock()
            mock_snmp = MagicMock()
            mds.Snmp.return_value = mock_snmp
            mock_snmp.getConfiguration.return_value = cfg
            snmp_config.run_module(module)
        mock_snmp.setConfiguration.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)

    def test_fail_json_on_connection_error(self):
        module = make_module(base_params(sys_name='X'))
        with patch('snmp_config.get_agent', side_effect=Exception('timeout')):
            snmp_config.run_module(module)
        module.fail_json.assert_called_once()
        assert 'timeout' in module.fail_json.call_args[1]['msg']
