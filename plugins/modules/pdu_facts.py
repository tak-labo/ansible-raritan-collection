DOCUMENTATION = r"""
---
module: pdu_facts
short_description: Collect facts from a Raritan PDU
description:
  - Gathers identification, configuration, and sensor data from a Raritan PDU.
  - Returns results as Ansible facts under the C(pdu) key.
  - Always returns C(changed=false).
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
"""

EXAMPLES = r"""
- name: Collect PDU facts
  raritan.xerus.pdu_facts:
    host: 192.168.1.100
    username: admin
    password: secret
    validate_certs: false

- name: Show PDU model
  ansible.builtin.debug:
    msg: "Model: {{ ansible_facts.pdu.model }}, Firmware: {{ ansible_facts.pdu.firmware }}"
"""

RETURN = r"""
ansible_facts:
  description: PDU facts collected from the device.
  returned: always
  type: dict
  contains:
    pdu:
      description: Dictionary of PDU data.
      type: dict
      contains:
        model:
          description: PDU model name.
          type: str
        serial_number:
          description: PDU serial number.
          type: str
        part_number:
          description: PDU part number.
          type: str
        firmware:
          description: Firmware version string.
          type: str
        hardware:
          description: Hardware revision string.
          type: str
        mac_address:
          description: MAC address of the PDU.
          type: str
        name:
          description: PDU name configured on the device.
          type: str
        cycle_delay:
          description: Outlet power cycle delay in seconds.
          type: int
        startup_state:
          description: Power state on PDU startup (on/off/last_known).
          type: str
        inlets:
          description: List of inlet sensor readings.
          type: list
          elements: dict
          contains:
            index:
              description: Zero-based inlet index.
              type: int
            voltage_v:
              description: Input voltage in volts. Null if unavailable.
              type: float
            current_a:
              description: Input current in amperes. Null if unavailable.
              type: float
            active_power_w:
              description: Active power in watts. Null if unavailable.
              type: float
            apparent_power_va:
              description: Apparent power in volt-amperes. Null if unavailable.
              type: float
            power_factor:
              description: Power factor (0.0–1.0). Null if unavailable.
              type: float
            line_frequency_hz:
              description: Line frequency in hertz. Null if unavailable.
              type: float
            active_energy_wh:
              description: Accumulated active energy in watt-hours. Null if unavailable.
              type: float
        outlets:
          description: List of outlet states and sensor readings.
          type: list
          elements: dict
          contains:
            number:
              description: Outlet number (1-based).
              type: int
            name:
              description: Outlet label.
              type: str
            power_state:
              description: Current power state (on/off/unknown).
              type: str
            available:
              description: Whether the outlet is available.
              type: bool
            current_a:
              description: Outlet current in amperes. Null if unavailable.
              type: float
            active_power_w:
              description: Outlet active power in watts. Null if unavailable.
              type: float
"""

import sys
import os

try:
    from ansible.module_utils.basic import AnsibleModule
    from ansible_collections.raritan.xerus.plugins.module_utils.raritan_client import get_agent, RaritanClientError
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../module_utils'))
    from raritan_client import get_agent, RaritanClientError

from raritan.rpc import pdumodel

PDU_TARGET = '/model/pdu/0'

_STARTUP_STATE_MAP = {
    'SS_ON': 'on',
    'SS_OFF': 'off',
    'SS_LASTKNOWN': 'last_known',
}

_POWER_STATE_MAP = {
    'PS_ON': 'on',
    'PS_OFF': 'off',
}


def _enum_name(enum_val):
    return str(enum_val).rsplit('.', 1)[-1]


def _read(sensor):
    try:
        r = sensor.getReading()
        return round(r.value, 4) if r.valid else None
    except Exception:
        return None


def _collect_inlet(inlet, idx):
    try:
        s = inlet.getSensors()
    except Exception:
        return {'index': idx}
    return {
        'index': idx,
        'voltage_v': _read(s.voltage),
        'current_a': _read(s.current),
        'active_power_w': _read(s.activePower),
        'apparent_power_va': _read(s.apparentPower),
        'power_factor': _read(s.powerFactor),
        'line_frequency_hz': _read(s.lineFrequency),
        'active_energy_wh': _read(s.activeEnergy),
    }


def _collect_outlet(outlet, number):
    result = {'number': number, 'name': '', 'power_state': 'unknown', 'available': False,
              'current_a': None, 'active_power_w': None}
    try:
        settings = outlet.getSettings()
        result['name'] = settings.name or ''
    except Exception:
        pass
    try:
        state = outlet.getState()
        result['available'] = state.available
        result['power_state'] = _POWER_STATE_MAP.get(_enum_name(state.powerState), 'unknown')
    except Exception:
        pass
    try:
        s = outlet.getSensors()
        result['current_a'] = _read(s.current)
        result['active_power_w'] = _read(s.activePower)
    except Exception:
        pass
    return result


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

    pdu = pdumodel.Pdu(PDU_TARGET, agent)

    try:
        meta = pdu.getMetaData()
        settings = pdu.getSettings()
    except Exception as e:
        module.fail_json(msg='Failed to get PDU info: {}'.format(e))
        return

    np = meta.nameplate
    facts = {
        'model': np.model or '',
        'serial_number': np.serialNumber or '',
        'part_number': np.partNumber or '',
        'firmware': meta.fwRevision or '',
        'hardware': meta.hwRevision or '',
        'mac_address': meta.macAddress or '',
        'name': settings.name or '',
        'cycle_delay': settings.cycleDelay,
        'startup_state': _STARTUP_STATE_MAP.get(_enum_name(settings.startupState), str(settings.startupState)),
        'inlets': [],
        'outlets': [],
    }

    try:
        inlets = pdu.getInlets()
        facts['inlets'] = [_collect_inlet(inlet, i) for i, inlet in enumerate(inlets)]
    except Exception:
        pass

    try:
        outlets = pdu.getOutlets()
        facts['outlets'] = [_collect_outlet(outlet, i + 1) for i, outlet in enumerate(outlets)]
    except Exception:
        pass

    module.exit_json(changed=False, ansible_facts={'pdu': facts})


def main():
    module = AnsibleModule(
        argument_spec=dict(
            host=dict(type='str', required=True),
            username=dict(type='str', required=True),
            password=dict(type='str', required=True, no_log=True),
            validate_certs=dict(type='bool', default=True),
        ),
        supports_check_mode=True,
    )
    run_module(module)


if __name__ == '__main__':
    main()
