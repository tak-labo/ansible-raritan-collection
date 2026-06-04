import pytest
from unittest.mock import patch, MagicMock, call
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/modules'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/module_utils'))

import pdu_config


def make_module(params):
    """AnsibleModule の最小限 mock を返す。"""
    m = MagicMock()
    m.params = params
    m.check_mode = False
    return m


def make_settings(name='PDU', startup_state_val=None, cycle_delay=0):
    """pdumodel.Pdu.Settings 風の mock を返す。"""
    from raritan.rpc import pdumodel as pm
    s = MagicMock()
    s.name = name
    s.startupState = startup_state_val if startup_state_val is not None else pm.Pdu.StartupState.SS_ON
    s.cycleDelay = cycle_delay
    return s


class TestPduConfig:
    def _run(self, module_params, current_settings, expect_changed):
        """共通テストヘルパー。"""
        module = make_module(module_params)
        current = current_settings

        with patch('pdu_config.get_agent') as mock_get_agent, \
             patch('pdu_config.pdumodel') as mock_pdumodel:

            mock_agent = MagicMock()
            mock_get_agent.return_value = mock_agent

            mock_pdu = MagicMock()
            mock_pdumodel.Pdu.return_value = mock_pdu
            mock_pdu.getSettings.return_value = current

            pdu_config.run_module(module)

        if expect_changed:
            mock_pdu.setSettings.assert_called_once()
            module.exit_json.assert_called_once_with(changed=True)
        else:
            mock_pdu.setSettings.assert_not_called()
            module.exit_json.assert_called_once_with(changed=False)

    def test_no_change_when_name_matches(self):
        params = {
            'host': '192.168.1.1', 'username': 'admin', 'password': 'pw',
            'validate_certs': True, 'name': 'PDU', 'startup_state': None, 'cycle_delay': None,
        }
        current = make_settings(name='PDU')
        self._run(params, current, expect_changed=False)

    def test_changed_when_name_differs(self):
        params = {
            'host': '192.168.1.1', 'username': 'admin', 'password': 'pw',
            'validate_certs': True, 'name': 'New PDU Name', 'startup_state': None, 'cycle_delay': None,
        }
        current = make_settings(name='Old Name')
        self._run(params, current, expect_changed=True)

    def test_changed_when_cycle_delay_differs(self):
        params = {
            'host': '192.168.1.1', 'username': 'admin', 'password': 'pw',
            'validate_certs': True, 'name': None, 'startup_state': None, 'cycle_delay': 15,
        }
        current = make_settings(cycle_delay=0)
        self._run(params, current, expect_changed=True)

    def test_no_change_when_all_params_none(self):
        """全パラメータが None（未指定）の場合は変更なし。"""
        params = {
            'host': '192.168.1.1', 'username': 'admin', 'password': 'pw',
            'validate_certs': True, 'name': None, 'startup_state': None, 'cycle_delay': None,
        }
        current = make_settings()
        self._run(params, current, expect_changed=False)

    def test_fail_json_on_connection_error(self):
        module = make_module({
            'host': '192.168.1.1', 'username': 'admin', 'password': 'pw',
            'validate_certs': True, 'name': 'X', 'startup_state': None, 'cycle_delay': None,
        })
        with patch('pdu_config.get_agent', side_effect=Exception('timeout')):
            pdu_config.run_module(module)
        module.fail_json.assert_called_once()
        assert 'timeout' in module.fail_json.call_args[1]['msg']
