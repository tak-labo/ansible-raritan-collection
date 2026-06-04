import pytest
from unittest.mock import patch, MagicMock
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/modules'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/module_utils'))

import pdu_facts


def make_module(params=None):
    m = MagicMock()
    m.params = params or {
        'host': '192.168.1.1', 'username': 'admin', 'password': 'pw',
        'validate_certs': True,
    }
    m.check_mode = False
    return m


def make_reading(value, valid=True):
    r = MagicMock()
    r.value = value
    r.valid = valid
    return r


def make_inlet_sensors(voltage=100.0, current=1.0, power=100.0, apparent=110.0,
                       pf=0.9, freq=50.0, energy=1000.0):
    s = MagicMock()
    s.voltage.getReading.return_value = make_reading(voltage)
    s.current.getReading.return_value = make_reading(current)
    s.activePower.getReading.return_value = make_reading(power)
    s.apparentPower.getReading.return_value = make_reading(apparent)
    s.powerFactor.getReading.return_value = make_reading(pf)
    s.lineFrequency.getReading.return_value = make_reading(freq)
    s.activeEnergy.getReading.return_value = make_reading(energy)
    return s


def make_outlet_sensors(current=0.5, power=50.0):
    s = MagicMock()
    s.current.getReading.return_value = make_reading(current)
    s.activePower.getReading.return_value = make_reading(power)
    return s


def make_nameplate(model='PX3-5138', serial='SN001', part=''):
    np = MagicMock()
    np.model = model
    np.serialNumber = serial
    np.partNumber = part
    return np


def make_meta(np=None, fw='4.3.0', hw='0x01', mac='00:11:22:33:44:55'):
    m = MagicMock()
    m.nameplate = np or make_nameplate()
    m.fwRevision = fw
    m.hwRevision = hw
    m.macAddress = mac
    return m


def make_settings(name='Test PDU', cycle_delay=5, startup_state=None):
    from raritan.rpc import pdumodel as pm
    s = MagicMock()
    s.name = name
    s.cycleDelay = cycle_delay
    s.startupState = startup_state or pm.Pdu.StartupState.SS_LASTKNOWN
    return s


def make_outlet(name='Outlet1', power_state=None, available=True, sensors=None):
    from raritan.rpc import pdumodel as pm
    o = MagicMock()
    o.getSettings.return_value.name = name
    o.getState.return_value.available = available
    o.getState.return_value.powerState = power_state or pm.Pdu.StartupState.SS_ON
    o.getSensors.return_value = sensors or make_outlet_sensors()
    return o


