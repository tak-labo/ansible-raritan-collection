import pytest
from unittest.mock import patch, MagicMock
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/modules'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/module_utils'))

import outlet_config


def make_module(params, check_mode=False):
    m = MagicMock()
    m.params = params
    m.check_mode = check_mode
    return m


def base_params(**overrides):
    p = {
        'host': '192.168.1.1', 'username': 'admin', 'password': 'pw',
        'validate_certs': True, 'outlet': 2,
        'name': None, 'state': 'unchanged', 'startup_state': None,
        'cycle_delay': None, 'non_critical': None,
    }
    p.update(overrides)
    return p


def make_outlet_settings(name='Outlet 2', startup_state=None, cycle_delay=0, non_critical=False):
    from raritan.rpc import pdumodel as pm
    s = MagicMock()
    s.name = name
    s.startupState = startup_state if startup_state is not None else pm.Outlet.StartupState.SS_ON
    s.cycleDelay = cycle_delay
    s.nonCritical = non_critical
    return s


def make_outlet_state(power_on=True):
    """pdumodel.Outlet.State 風 mock。"""
    st = MagicMock()
    # PowerState.PS_ON=1, PS_OFF=0
    st.powerState = 1 if power_on else 0
    return st


class TestOutletConfig:
    def _setup_mocks(self, mock_get_agent, mock_pdumodel, n_outlets=4,
                     outlet_settings=None, outlet_state=None):
        mock_agent = MagicMock()
        mock_get_agent.return_value = mock_agent

        mock_pdu = MagicMock()
        mock_pdumodel.Pdu.return_value = mock_pdu

        outlets = [MagicMock() for _ in range(n_outlets)]
        for i, o in enumerate(outlets):
            o.getSettings.return_value = outlet_settings or make_outlet_settings()
            o.getState.return_value = outlet_state or make_outlet_state(power_on=False)

        mock_pdu.getOutlets.return_value = outlets
        return mock_pdu, outlets

    def test_no_change_when_name_matches(self):
        module = make_module(base_params(name='Outlet 2'))
        with patch('outlet_config.get_agent') as mga, \
             patch('outlet_config.pdumodel') as mpm:
            pdu, outlets = self._setup_mocks(mga, mpm,
                outlet_settings=make_outlet_settings(name='Outlet 2'))
            outlet_config.run_module(module)

        outlets[1].setSettings.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    def test_changed_when_name_differs(self):
        module = make_module(base_params(name='New Name'))
        with patch('outlet_config.get_agent') as mga, \
             patch('outlet_config.pdumodel') as mpm:
            pdu, outlets = self._setup_mocks(mga, mpm,
                outlet_settings=make_outlet_settings(name='Old Name'))
            outlet_config.run_module(module)

        outlets[1].setSettings.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_state_on_powers_on_when_off(self):
        module = make_module(base_params(state='on'))
        with patch('outlet_config.get_agent') as mga, \
             patch('outlet_config.pdumodel') as mpm:
            pdu, outlets = self._setup_mocks(mga, mpm,
                outlet_state=make_outlet_state(power_on=False))
            mpm.Outlet.PowerState.PS_ON = 1
            mpm.Outlet.PowerState.PS_OFF = 0
            outlet_config.run_module(module)

        outlets[1].setPowerState.assert_called_once_with(1)
        module.exit_json.assert_called_once_with(changed=True)

    def test_state_on_no_change_when_already_on(self):
        module = make_module(base_params(state='on'))
        with patch('outlet_config.get_agent') as mga, \
             patch('outlet_config.pdumodel') as mpm:
            pdu, outlets = self._setup_mocks(mga, mpm,
                outlet_state=make_outlet_state(power_on=True))
            mpm.Outlet.PowerState.PS_ON = 1
            mpm.Outlet.PowerState.PS_OFF = 0
            outlet_config.run_module(module)

        outlets[1].setPowerState.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    def test_state_cycle_always_cycles(self):
        module = make_module(base_params(state='cycle'))
        with patch('outlet_config.get_agent') as mga, \
             patch('outlet_config.pdumodel') as mpm:
            pdu, outlets = self._setup_mocks(mga, mpm)
            mpm.Outlet.PowerState.PS_ON = 1
            mpm.Outlet.PowerState.PS_OFF = 0
            outlet_config.run_module(module)

        outlets[1].cyclePowerState.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_outlet_number_out_of_range(self):
        module = make_module(base_params(outlet=99))
        with patch('outlet_config.get_agent') as mga, \
             patch('outlet_config.pdumodel') as mpm:
            self._setup_mocks(mga, mpm, n_outlets=4)
            outlet_config.run_module(module)

        module.fail_json.assert_called_once()
        assert 'Outlet 99' in module.fail_json.call_args[1]['msg']

    def test_check_mode_does_not_call_set(self):
        module = make_module(base_params(name='New Name'), check_mode=True)
        with patch('outlet_config.get_agent') as mga, \
             patch('outlet_config.pdumodel') as mpm:
            pdu, outlets = self._setup_mocks(mga, mpm,
                outlet_settings=make_outlet_settings(name='Old Name'))
            outlet_config.run_module(module)

        outlets[1].setSettings.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)
