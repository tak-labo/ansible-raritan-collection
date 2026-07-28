# Raritan SDK: Outlet Sensors Reference

Reference notes on `raritan.rpc.pdumodel.Outlet.Sensors` and the underlying
`raritan.rpc.sensors.NumericSensor` API, gathered while implementing
`outlet_config`'s threshold support. Companion to
`docs/raritan-sdk-inlet-sensors.md` — see that doc for the shared
`NumericSensor` API details (`getThresholds()`/`setThresholds()`, the
`Thresholds` struct fields, and `setThresholds()` return codes), which are
identical for outlets and inlets. SDK location:
`.venv/lib/python3.14/site-packages/raritan/rpc/`.

## All sensors on `Outlet.Sensors`

`Outlet.Sensors` (`pdumodel/__init__.py`) exposes 18 `NumericSensor`
attributes plus one `StateSensor`. All 18 `NumericSensor` entries support
`getThresholds()`/`setThresholds()` and are usable with `outlet_config`'s
`sensor` param (see `SENSOR_MAP` in `plugins/modules/outlet_config.py`).

| `sensor` param (snake_case) | SDK attribute (camelCase) | SDK type |
|---|---|---|
| `voltage` | `voltage` | `NumericSensor` |
| `current` | `current` | `NumericSensor` |
| `peak_current` | `peakCurrent` | `NumericSensor` |
| `maximum_current` | `maximumCurrent` | `NumericSensor` |
| `unbalanced_current` | `unbalancedCurrent` | `NumericSensor` |
| `active_power` | `activePower` | `NumericSensor` |
| `reactive_power` | `reactivePower` | `NumericSensor` |
| `apparent_power` | `apparentPower` | `NumericSensor` |
| `power_factor` | `powerFactor` | `NumericSensor` |
| `displacement_power_factor` | `displacementPowerFactor` | `NumericSensor` |
| `active_energy` | `activeEnergy` | `NumericSensor` |
| `apparent_energy` | `apparentEnergy` | `NumericSensor` |
| `phase_angle` | `phaseAngle` | `NumericSensor` |
| `line_frequency` | `lineFrequency` | `NumericSensor` |
| `crest_factor` | `crestFactor` | `NumericSensor` |
| `voltage_thd` | `voltageThd` | `NumericSensor` |
| `current_thd` | `currentThd` | `NumericSensor` |
| `inrush_current` | `inrushCurrent` | `NumericSensor` |
| — | `outletState` | `StateSensor` (no thresholds) |

## Differences from `Inlet.Sensors`

Outlets and inlets share most sensor names, but the sets aren't identical
(21 `NumericSensor` on inlets vs. 18 on outlets):

- **Outlet-only**: `maximum_current`, `inrush_current` — outlet-specific
  protection/monitoring sensors with no inlet equivalent.
- **Inlet-only** (not present on `Outlet.Sensors` at all): the three-phase
  imbalance sensors (`unbalanced_line_line_current`, `unbalanced_voltage`,
  `unbalanced_line_line_voltage`) and the residual-current sensors
  (`residual_current`, `residual_ac_current`, `residual_dc_current`) — these
  only make sense at the inlet (whole-circuit) level, not per-outlet.
- **Shared but named differently in practice**: `unbalanced_current` exists
  on both, but inlets additionally split it into line-line/voltage variants
  that outlets don't have.

Because the two sensor sets differ, `outlet_config.SENSOR_MAP` and
`inlet_config.SENSOR_MAP` are maintained as separate dicts rather than a
shared one — keep this in mind if you're tempted to unify them.

## Current module coverage vs. SDK capability

- `outlet_config`'s `sensor` param already accepts all 18 `NumericSensor`
  names above — full write coverage exists today.
- `pdu_facts`'s `_collect_outlet()` (`plugins/modules/pdu_facts.py`) only
  reads `current` and `active_power` **readings** (via `_read()`) and does
  **not** call `_read_thresholds()` for any outlet sensor — unlike inlets,
  outlet facts currently expose no threshold data at all. Since
  `_read_thresholds()` is generic over any `NumericSensor`, adding outlet
  threshold reporting (e.g. for `current`/`active_power`, mirroring the 4
  inlet sensors already covered) is a matter of adding
  `_read_thresholds(s.<sensor>)` calls in `_collect_outlet()` — not a
  structural change.