class TestPduFacts:
    def _setup(self, mock_get_agent, mock_pm, meta=None, settings=None, inlets=None, outlets=None):
        mock_get_agent.return_value = MagicMock()
        mock_pdu = MagicMock()
        mock_pm.Pdu.return_value = mock_pdu
        mock_pdu.getMetaData.return_value = meta or make_meta()
        mock_pdu.getSettings.return_value = settings or make_settings()
        mock_pdu.getInlets.return_value = inlets if inlets is not None else [MagicMock(getSensors=lambda: make_inlet_sensors())]
        mock_pdu.getOutlets.return_value = outlets if outlets is not None else []
        return mock_pdu

    def test_basic_facts_returned(self):
        module = make_module()
        with patch('pdu_facts.get_agent') as mga, patch('pdu_facts.pdumodel') as mpm:
            self._setup(mga, mpm)
            pdu_facts.run_module(module)
        module.exit_json.assert_called_once()
        call_kwargs = module.exit_json.call_args[1]
        assert call_kwargs['changed'] is False
        assert 'pdu' in call_kwargs['ansible_facts']

    def test_pdu_identification_fields(self):
        module = make_module()
        meta = make_meta(make_nameplate('PX3-5138', 'SN999', 'PN001'), '4.3.13', '0x03', 'aa:bb:cc:dd:ee:ff')
        with patch('pdu_facts.get_agent') as mga, patch('pdu_facts.pdumodel') as mpm:
            self._setup(mga, mpm, meta=meta)
            pdu_facts.run_module(module)
        facts = module.exit_json.call_args[1]['ansible_facts']['pdu']
        assert facts['model'] == 'PX3-5138'
        assert facts['serial_number'] == 'SN999'
        assert facts['part_number'] == 'PN001'
        assert facts['firmware'] == '4.3.13'
        assert facts['hardware'] == '0x03'
        assert facts['mac_address'] == 'aa:bb:cc:dd:ee:ff'

    def test_settings_fields(self):
        module = make_module()
        from raritan.rpc import pdumodel as pm
        settings = make_settings('My PDU', 10, pm.Pdu.StartupState.SS_ON)
        with patch('pdu_facts.get_agent') as mga, patch('pdu_facts.pdumodel') as mpm:
            self._setup(mga, mpm, settings=settings)
            pdu_facts.run_module(module)
        facts = module.exit_json.call_args[1]['ansible_facts']['pdu']
        assert facts['name'] == 'My PDU'
        assert facts['cycle_delay'] == 10
        assert facts['startup_state'] == 'on'

    def test_inlet_sensor_readings(self):
        module = make_module()
        inlet = MagicMock()
        inlet.getSensors.return_value = make_inlet_sensors(
            voltage=102.4, current=0.5, power=50.0, apparent=55.0,
            pf=0.91, freq=50.0, energy=1234.5
        )
        with patch('pdu_facts.get_agent') as mga, patch('pdu_facts.pdumodel') as mpm:
            self._setup(mga, mpm, inlets=[inlet])
            pdu_facts.run_module(module)
        facts = module.exit_json.call_args[1]['ansible_facts']['pdu']
        assert len(facts['inlets']) == 1
        inlet_facts = facts['inlets'][0]
        assert inlet_facts['index'] == 0
        assert inlet_facts['voltage_v'] == 102.4
        assert inlet_facts['current_a'] == 0.5
        assert inlet_facts['active_power_w'] == 50.0
        assert inlet_facts['line_frequency_hz'] == 50.0

    def test_sensor_invalid_returns_none(self):
        module = make_module()
        inlet = MagicMock()
        s = make_inlet_sensors()
        s.voltage.getReading.return_value = make_reading(0.0, valid=False)
        inlet.getSensors.return_value = s
        with patch('pdu_facts.get_agent') as mga, patch('pdu_facts.pdumodel') as mpm:
            self._setup(mga, mpm, inlets=[inlet])
            pdu_facts.run_module(module)
        facts = module.exit_json.call_args[1]['ansible_facts']['pdu']
        assert facts['inlets'][0]['voltage_v'] is None

    def test_sensor_exception_returns_none(self):
        module = make_module()
        inlet = MagicMock()
        s = make_inlet_sensors()
        s.voltage.getReading.side_effect = Exception('sensor error')
        inlet.getSensors.return_value = s
        with patch('pdu_facts.get_agent') as mga, patch('pdu_facts.pdumodel') as mpm:
            self._setup(mga, mpm, inlets=[inlet])
            pdu_facts.run_module(module)
        facts = module.exit_json.call_args[1]['ansible_facts']['pdu']
        assert facts['inlets'][0]['voltage_v'] is None

    def test_outlet_facts(self):
        module = make_module()
        from raritan.rpc import pdumodel as pm
        outlet = MagicMock()
        outlet.getSettings.return_value.name = 'Web Server'
        outlet.getState.return_value.available = True
        outlet.getState.return_value.powerState = pm.Outlet.PowerState.PS_ON
        outlet.getSensors.return_value = make_outlet_sensors(current=0.3, power=30.0)
        with patch('pdu_facts.get_agent') as mga, patch('pdu_facts.pdumodel') as mpm:
            self._setup(mga, mpm, outlets=[outlet])
            pdu_facts.run_module(module)
        facts = module.exit_json.call_args[1]['ansible_facts']['pdu']
        assert len(facts['outlets']) == 1
        o = facts['outlets'][0]
        assert o['number'] == 1
        assert o['name'] == 'Web Server'
        assert o['power_state'] == 'on'
        assert o['available'] is True
        assert o['current_a'] == 0.3
        assert o['active_power_w'] == 30.0

    def test_always_changed_false(self):
        module = make_module()
        with patch('pdu_facts.get_agent') as mga, patch('pdu_facts.pdumodel') as mpm:
            self._setup(mga, mpm)
            pdu_facts.run_module(module)
        assert module.exit_json.call_args[1]['changed'] is False

    def test_connection_error(self):
        module = make_module()
        with patch('pdu_facts.get_agent', side_effect=Exception('timeout')):
            pdu_facts.run_module(module)
        module.fail_json.assert_called_once()
        assert 'timeout' in module.fail_json.call_args[1]['msg']

    def test_get_metadata_error(self):
        module = make_module()
        with patch('pdu_facts.get_agent') as mga, patch('pdu_facts.pdumodel') as mpm:
            mock_pdu = MagicMock()
            mga.return_value = MagicMock()
            mpm.Pdu.return_value = mock_pdu
            mock_pdu.getMetaData.side_effect = Exception('RPC error')
            pdu_facts.run_module(module)
        module.fail_json.assert_called_once()
