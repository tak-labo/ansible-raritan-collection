# Raritan SDK: Module Coverage by Category

Full inventory of `raritan.rpc` subpackages (`.venv/lib/python3.14/site-packages/raritan/rpc/`),
grouped by functional area, cross-referenced against what this collection's
`plugins/modules/` actually imports today. For the sensor/threshold-specific
landscape (a cross-cutting concern that spans several of the categories
below), see `docs/raritan-sdk-sensor-coverage.md`,
`docs/raritan-sdk-inlet-sensors.md`, and `docs/raritan-sdk-outlet-sensors.md`
instead — this doc covers everything else.

"Implemented" below means a current module imports that SDK subpackage
**and** exercises the relevant class — not just that the package exists.
Several packages are imported but only partially used (e.g. `net` only for
DNS, `devsettings` only for SNMP); those are marked "partial".

## Coverage at a glance

**10 of ~38 subpackages touched, 4 of those only partially.**

| Category | Subpackages | Status |
|---|---|---|
| PDU hardware model | `pdumodel` | 🟡 partial |
| Network & connectivity | `net`, `cascading`, `sx`, `serial`, `modbus` | 🟡 partial (`net` only) |
| Auth & security | `auth`, `security`, `cert`, `usermgmt` | 🟡 partial (`usermgmt` only) |
| Notifications & events | `event`, `devsettings` (Smtp/Snmp/etc.), `logging` | 🟡 partial (`event` + SNMP only) |
| System & firmware | `sys`, `firmware`, `bulkcfg`, `bulkrpc`, `rawcfg`, `cfg`, `production`, `test` | ❌ none |
| Peripherals & physical I/O | `peripheral`, `portsmodel`, `usb`, `smartcard`, `smartlock`, `webcam`, `zigbee`, `hmi`, `display`, `dsam`, `assetmgrmodel` | ❌ none |
| Monitoring & diagnostics | `diag`, `fitness`, `res_mon`, `session`, `servermon`, `tfw` | ❌ none |
| Automation/scripting | `luaservice` | ❌ none |
| Date/time | `datetime` | ✅ implemented |
| Sensor primitives | `sensors` | ✅ implemented (internal, via `pdumodel`) |

## By category

### PDU hardware model — 🟡 partial

| Package | Representative class | Purpose | Shape |
|---|---|---|---|
| `pdumodel` | `Pdu`, `Inlet`, `Outlet`, `Circuit`, `OverCurrentProtector`, `Controller` | PDU body, inlets, outlets, circuits, breakers | facts-heavy + Settings |

Implemented: `Pdu` (name/cycle-delay/startup-state via `pdu_config`), `Inlet`
(name + thresholds via `inlet_config`), `Outlet` (name/power-state/thresholds
via `outlet_config`), plus read-only facts for all three via `pdu_facts`.
**Not implemented**: `Circuit`, `OverCurrentProtector` (breakers),
`OutletGroup`, `PowerMeter`/`Panel`, `TransferSwitch` — see
`docs/raritan-sdk-sensor-coverage.md` for their sensor/threshold angle
specifically.

### Network & connectivity — 🟡 partial (`net` only, and only DNS within it)

| Package | Representative class | Purpose | Shape |
|---|---|---|---|
| `net` | `Net`, `InterfaceSettings`, `Diagnostics` | IP/DNS/interface config, ping/traceroute | Settings (+ diag = action) |
| `cascading` | `CascadeManager` | Multi-PDU cascade/daisy-chain config | Settings + facts |
| `sx` | `Sx` | Serial console server function | Settings |
| `serial` | `SerialPort`, `AnalogModem`, `GsmModem` | Serial port / modem config | Settings |
| `modbus` | `GatewayMgr` | Modbus gateway config | Settings |

`dns_config` only touches `net.Net`'s DNS settings — `InterfaceSettings`
(NIC/VLAN/link mode) and `Diagnostics` (ping/traceroute) on the same
`net` package are untouched. Everything else in this category is
unimplemented.

### Auth & security — 🟡 partial (`usermgmt` only)

| Package | Representative class | Purpose | Shape |
|---|---|---|---|
| `usermgmt` | `User`, `Role`, `RoleManager` | User accounts, roles, permissions | Settings/Resource |
| `auth` | `AuthManager`, `LdapManager`, `RadiusManager` | Auth order, LDAP/RADIUS/TACACS+ | Settings |
| `security` | `Security`, `RoleAccessControl`, `PasswordSettings` | Firewall, password policy, SSH, RSA | Settings |
| `cert` | `ServerSSLCert` | SSL certificate management | Settings + action (CSR/import) |

`user_account` covers `usermgmt` (accounts + SNMPv3, no roles). `auth`,
`security`, and `cert` are entirely unimplemented — see the earlier
recommendation to prioritize `security_config` and `auth_config`.

### Notifications & events — 🟡 partial (`event` + SNMP only)

