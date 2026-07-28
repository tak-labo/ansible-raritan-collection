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
    }
    p.update(overrides)
    return p


def make_inlet_settings(name='Inlet 2'):
    s = MagicMock()
    s.name = name
    return s


class TestInletConfig:
    def _setup_mocks(self, mock_get_agent, mock_pdumodel, n_inlets=2, inlet_settings=None):
        mock_agent = MagicMock()
        mock_get_agent.return_value = mock_agent

        mock_pdu = MagicMock()
        mock_pdumodel.Pdu.return_value = mock_pdu

        inlets = [MagicMock() for _ in range(n_inlets)]
        for i, inlet in enumerate(inlets):
            inlet.getSettings.return_value = inlet_settings or make_inlet_settings()

        mock_pdu.getInlets.return_value = inlets
        return mock_pdu, inlets

    def test_no_change_when_name_matches(self):
        module = make_module(base_params(name='Inlet 2'))
        with patch('inlet_config.get_agent') as mga, \
             patch('inlet_config.pdumodel') as mpm:
            pdu, inlets = self._setup_mocks(mga, mpm,
                inlet_settings=make_inlet_settings(name='Inlet 2'))
            inlet_config.run_module(module)

        inlets[1].setSettings.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    def test_changed_when_name_differs(self):
        module = make_module(base_params(name='New Name'))
        with patch('inlet_config.get_agent') as mga, \
             patch('inlet_config.pdumodel') as mpm:
            pdu, inlets = self._setup_mocks(mga, mpm,
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
            pdu, inlets = self._setup_mocks(mga, mpm,
                inlet_settings=make_inlet_settings(name='Old Name'))
            inlet_config.run_module(module)

        inlets[1].setSettings.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)
