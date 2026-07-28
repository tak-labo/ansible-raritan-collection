# Raritan SDK: Inlet Sensors Reference

Reference notes on `raritan.rpc.pdumodel.Inlet.Sensors` and the underlying
`raritan.rpc.sensors.NumericSensor` API, gathered while implementing
`inlet_config`'s threshold support and `pdu_facts`'s threshold reporting.
SDK location: `.venv/lib/python3.14/site-packages/raritan/rpc/`.

## All sensors on `Inlet.Sensors`

`Inlet.Sensors` (`pdumodel/__init__.py`) exposes the following attributes.
The 21 marked `NumericSensor` all support `getThresholds()`/`setThresholds()`
and are usable with `inlet_config`'s `sensor` param (see `SENSOR_MAP` in
`plugins/modules/inlet_config.py`) and with `pdu_facts`'s `_read_thresholds()`
helper. `voltageThd`/`currentThd` etc. included.

| `sensor` param (snake_case) | SDK attribute (camelCase) | SDK type |
|---|---|---|
| `voltage` | `voltage` | `NumericSensor` |
| `current` | `current` | `NumericSensor` |
| `peak_current` | `peakCurrent` | `NumericSensor` |
| `residual_current` | `residualCurrent` | `NumericSensor` |
| `residual_ac_current` | `residualACCurrent` | `NumericSensor` |
| `residual_dc_current` | `residualDCCurrent` | `NumericSensor` |
| `active_power` | `activePower` | `NumericSensor` |
| `reactive_power` | `reactivePower` | `NumericSensor` |
| `apparent_power` | `apparentPower` | `NumericSensor` |
| `power_factor` | `powerFactor` | `NumericSensor` |
| `displacement_power_factor` | `displacementPowerFactor` | `NumericSensor` |
| `active_energy` | `activeEnergy` | `NumericSensor` |
| `apparent_energy` | `apparentEnergy` | `NumericSensor` |
| `unbalanced_current` | `unbalancedCurrent` | `NumericSensor` |
| `unbalanced_line_line_current` | `unbalancedLineLineCurrent` | `NumericSensor` |
| `unbalanced_voltage` | `unbalancedVoltage` | `NumericSensor` |
| `unbalanced_line_line_voltage` | `unbalancedLineLineVoltage` | `NumericSensor` |
| `line_frequency` | `lineFrequency` | `NumericSensor` |
| `phase_angle` | `phaseAngle` | `NumericSensor` |
| `crest_factor` | `crestFactor` | `NumericSensor` |
| `voltage_thd` | `voltageThd` | `NumericSensor` |
| `current_thd` | `currentThd` | `NumericSensor` |
| — | `powerQuality` | `StateSensor` (no thresholds) |
| — | `surgeProtectorStatus` | `StateSensor` (no thresholds) |
| — | `residualCurrentStatus` | `ResidualCurrentStateSensor` (no thresholds) |

The last three are not in `SENSOR_MAP` — `StateSensor`/`ResidualCurrentStateSensor`
have no `getThresholds()`/`setThresholds()`, so they don't fit the threshold
pattern at all.

## `NumericSensor` API (`raritan/rpc/sensors/__init__.py`)

```
getMetaData()          # NumericSensor.MetaData (includes thresholdCaps, range)
getDefaultThresholds() # NumericSensor.Thresholds — factory defaults
getThresholds()        # NumericSensor.Thresholds — current settings
setThresholds(t)       # takes NumericSensor.Thresholds, returns int rc
getReading()           # NumericSensor.Reading (.value, .valid)
getMinMax() / resetMinMax()
```

`setThresholds()` return codes (class constants on `NumericSensor`):
- `0` — OK
- `THRESHOLD_OUT_OF_RANGE = 1` — value outside the sensor's supported range
- `THRESHOLD_INVALID = 2` — constraint violation (e.g. `lowerWarning > upperWarning`)
- `THRESHOLD_NOT_SUPPORTED = 3` — this threshold kind isn't supported by the sensor

### `Thresholds` struct fields

| Field | Type | Meaning |
|---|---|---|
| `upperCriticalActive` | bool | Whether the upper-critical threshold is enabled |
| `upperCritical` | double | Upper critical threshold value |
| `upperWarningActive` | bool | Whether the upper-warning threshold is enabled |
| `upperWarning` | double | Upper warning threshold value |
| `lowerWarningActive` | bool | Whether the lower-warning threshold is enabled |
| `lowerWarning` | double | Lower warning threshold value |
| `lowerCriticalActive` | bool | Whether the lower-critical threshold is enabled |
| `lowerCritical` | double | Lower critical threshold value |
| `assertionTimeout` | int | Assertion delay, in samples |
| `deassertionHysteresis` | double | Hysteresis applied before de-asserting |

`inlet_config` and `pdu_facts` only use the four `*Active`/value pairs;
`assertionTimeout`/`deassertionHysteresis` are not currently exposed by
either module.

`NumericSensor.MetaData.thresholdCaps` (`ThresholdCapabilities` struct) has
`hasUpperCritical`/`hasUpperWarning`/`hasLowerWarning`/`hasLowerCritical` bools
indicating which threshold kinds a given sensor actually supports — useful for
validating before calling `setThresholds()`, though neither module currently
checks this proactively (they rely on the `rc` returned by `setThresholds()`).

## Current module coverage vs. SDK capability

- `inlet_config`'s `sensor` param already accepts all 21 `NumericSensor`
  names above — full write coverage exists today.
- `pdu_facts`'s `_collect_inlet()` (`plugins/modules/pdu_facts.py`) only
  calls `_read_thresholds()` for 4 of the 21 (`voltage`, `current`,
  `active_power`, `apparent_power`), chosen as the most commonly monitored.
  Extending to the rest is a matter of adding more
  `_read_thresholds(s.<sensor>)` calls in `_collect_inlet()` — not a
  structural change, since `_read_thresholds()` is already generic over any
  `NumericSensor`.
