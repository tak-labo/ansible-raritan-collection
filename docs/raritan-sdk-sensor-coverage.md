# Raritan SDK: Sensor Coverage Overview

Full landscape of `NumericSensor`-bearing (threshold-capable) objects in the
`raritan` SDK, and how much of it this collection currently implements.
Gathered while implementing `inlet_config`/`outlet_config` threshold support
and scoping what else could follow the same pattern. See
`docs/raritan-sdk-inlet-sensors.md` and `docs/raritan-sdk-outlet-sensors.md`
for the per-sensor field tables and the shared `NumericSensor` API details
(`getThresholds()`/`setThresholds()`, the `Thresholds` struct, return codes).
SDK location: `.venv/lib/python3.14/site-packages/raritan/rpc/`.

## Coverage at a glance

| Category | SDK class | Thresholds? | Module coverage |
|---|---|:---:|---|
| Inlet | `pdumodel.Inlet.Sensors` (21 `NumericSensor`) | ✅ | ✅ `inlet_config` (set/unset), `pdu_facts` (read, 4/21 sensors) |
| Outlet | `pdumodel.Outlet.Sensors` (18 `NumericSensor`) | ✅ | ✅ `outlet_config` (set/unset), `pdu_facts` (read, 0/18 sensors) |
| PDU body (aggregate power) | `pdumodel.Pdu.Sensors` (4 `NumericSensor`) | ✅ | ❌ not implemented |
| Circuit | `pdumodel.Circuit.Sensors` (11 `NumericSensor`) | ✅ | ❌ not implemented |
| Circuit breaker / OCP | `pdumodel.OverCurrentProtector.Sensors` (16 `NumericSensor` + 3 `StateSensor`) | ✅ | ❌ not implemented |
| Outlet group | `pdumodel.OutletGroup.Sensors` | ✅ | ❌ not implemented |
| External power meter / panel | `pdumodel.PowerMeter.Sensors` (13 `NumericSensor`; `Panel` inherits this) | ✅ | ❌ not implemented |
| Transfer switch (ATS) | `pdumodel.TransferSwitch.Sensors` (1 `NumericSensor` + `StateSensor`s) | ✅ | ❌ not implemented |
| Type-B residual current sensor | `pdumodel.TypeBResidualCurrentNumericSensor` | ✅ | ❌ not implemented |
| Voltage quality (dip/swell) sensor | `pdumodel.VoltageMonitoringSensor` (own `DipSwellThresholds`) | ✅ | ❌ not implemented |
| External peripheral (DPX/DX2/DX3 temp, humidity, airflow, etc.) | `peripheral.Device.device` (runtime-typed `sensors.NumericSensor`) | ✅ | ❌ not implemented |
| Gateway custom sensors (Modbus/SNMP) | `peripheral.GatewaySensorManager.NumericSensorClass` | ✅ | ❌ not implemented |
| PDU power-supply redundancy status | `pdumodel.Pdu.Sensors.powerSupplyStatus` | ❌ (`StateSensor`) | n/a — no thresholds to manage |
| OCP trip / residual-current status | `pdumodel.OverCurrentProtector.Sensors` (`trip`, `residualCurrentStatus`) | ❌ (`StateSensor`) | n/a |
| Transfer switch bypass/source status | `pdumodel.TransferSwitch.Sensors` (non-`sourceVoltagePhaseSyncAngle` fields) | ❌ (`StateSensor`) | n/a |
| Server monitoring (ping) | `servermon.ServerMonitor` | ❌ (no sensor classes at all) | n/a |

**Threshold-capable categories implemented: 2 / 12.**

## Notes

- "Thresholds?" reflects whether the SDK class *can* carry threshold data
  (i.e. is a `NumericSensor` or subclass — `AccumulatingNumericSensor` for
  energy counters also qualifies). It doesn't mean every module using that
  class exposes the thresholds; see the Module coverage column for that.
- `pdu_facts`'s `_read_thresholds()` helper (`plugins/modules/pdu_facts.py`)
  is generic over any `NumericSensor`, so extending read coverage to any
  row above is a matter of calling it with the right sensor object — not a
  structural change. Writing (`setThresholds()`) requires a `sensor`-style
  param and `SENSOR_MAP` per new resource type, following the
  `inlet_config`/`outlet_config` pattern.
- Rows marked "n/a" have no thresholds to manage at all (pure state/status
  sensors) — there is nothing to add for those beyond exposing the state
  itself as a fact, which is a separate (non-threshold) feature.
- If adding a new module for one of the "not implemented" rows, follow the
  `inlet_config`/`outlet_config` shape: a `SENSOR_MAP` (snake_case param →
  SDK camelCase attribute) scoped to that resource's own sensor set — do
  not try to share one `SENSOR_MAP` across resource types, since the sets
  differ (see `docs/raritan-sdk-outlet-sensors.md`'s "Differences from
  `Inlet.Sensors`" section for a concrete example of why).
