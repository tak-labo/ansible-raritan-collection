DOCUMENTATION = r"""
---
module: inlet_config
short_description: Configure a Raritan PDU inlet name
description:
  - Manages the inlet name. Settings management is idempotent.
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
  inlet:
    description: Inlet number (1-based).
    required: true
    type: int
  name:
    description: Inlet label name.
    type: str
  sensor:
    description: Sensor to configure thresholds for. Required when any threshold option is set.
    type: str
    choices:
      - voltage
      - current
      - peak_current
      - residual_current
      - residual_ac_current
      - residual_dc_current
      - active_power
      - reactive_power
      - apparent_power
      - power_factor
      - displacement_power_factor
      - active_energy
      - apparent_energy
      - unbalanced_current
      - unbalanced_line_line_current
      - unbalanced_voltage
      - unbalanced_line_line_voltage
      - line_frequency
      - phase_angle
      - crest_factor
      - voltage_thd
      - current_thd
  upper_critical:
    description: Upper critical threshold value. Setting it also enables it.
    type: float
  upper_warning:
    description: Upper warning threshold value. Setting it also enables it.
    type: float
  lower_warning:
    description: Lower warning threshold value. Setting it also enables it.
    type: float
  lower_critical:
    description: Lower critical threshold value. Setting it also enables it.
    type: float
  unset_thresholds:
    description: >-
      Threshold fields to disable (clears the corresponding *Active flag without
      changing the stored value). Requires C(sensor) when set. A field must not
      appear here and as a value option at the same time.
    type: list
    elements: str
    choices:
      - upper_critical
      - upper_warning
      - lower_warning
      - lower_critical
"""

EXAMPLES = r"""
- name: Rename inlet 1
  taklabo.raritan_xerus.inlet_config:
    host: 192.168.1.100
    username: admin
    password: secret
    validate_certs: false
    inlet: 1
    name: "Main Feed"

- name: Set voltage upper thresholds on inlet 1
  taklabo.raritan_xerus.inlet_config:
    host: 192.168.1.100
    username: admin
    password: secret
    validate_certs: false
    inlet: 1
    sensor: voltage
    upper_warning: 240.0
    upper_critical: 250.0

- name: Disable voltage upper_warning threshold on inlet 1
  taklabo.raritan_xerus.inlet_config:
    host: 192.168.1.100
    username: admin
    password: secret
    validate_certs: false
    inlet: 1
    sensor: voltage
    unset_thresholds:
      - upper_warning
"""

RETURN = r"""# """

import sys
import os

try:
    from ansible.module_utils.basic import AnsibleModule
    from ansible_collections.taklabo.raritan_xerus.plugins.module_utils.raritan_client import get_agent, RaritanClientError
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../module_utils'))
    from raritan_client import get_agent, RaritanClientError

from raritan.rpc import pdumodel

PDU_TARGET = '/model/pdu/0'

SENSOR_MAP = {
    'voltage': 'voltage',
    'current': 'current',
    'peak_current': 'peakCurrent',
    'residual_current': 'residualCurrent',
    'residual_ac_current': 'residualACCurrent',
    'residual_dc_current': 'residualDCCurrent',
    'active_power': 'activePower',
    'reactive_power': 'reactivePower',
    'apparent_power': 'apparentPower',
    'power_factor': 'powerFactor',
    'displacement_power_factor': 'displacementPowerFactor',
    'active_energy': 'activeEnergy',
    'apparent_energy': 'apparentEnergy',
    'unbalanced_current': 'unbalancedCurrent',
    'unbalanced_line_line_current': 'unbalancedLineLineCurrent',
    'unbalanced_voltage': 'unbalancedVoltage',
    'unbalanced_line_line_voltage': 'unbalancedLineLineVoltage',
    'line_frequency': 'lineFrequency',
    'phase_angle': 'phaseAngle',
    'crest_factor': 'crestFactor',
    'voltage_thd': 'voltageThd',
    'current_thd': 'currentThd',
}