| Package | Representative class | Purpose | Shape |
|---|---|---|---|
| `event` | `Engine`, `AlarmManager`, `Service` | Event engine, alarms, actions | Settings + facts |
| `devsettings` | `Smtp`, `Snmp`, `Modbus`, `Redfish`, `Zeroconf`, `Crestron` | Per-subsystem service settings | Settings |
| `logging` | `EventLog`, `DebugLog`, `WlanLog` | Log retrieval/clearing | facts (read-only) |

`event_rule`/`syslog_action`/`snmp_trap_action` cover `event`. `snmp_config`
only touches `devsettings.Snmp` — `Smtp` (email notifications), `Modbus`,
`Redfish`, `Zeroconf`, `Crestron` in the same package are untouched.
`logging` is unimplemented (read-only, so it'd be a `pdu_facts`-style
addition, not a config module).

### System & firmware — ❌ none implemented

| Package | Representative class | Purpose | Shape |
|---|---|---|---|
| `sys` | `System` | Reboot, factory reset | action |
| `firmware` | `Firmware`, `FirmwareUpdateStatus` | Firmware update + progress | action |
| `bulkcfg` | `BulkConfiguration` | Bulk XML config apply | action |
| `bulkrpc` | `BulkRequest` | Batch RPC execution | action |
| `rawcfg` | `RawConfiguration` | Raw XML config read/write | action |
| `cfg` | `Cfg` | Generic key-value config | Settings |
| `production` | `Production` | Manufacturing info | facts (read-only) |
| `test` | `Display`, `Unit` | Factory self-test (LEDs, beeper) | action — out of scope, not an operational feature |

Mostly action/one-shot shaped, which doesn't fit the idempotent
`getSettings`/`setSettings` pattern well — lower priority for this
collection except perhaps `sys` (reboot) as a simple action module.

### Peripherals & physical I/O — ❌ none implemented

| Package | Representative class | Purpose | Shape |
|---|---|---|---|
| `peripheral` | `DeviceSlot`, `DeviceManager`, `SensorHub` | External DPX/DX2/DX3 sensors | facts + Settings |
| `portsmodel` | `Port`, `PortFuse` | Port naming/mode, fuse status | facts + Settings |
| `usb` | `Usb`, `UsbDevice` | USB device info | facts |
| `smartcard` | `CardReader`, `CardReaderManager` | Smart card reader | facts |
| `smartlock` | `DoorAccessControl`, `Keypad` | Door lock / keypad control | Settings + action |
| `webcam` | `Webcam`, `WebcamManager` | Webcam config + capture | Settings + facts |
| `zigbee` | `ZigbeeDevice`, `ZigbeeManager` | Zigbee device management | facts + Settings |
| `hmi` | `ExternalBeeper`, `InternalBeeper` | Beeper control | Settings + action |
| `display` | `DisplayControl` | Front-panel LED display | Settings + action |
| `dsam` | `DsamManager`, `DsamDevice` | DSAM sensor module management | facts (+ some Settings) |
| `assetmgrmodel` | `AssetStrip`, `AssetStripConfig` | Asset tag strip (rack tracking) | Settings + facts |

`peripheral.DeviceSlot` is the most natural next step given the existing
sensor-module work (`inlet_config`/`outlet_config`) — external temperature/
humidity sensors follow the same `NumericSensor` threshold pattern (see
`docs/raritan-sdk-sensor-coverage.md`). The rest are niche hardware options
(door locks, smart cards, Zigbee, webcams) — implement only if a specific
deployment needs them.

### Monitoring & diagnostics — ❌ none implemented

| Package | Representative class | Purpose | Shape |
|---|---|---|---|
| `diag` | `DiagLogSettings` | Diagnostic logging config | Settings |
| `fitness` | `Fitness`, `HardwareHealth` | Hardware health monitoring | facts (read-only) |
| `res_mon` | `ResMon` | Resource (CPU/memory) monitoring | facts (read-only) |
| `session` | `SessionManager` | Active session list/termination | facts + action |
| `servermon` | `ServerMonitor` | Server ping monitoring | Settings + facts |
| `tfw` | `ScannerCtrl`, `CoreCtrl` | Transfer switch scanner/core control | Settings + facts |

Mostly read-only facts candidates (`fitness`, `res_mon`) — natural
extensions to `pdu_facts` rather than new config modules.

### Automation/scripting — ❌ none implemented

| Package | Representative class | Purpose | Shape |
|---|---|---|---|
| `luaservice` | `Manager` | Custom Lua script execution | Settings + action |

Niche — only relevant if a deployment relies on custom Lua automation on
the PDU itself.

### Date/time — ✅ implemented

| Package | Representative class | Purpose | Shape |
|---|---|---|---|
| `datetime` | `DateTime` | NTP servers, timezone | Settings |

Fully covered by `datetime_config`.

## Where to look next

Per the earlier analysis (see conversation / commit history), the top
candidates for new modules, in priority order, are: `security_config`
(`security.Security`), `auth_config` (`auth.*Manager`), `smtp_config`
(`devsettings.Smtp`), `network_interface_config` (`net.InterfaceSettings`/
`net.Services`), and `cert_config` (`cert.ServerSSLCert`) — all Settings-
or Resource-shaped and high real-world value. `peripheral.DeviceSlot` is
the natural next step for sensor-pattern extension specifically.
