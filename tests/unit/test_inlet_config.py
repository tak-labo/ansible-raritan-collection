import pytest
from unittest.mock import patch, MagicMock
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/modules'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/module_utils'))

import inlet_config


def make_module(params, check_mode=False):
    m = MagicMock()
    m.params = params
    m.check_mode = check_mode
    return m


def base_params(**overrides):
    p = {
        'host': '192.168.1.1', 'username': 'admin', 'password': 'pw',
        'validate_certs': True, 'inlet': 2,
        'name': None,
        'sensor': None, 'upper_critical': None, 'upper_warning': None,
        'lower_warning': None, 'lower_critical': None,
        'unset_thresholds': None,
    }
    p.update(overrides)
    return p


def make_inlet_settings(name='Inlet 2'):
    s = MagicMock()
    s.name = name
    return s


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


class TestInletConfig:
    def _setup_mocks(self, mock_get_agent, mock_pdumodel, n_inlets=2, inlet_settings=None,
                     sensor_thresholds=None, sensor_name='voltage', setthresholds_rc=0):
        mock_agent = MagicMock()
        mock_get_agent.return_value = mock_agent

        mock_pdu = MagicMock()
        mock_pdumodel.Pdu.return_value = mock_pdu

        sensor_mocks = []
        inlets = [MagicMock() for _ in range(n_inlets)]
        for i, inlet in enumerate(inlets):
            inlet.getSettings.return_value = inlet_settings or make_inlet_settings()
            sensor_obj = MagicMock()
            sensor = MagicMock()
            sensor.getThresholds.return_value = sensor_thresholds or make_thresholds()
            sensor.setThresholds.return_value = setthresholds_rc
            setattr(sensor_obj, inlet_config.SENSOR_MAP[sensor_name], sensor)
            inlet.getSensors.return_value = sensor_obj
            sensor_mocks.append(sensor)

        mock_pdu.getInlets.return_value = inlets
        return mock_pdu, inlets, sensor_mocks

    def test_no_change_when_name_matches(self):
        module = make_module(base_params(name='Inlet 2'))
        with patch('inlet_config.get_agent') as mga, \
             patch('inlet_config.pdumodel') as mpm:
            pdu, inlets, _ = self._setup_mocks(mga, mpm,
                inlet_settings=make_inlet_settings(name='Inlet 2'))
            inlet_config.run_module(module)

        inlets[1].setSettings.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    def test_changed_when_name_differs(self):
        module = make_module(base_params(name='New Name'))
        with patch('inlet_config.get_agent') as mga, \
             patch('inlet_config.pdumodel') as mpm:
            pdu, inlets, _ = self._setup_mocks(mga, mpm,
                inlet_settings=make_inlet_settings(name='Old Name'))
            inlet_config.run_module(module)

        inlets[1].setSettings.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_inlet_number_out_of_range(self):
        module = make_module(base_params(inlet=99))
        with patch('inlet_config.get_agent') as mga, \
             patch('inlet_config.pdumodel') as mpm:
            self._setup_mocks(mga, mpm, n_inlets=2)
            inlet_config.run_module(module)

        module.fail_json.assert_called_once()
        assert 'Inlet 99' in module.fail_json.call_args[1]['msg']

    def test_check_mode_does_not_call_set(self):
        module = make_module(base_params(name='New Name'), check_mode=True)
        with patch('inlet_config.get_agent') as mga, \
             patch('inlet_config.pdumodel') as mpm:
            pdu, inlets, _ = self._setup_mocks(mga, mpm,
                inlet_settings=make_inlet_settings(name='Old Name'))
            inlet_config.run_module(module)

        inlets[1].setSettings.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)

    def test_no_change_when_threshold_matches(self):
        module = make_module(base_params(sensor='voltage', upper_critical=250.0))
        with patch('inlet_config.get_agent') as mga, \
             patch('inlet_config.pdumodel') as mpm:
            pdu, inlets, sensors = self._setup_mocks(mga, mpm,
                sensor_thresholds=make_thresholds(upper_critical=250.0),
                sensor_name='voltage')
            inlet_config.run_module(module)

        sensors[1].setThresholds.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    def test_changed_when_threshold_differs(self):
        module = make_module(base_params(sensor='voltage', upper_critical=260.0))
        with patch('inlet_config.get_agent') as mga, \
             patch('inlet_config.pdumodel') as mpm:
            pdu, inlets, sensors = self._setup_mocks(mga, mpm,
                sensor_thresholds=make_thresholds(upper_critical=250.0),
                sensor_name='voltage')
            inlet_config.run_module(module)

        thresh_arg = sensors[1].setThresholds.call_args[0][0]
        assert thresh_arg.upperCritical == 260.0
        assert thresh_arg.upperCriticalActive is True
        module.exit_json.assert_called_once_with(changed=True)

    def test_threshold_param_without_sensor_fails(self):
        module = make_module(base_params(upper_critical=260.0))
        with patch('inlet_config.get_agent') as mga, \
             patch('inlet_config.pdumodel') as mpm:
            self._setup_mocks(mga, mpm)
            inlet_config.run_module(module)

        module.fail_json.assert_called_once()
        assert 'sensor' in module.fail_json.call_args[1]['msg']

    def test_set_thresholds_error_rc_fails(self):
        module = make_module(base_params(sensor='current', lower_warning=1.0))
        with patch('inlet_config.get_agent') as mga, \
             patch('inlet_config.pdumodel') as mpm:
            pdu, inlets, sensors = self._setup_mocks(mga, mpm,
                sensor_thresholds=make_thresholds(),
                sensor_name='current', setthresholds_rc=1)
            inlet_config.run_module(module)

        module.fail_json.assert_called_once()
        assert 'rc=1' in module.fail_json.call_args[1]['msg']

    def test_check_mode_does_not_call_set_thresholds(self):
        module = make_module(base_params(sensor='voltage', upper_critical=260.0),
                              check_mode=True)
        with patch('inlet_config.get_agent') as mga, \
             patch('inlet_config.pdumodel') as mpm:
            pdu, inlets, sensors = self._setup_mocks(mga, mpm,
                sensor_thresholds=make_thresholds(upper_critical=250.0),
                sensor_name='voltage')
            inlet_config.run_module(module)

        sensors[1].setThresholds.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)

    def test_unset_threshold_clears_active_flag(self):
        module = make_module(base_params(sensor='voltage', unset_thresholds=['upper_warning']))
        with patch('inlet_config.get_agent') as mga, \
             patch('inlet_config.pdumodel') as mpm:
            pdu, inlets, sensors = self._setup_mocks(mga, mpm,
                sensor_thresholds=make_thresholds(upper_warning=240.0),
                sensor_name='voltage')
            inlet_config.run_module(module)

        thresh_arg = sensors[1].setThresholds.call_args[0][0]
        assert thresh_arg.upperWarningActive is False
        module.exit_json.assert_called_once_with(changed=True)

    def test_unset_already_inactive_threshold_is_noop(self):
        module = make_module(base_params(sensor='voltage', unset_thresholds=['upper_warning']))
        with patch('inlet_config.get_agent') as mga, \
             patch('inlet_config.pdumodel') as mpm:
            pdu, inlets, sensors = self._setup_mocks(mga, mpm,
                sensor_thresholds=make_thresholds(),
                sensor_name='voltage')
            inlet_config.run_module(module)

        sensors[1].setThresholds.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    def test_set_and_unset_same_field_fails(self):
        module = make_module(base_params(
            sensor='voltage', upper_warning=240.0, unset_thresholds=['upper_warning']))
        with patch('inlet_config.get_agent') as mga, \
             patch('inlet_config.pdumodel') as mpm:
            self._setup_mocks(mga, mpm, sensor_name='voltage')
            inlet_config.run_module(module)

        module.fail_json.assert_called_once()
        assert 'upper_warning' in module.fail_json.call_args[1]['msg']

    def test_reapply_same_value_reactivates_inactive_threshold(self):
        # value already matches stored threshold, but Active flag is off
        # (e.g. previously cleared via unset_thresholds) -- must still re-enable.
        module = make_module(base_params(sensor='voltage', upper_warning=240.0))
        with patch('inlet_config.get_agent') as mga, \
             patch('inlet_config.pdumodel') as mpm:
            thresholds = make_thresholds()
            thresholds.upperWarning = 240.0
            thresholds.upperWarningActive = False
            pdu, inlets, sensors = self._setup_mocks(mga, mpm,
                sensor_thresholds=thresholds, sensor_name='voltage')
            inlet_config.run_module(module)

        thresh_arg = sensors[1].setThresholds.call_args[0][0]
        assert thresh_arg.upperWarningActive is True
        module.exit_json.assert_called_once_with(changed=True)

    def test_unset_threshold_without_sensor_fails(self):
        module = make_module(base_params(unset_thresholds=['upper_warning']))
        with patch('inlet_config.get_agent') as mga, \
             patch('inlet_config.pdumodel') as mpm:
            self._setup_mocks(mga, mpm)
            inlet_config.run_module(module)

        module.fail_json.assert_called_once()
        assert 'sensor' in module.fail_json.call_args[1]['msg']