THRESHOLD_FIELDS = {
    'upper_critical': ('upperCritical', 'upperCriticalActive'),
    'upper_warning': ('upperWarning', 'upperWarningActive'),
    'lower_warning': ('lowerWarning', 'lowerWarningActive'),
    'lower_critical': ('lowerCritical', 'lowerCriticalActive'),
}


def run_module(module):
    p = module.params
    inlet_num = p['inlet']

    unset_thresholds = p.get('unset_thresholds') or []

    overlap = [f for f in unset_thresholds if p.get(f) is not None]
    if overlap:
        module.fail_json(msg='{} cannot be set and unset at the same time'.format(', '.join(overlap)))
        return

    threshold_params_given = any(p.get(f) is not None for f in THRESHOLD_FIELDS) or bool(unset_thresholds)
    if threshold_params_given and p.get('sensor') is None:
        module.fail_json(msg='sensor is required when a threshold option is set')
        return

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
        inlets = pdu.getInlets()
    except Exception as e:
        module.fail_json(msg='Failed to get inlets: {}'.format(e))
        return

    idx = inlet_num - 1
    if idx < 0 or idx >= len(inlets):
        module.fail_json(msg='Inlet {} not found (PDU has {} inlets)'.format(
            inlet_num, len(inlets)))
        return

    inlet = inlets[idx]

    try:
        settings = inlet.getSettings()
    except Exception as e:
        module.fail_json(msg='Failed to get inlet settings: {}'.format(e))
        return

    settings_changed = False

    if p.get('name') is not None and settings.name != p['name']:
        settings.name = p['name']
        settings_changed = True

    if settings_changed and not module.check_mode:
        try:
            inlet.setSettings(settings)
        except Exception as e:
            module.fail_json(msg='Failed to set inlet settings: {}'.format(e))
            return

    thresholds_changed = False

    if p.get('sensor') is not None:
        try:
            sensors = inlet.getSensors()
            sensor = getattr(sensors, SENSOR_MAP[p['sensor']])
        except Exception as e:
            module.fail_json(msg='Failed to get sensor {}: {}'.format(p['sensor'], e))
            return

        try:
            thresholds = sensor.getThresholds()
        except Exception as e:
            module.fail_json(msg='Failed to get thresholds: {}'.format(e))
            return

        for param_name, (value_attr, active_attr) in THRESHOLD_FIELDS.items():
            value = p.get(param_name)
            if value is not None and getattr(thresholds, value_attr) != value:
                setattr(thresholds, value_attr, value)
                setattr(thresholds, active_attr, True)
                thresholds_changed = True
            elif param_name in unset_thresholds and getattr(thresholds, active_attr):
                setattr(thresholds, active_attr, False)
                thresholds_changed = True

        if thresholds_changed and not module.check_mode:
            try:
                rc = sensor.setThresholds(thresholds)
            except Exception as e:
                module.fail_json(msg='Failed to set thresholds: {}'.format(e))
                return
            if rc != 0:
                module.fail_json(msg='Failed to set thresholds: rc={}'.format(rc))
                return

    module.exit_json(changed=settings_changed or thresholds_changed)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            host=dict(type='str', required=True),
            username=dict(type='str', required=True),
            password=dict(type='str', required=True, no_log=True),
            validate_certs=dict(type='bool', default=True),
            inlet=dict(type='int', required=True),
            name=dict(type='str'),
            sensor=dict(type='str', choices=list(SENSOR_MAP.keys())),
            upper_critical=dict(type='float'),
            upper_warning=dict(type='float'),
            lower_warning=dict(type='float'),
            lower_critical=dict(type='float'),
            unset_thresholds=dict(type='list', elements='str', choices=list(THRESHOLD_FIELDS.keys())),
        ),
        supports_check_mode=True,
    )
    run_module(module)


if __name__ == '__main__':
    main()
