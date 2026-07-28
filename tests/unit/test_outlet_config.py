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
        'sensor': None, 'upper_critical': None, 'upper_warning': None,
        'lower_warning': None, 'lower_critical': None,
        'unset_thresholds': None,
    }
    p.update(overrides)
    return p


def make_thresholds(upper_critical=None, upper_warning=None,
                     lower_warning=None, lower_critical=None):
    t = MagicMock()
    t.upperCriticalActive = upper_critical is not None
    t.upperCritical = upper_critical or 0.0
    t.upperWarningActive = upper_warning is not None
    t.upperWarning = upper_warning or 0.0
    t.lowerWarningActive = lower_warning is not None
    t.lowerWarning = lower_warning or 0.0
    t.lowerCriticalActive = lower_critical is not None
    t.lowerCritical = lower_critical or 0.0
    return t


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
                     outlet_settings=None, outlet_state=None,
                     sensor_thresholds=None, sensor_name='current', setthresholds_rc=0):
        mock_agent = MagicMock()
        mock_get_agent.return_value = mock_agent

        mock_pdu = MagicMock()
        mock_pdumodel.Pdu.return_value = mock_pdu

        sensor_mocks = []
        outlets = [MagicMock() for _ in range(n_outlets)]
        for i, o in enumerate(outlets):
            o.getSettings.return_value = outlet_settings or make_outlet_settings()
            o.getState.return_value = outlet_state or make_outlet_state(power_on=False)
            sensor_obj = MagicMock()
            sensor = MagicMock()
            sensor.getThresholds.return_value = sensor_thresholds or make_thresholds()
            sensor.setThresholds.return_value = setthresholds_rc
            setattr(sensor_obj, outlet_config.SENSOR_MAP[sensor_name], sensor)
            o.getSensors.return_value = sensor_obj
            sensor_mocks.append(sensor)

        mock_pdu.getOutlets.return_value = outlets
        return mock_pdu, outlets, sensor_mocks

    def test_no_change_when_name_matches(self):
        module = make_module(base_params(name='Outlet 2'))
        with patch('outlet_config.get_agent') as mga, \
             patch('outlet_config.pdumodel') as mpm:
            pdu, outlets, _ = self._setup_mocks(mga, mpm,
                outlet_settings=make_outlet_settings(name='Outlet 2'))
            outlet_config.run_module(module)

        outlets[1].setSettings.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    def test_changed_when_name_differs(self):
        module = make_module(base_params(name='New Name'))
        with patch('outlet_config.get_agent') as mga, \
             patch('outlet_config.pdumodel') as mpm:
            pdu, outlets, _ = self._setup_mocks(mga, mpm,
                outlet_settings=make_outlet_settings(name='Old Name'))
            outlet_config.run_module(module)

        outlets[1].setSettings.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_state_on_powers_on_when_off(self):
        module = make_module(base_params(state='on'))
        with patch('outlet_config.get_agent') as mga, \
             patch('outlet_config.pdumodel') as mpm:
            pdu, outlets, _ = self._setup_mocks(mga, mpm,
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
            pdu, outlets, _ = self._setup_mocks(mga, mpm,
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
            pdu, outlets, _ = self._setup_mocks(mga, mpm)
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
            pdu, outlets, _ = self._setup_mocks(mga, mpm,
                outlet_settings=make_outlet_settings(name='Old Name'))
            outlet_config.run_module(module)

        outlets[1].setSettings.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)

    def test_no_change_when_threshold_matches(self):
        module = make_module(base_params(sensor='current', upper_critical=15.0))
        with patch('outlet_config.get_agent') as mga, \
             patch('outlet_config.pdumodel') as mpm:
            pdu, outlets, sensors = self._setup_mocks(mga, mpm,
                sensor_thresholds=make_thresholds(upper_critical=15.0),
                sensor_name='current')
            outlet_config.run_module(module)

        sensors[1].setThresholds.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    def test_changed_when_threshold_differs(self):
        module = make_module(base_params(sensor='current', upper_critical=16.0))
        with patch('outlet_config.get_agent') as mga, \
             patch('outlet_config.pdumodel') as mpm:
            pdu, outlets, sensors = self._setup_mocks(mga, mpm,
                sensor_thresholds=make_thresholds(upper_critical=15.0),
                sensor_name='current')
            outlet_config.run_module(module)

        thresh_arg = sensors[1].setThresholds.call_args[0][0]
        assert thresh_arg.upperCritical == 16.0
        assert thresh_arg.upperCriticalActive is True
        module.exit_json.assert_called_once_with(changed=True)

    def test_threshold_param_without_sensor_fails(self):
        module = make_module(base_params(upper_critical=16.0))
        with patch('outlet_config.get_agent') as mga, \
             patch('outlet_config.pdumodel') as mpm:
            self._setup_mocks(mga, mpm)
            outlet_config.run_module(module)

        module.fail_json.assert_called_once()
        assert 'sensor' in module.fail_json.call_args[1]['msg']

    def test_set_thresholds_error_rc_fails(self):
        module = make_module(base_params(sensor='active_power', lower_warning=1.0))
        with patch('outlet_config.get_agent') as mga, \
             patch('outlet_config.pdumodel') as mpm:
            pdu, outlets, sensors = self._setup_mocks(mga, mpm,
                sensor_thresholds=make_thresholds(),
                sensor_name='active_power', setthresholds_rc=1)
            outlet_config.run_module(module)

        module.fail_json.assert_called_once()
        assert 'rc=1' in module.fail_json.call_args[1]['msg']

    def test_check_mode_does_not_call_set_thresholds(self):
        module = make_module(base_params(sensor='current', upper_critical=16.0),
                              check_mode=True)
        with patch('outlet_config.get_agent') as mga, \
             patch('outlet_config.pdumodel') as mpm:
            pdu, outlets, sensors = self._setup_mocks(mga, mpm,
                sensor_thresholds=make_thresholds(upper_critical=15.0),
                sensor_name='current')
            outlet_config.run_module(module)

        sensors[1].setThresholds.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)

    def test_unset_threshold_clears_active_flag(self):
        module = make_module(base_params(sensor='current', unset_thresholds=['upper_warning']))
        with patch('outlet_config.get_agent') as mga, \
             patch('outlet_config.pdumodel') as mpm:
            pdu, outlets, sensors = self._setup_mocks(mga, mpm,
                sensor_thresholds=make_thresholds(upper_warning=12.0),
                sensor_name='current')
            outlet_config.run_module(module)

        thresh_arg = sensors[1].setThresholds.call_args[0][0]
        assert thresh_arg.upperWarningActive is False
        module.exit_json.assert_called_once_with(changed=True)

    def test_unset_already_inactive_threshold_is_noop(self):
        module = make_module(base_params(sensor='current', unset_thresholds=['upper_warning']))
        with patch('outlet_config.get_agent') as mga, \
             patch('outlet_config.pdumodel') as mpm:
            pdu, outlets, sensors = self._setup_mocks(mga, mpm,
                sensor_thresholds=make_thresholds(),
                sensor_name='current')
            outlet_config.run_module(module)

        sensors[1].setThresholds.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    def test_set_and_unset_same_field_fails(self):
        module = make_module(base_params(
            sensor='current', upper_warning=12.0, unset_thresholds=['upper_warning']))
        with patch('outlet_config.get_agent') as mga, \
             patch('outlet_config.pdumodel') as mpm:
            self._setup_mocks(mga, mpm, sensor_name='current')
            outlet_config.run_module(module)

        module.fail_json.assert_called_once()
        assert 'upper_warning' in module.fail_json.call_args[1]['msg']

    def test_unset_threshold_without_sensor_fails(self):
        module = make_module(base_params(unset_thresholds=['upper_warning']))
        with patch('outlet_config.get_agent') as mga, \
             patch('outlet_config.pdumodel') as mpm:
            self._setup_mocks(mga, mpm)
            outlet_config.run_module(module)

        module.fail_json.assert_called_once()
        assert 'sensor' in module.fail_json.call_args[1]['msg']
