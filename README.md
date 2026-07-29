# taklabo.raritan_xerus

Ansible Collection for managing Raritan PDU and other devices.

## Requirements

- Python >= 3.9
- `raritan` pip package == 4.3.13.52458 (pinned to match tested firmware; see below)
- Raritan PDU firmware (tested with 4.3.13.5-52458 on PX3-5138JR)

## Installation

    ansible-galaxy collection install taklabo.raritan_xerus

Install Python dependency:

    pip install raritan==4.3.13.52458

The `raritan` SDK's schema must match your PDU's firmware — a newer SDK
version can declare fields your firmware doesn't return, which crashes
`pdu_facts`/`dns_config` with a `KeyError`. `4.3.13.52458` matches the
firmware build this collection is tested against; if your PDU runs a
different firmware version, pick the matching `raritan` release instead
of defaulting to the latest.

## Modules

| Module | Description |
|---|---|
| `taklabo.raritan_xerus.datetime_config` | Configure NTP servers and timezone |
| `taklabo.raritan_xerus.dns_config` | Configure DNS server addresses, search suffixes, and IPv6 resolver preference |
| `taklabo.raritan_xerus.event_rule` | Manage event engine rules (bind actions to event conditions) |
| `taklabo.raritan_xerus.inlet_config` | Configure individual inlet name and sensor thresholds |
| `taklabo.raritan_xerus.outlet_config` | Configure individual outlets and control power state (on/off/cycle) |
| `taklabo.raritan_xerus.pdu_backup` | Download and save a PDU configuration backup locally |
| `taklabo.raritan_xerus.pdu_config` | Configure PDU-wide settings (name, startup state, cycle delay) |
| `taklabo.raritan_xerus.pdu_facts` | Collect PDU facts (model, firmware, inlet sensors, outlet states) |
| `taklabo.raritan_xerus.snmp_config` | Configure SNMP v2/v3 settings |
| `taklabo.raritan_xerus.snmp_trap_action` | Manage SNMP trap event actions in the PDU event engine |
| `taklabo.raritan_xerus.syslog_action` | Manage syslog event actions in the PDU event engine |
| `taklabo.raritan_xerus.user_account` | Manage PDU user accounts with SNMPv3 settings (create/update/delete) |

All modules support `check_mode`. Most are idempotent; `pdu_facts` is read-only and always returns `changed=false`, and `pdu_backup` is only idempotent when `filename` is set explicitly (see below).

## Module Reference

### datetime_config

| Parameter | Type | Required | Description |
|---|---|---|---|
| `host` | str | yes | PDU hostname or IP address |
| `username` | str | yes | Authentication username |
| `password` | str | yes | Authentication password |
| `validate_certs` | bool | no (default: true) | Validate TLS certificate |
| `timezone` | str | no | Timezone display name (e.g. `"(UTC+09:00) Osaka, Sapporo, Tokyo"`) |
| `protocol` | str | no | Time sync protocol (`ntp` / `static`) |
| `ntp_server1` | str | no | Primary NTP server hostname or IP |
| `ntp_server2` | str | no | Secondary NTP server hostname or IP |

### dns_config

| Parameter | Type | Required | Description |
|---|---|---|---|
| `host` | str | yes | PDU hostname or IP address |
| `username` | str | yes | Authentication username |
| `password` | str | yes | Authentication password |
| `validate_certs` | bool | no (default: true) | Validate TLS certificate |
| `servers` | list[str] | no | DNS server IP addresses |
| `search_suffixes` | list[str] | no | DNS search domain suffixes |
| `prefer_ipv6` | bool | no | Prefer IPv6 DNS resolver |

Server and suffix lists are compared order-insensitively.

### event_rule

| Parameter | Type | Required | Description |
|---|---|---|---|
| `host` | str | yes | PDU hostname or IP address |
| `username` | str | yes | Authentication username |
| `password` | str | yes | Authentication password |
| `validate_certs` | bool | no (default: true) | Validate TLS certificate |
| `name` | str | yes | Rule name (used as idempotency key) |
| `action_names` | list | no | Action names to execute when the rule fires (resolved to IDs automatically) |
| `event_id` | list | no (default: ["**"]) | Event ID pattern list. `["**"]` matches all events |
| `match_type` | str | no (default: both) | When to fire: `asserted` / `deasserted` / `both` |
| `enabled` | bool | no (default: true) | Whether the rule is active |
| `auto_rearm` | bool | no (default: true) | Automatically rearm after firing |
| `state` | str | no (default: present) | `present` to create/update, `absent` to delete |

### inlet_config

| Parameter | Type | Required | Description |
|---|---|---|---|
| `host` | str | yes | PDU hostname or IP address |
| `username` | str | yes | Authentication username |
| `password` | str | yes | Authentication password |
| `validate_certs` | bool | no (default: true) | Validate TLS certificate |
| `inlet` | int | yes | Inlet number (1-based) |
| `name` | str | no | Inlet label |
| `sensor` | str | no | Sensor to configure thresholds for (`voltage`, `current`, `active_power`, etc.). Required when any threshold option is set |
| `upper_critical` | float | no | Upper critical threshold value. Setting it also enables it |
| `upper_warning` | float | no | Upper warning threshold value. Setting it also enables it |
| `lower_warning` | float | no | Lower warning threshold value. Setting it also enables it |
| `lower_critical` | float | no | Lower critical threshold value. Setting it also enables it |
| `unset_thresholds` | list[str] | no | Threshold fields to disable (`upper_critical`/`upper_warning`/`lower_warning`/`lower_critical`). Requires `sensor`. A field can't be set and unset at the same time |

### outlet_config

| Parameter | Type | Required | Description |
|---|---|---|---|
| `host` | str | yes | PDU hostname or IP address |
| `username` | str | yes | Authentication username |
| `password` | str | yes | Authentication password |
| `validate_certs` | bool | no (default: true) | Validate TLS certificate |
| `outlet` | int | yes | Outlet number (1-based) |
| `name` | str | no | Outlet label |
| `state` | str | no (default: unchanged) | Power state (`on` / `off` / `cycle` / `unchanged`) |
| `startup_state` | str | no | Power state on PDU startup (`on` / `off` / `last_known`) |
| `cycle_delay` | int | no | Power cycle delay in seconds |
| `non_critical` | bool | no | Exclude outlet from load shedding |
| `sensor` | str | no | Sensor to configure thresholds for (`voltage`, `current`, `active_power`, etc.). Required when any threshold option is set |
| `upper_critical` | float | no | Upper critical threshold value. Setting it also enables it |
| `upper_warning` | float | no | Upper warning threshold value. Setting it also enables it |
| `lower_warning` | float | no | Lower warning threshold value. Setting it also enables it |
| `lower_critical` | float | no | Lower critical threshold value. Setting it also enables it |
| `unset_thresholds` | list[str] | no | Threshold fields to disable (`upper_critical`/`upper_warning`/`lower_warning`/`lower_critical`). Requires `sensor`. A field can't be set and unset at the same time |

`state: cycle` always reports `changed: true`. Outlet sensors don't include the residual-current/three-phase-imbalance sensors available on inlets (see `SENSOR_MAP` in `plugins/modules/outlet_config.py` for the full list).

### pdu_backup

| Parameter | Type | Required | Description |
|---|---|---|---|
| `host` | str | yes | PDU hostname or IP address |
| `username` | str | yes | Authentication username |
| `password` | str | yes | Authentication password |
| `validate_certs` | bool | no (default: true) | Validate TLS certificate |
| `backup_path` | str | no (default: `./backup`) | Local directory to save the backup file into. Created if missing |
| `filename` | str | no | Backup filename. If omitted, a timestamped filename is generated and every run is treated as a new backup |
| `method` | str | no (default: raw) | `raw` downloads the device's raw config; `bulk` uses the bulk config mechanism in backup mode (supports encryption/filter profiles) |
| `bulk_password` | str | no | Password to encrypt the bulk config file with. Only used when `method=bulk` |
| `bulk_filter_profile` | str | no | Bulk configuration filter profile name. Only used when `method=bulk` |

Unlike other modules, this performs a raw HTTP file download (not JSON-RPC) via the SDK's `rawcfg`/`bulkcfg` module-level functions — there is no `getSettings`/`setSettings` diff step. When `filename` is omitted, a new timestamped file is written on every run and `changed` is always `true` (matching the "backup" behavior of network modules like `ios_config`). When `filename` is set explicitly, the downloaded content is compared byte-for-byte against the existing file and `changed` is `false` when unchanged — useful for fixed-path backups run on a schedule. Restoring a backup (upload) is not implemented yet.

### pdu_config

| Parameter | Type | Required | Description |
|---|---|---|---|
| `host` | str | yes | PDU hostname or IP address |
| `username` | str | yes | Authentication username |
| `password` | str | yes | Authentication password |
| `validate_certs` | bool | no (default: true) | Validate TLS certificate |
| `name` | str | no | PDU name |
| `startup_state` | str | no | Power state on startup (`on` / `off` / `last_known`) |
| `cycle_delay` | int | no | Outlet power cycle delay in seconds |

### pdu_facts

| Parameter | Type | Required | Description |
|---|---|---|---|
| `host` | str | yes | PDU hostname or IP address |
| `username` | str | yes | Authentication username |
| `password` | str | yes | Authentication password |
| `validate_certs` | bool | no (default: true) | Validate TLS certificate |

Returns `ansible_facts.pdu` with the following keys:

| Key | Description |
|---|---|
| `model`, `serial_number`, `part_number` | Hardware identification |
| `firmware`, `hardware`, `mac_address` | Firmware version, hardware revision, MAC address |
| `name`, `cycle_delay`, `startup_state` | Current PDU settings |
| `inlets[]` | List of inlet sensor readings (`voltage_v`, `current_a`, `active_power_w`, `apparent_power_va`, `power_factor`, `line_frequency_hz`, `active_energy_wh`) plus thresholds (`voltage_thresholds`, `current_thresholds`, `active_power_thresholds`, `apparent_power_thresholds`, each a dict with `upper_critical`/`upper_warning`/`lower_warning`/`lower_critical`, `null` when not active) |
| `outlets[]` | List of outlet states (`number`, `name`, `power_state`, `available`, `current_a`, `active_power_w`) |

### snmp_config

| Parameter | Type | Required | Description |
|---|---|---|---|
| `host` | str | yes | PDU hostname or IP address |
| `username` | str | yes | Authentication username |
| `password` | str | yes | Authentication password |
| `validate_certs` | bool | no (default: true) | Validate TLS certificate |
| `v2_enabled` | bool | no | Enable SNMP v2 |
| `v3_enabled` | bool | no | Enable SNMP v3 |
| `read_community` | str | no | SNMP v2 read community string |
| `write_community` | str | no | SNMP v2 write community string |
| `sys_contact` | str | no | SNMP sysContact value |
| `sys_name` | str | no | SNMP sysName value |
| `sys_location` | str | no | SNMP sysLocation value |

### snmp_trap_action

| Parameter | Type | Required | Description |
|---|---|---|---|
| `host` | str | yes | PDU hostname or IP address |
| `username` | str | yes | Authentication username |
| `password` | str | yes | Authentication password |
| `validate_certs` | bool | no (default: true) | Validate TLS certificate |
| `name` | str | yes | Action name (used as idempotency key) |
| `notification_type` | str | no (default: v2Trap) | SNMP notification type (`v2Trap` / `v3Trap` / `v2Inform`) |
| `destinations` | list | no | List of trap destinations (up to 3). Each entry: `host` (required), `port` (default: 162), `community` (default: "") |
| `state` | str | no (default: present) | `present` to create/update, `absent` to delete |

### syslog_action

| Parameter | Type | Required | Description |
|---|---|---|---|
| `host` | str | yes | PDU hostname or IP address |
| `username` | str | yes | Authentication username |
| `password` | str | yes | Authentication password |
| `validate_certs` | bool | no (default: true) | Validate TLS certificate |
| `name` | str | yes | Action name (used as idempotency key) |
| `server` | str | no | Syslog server hostname or IP address |
| `port` | int | no (default: 514) | Syslog server UDP port |
| `state` | str | no (default: present) | `present` to create/update, `absent` to delete |

Sends syslog messages over UDP only (TCP/TLS are not exposed as module options). Actions created before this fix used an invalid `type` (`'syslog'` instead of `'SendSyslogMessage'`); since `modifyAction` may not update `type` on existing actions, delete (`state: absent`) and recreate any action created with an older version of this module.

### user_account

| Parameter | Type | Required | Description |
|---|---|---|---|
| `host` | str | yes | PDU hostname or IP address |
| `username` | str | yes | Authentication username (PDU admin) |
| `password` | str | yes | Authentication password (PDU admin) |
| `validate_certs` | bool | no (default: true) | Validate TLS certificate |
| `target_user` | str | yes | Username to manage |
| `new_password` | str | no | Password for the target user. Required when creating or updating; not sent when no changes detected. |
| `snmp_v3_enabled` | bool | no | Enable SNMPv3 for this user |
| `sec_level` | str | no | SNMPv3 security level (`no_auth_no_priv` / `auth_no_priv` / `auth_priv`) |
| `auth_protocol` | str | no | Authentication protocol (`md5` / `sha1` / `sha224` / `sha256` / `sha384` / `sha512`) |
| `priv_protocol` | str | no | Privacy protocol (`des` / `aes128` / `aes192` / `aes256` / `aes192_3des` / `aes256_3des`) |
| `use_password_as_auth_passphrase` | bool | no | Use account password as authentication passphrase |
| `auth_passphrase` | str | no | Authentication passphrase (when `use_password_as_auth_passphrase` is false) |
| `use_auth_passphrase_as_priv_passphrase` | bool | no | Use authentication passphrase as privacy passphrase |
| `priv_passphrase` | str | no | Privacy passphrase (when `use_auth_passphrase_as_priv_passphrase` is false) |
| `state` | str | no (default: present) | `present` to create/update, `absent` to delete |

Note: Passphrases are write-only — not included in idempotency check (PDU does not return current values).

## Playbooks

Ready-to-use playbooks are in `playbooks/`. Copy `playbooks/vars.yml.example` to `playbooks/vars.yml`, fill in your PDU credentials, then run any playbook directly.

```bash
cp playbooks/vars.yml.example playbooks/vars.yml
vi playbooks/vars.yml   # edit pdu_host, pdu_user, pdu_pass
ansible-playbook playbooks/pdu_facts.yml
ansible-playbook playbooks/outlet_on.yml
```

### Playbook Reference

#### pdu_facts.yml

Display PDU hardware model, firmware version, and real-time sensor readings (inlet/outlet voltage, current, power).

**Usage:**
```bash
ansible-playbook playbooks/pdu_facts.yml
```

**Output:** Facts registered as `pdu_info` (model, firmware) and `inlet_readings`, `outlet_readings` (voltage, current, active/apparent power, thresholds).

---

#### outlet_on.yml

Power on a specific outlet. Prompts for outlet number (1-based).

**Usage:**
```bash
ansible-playbook playbooks/outlet_on.yml
# Prompted for: outlet_number
```

**Variables (in `playbooks/vars.yml`):**
- `pdu_host` (required) — PDU IP/hostname
- `pdu_user` (required) — PDU username
- `pdu_pass` (required) — PDU password
- `validate_certs` (optional, default: true) — Validate TLS certificate

---

#### outlet_off.yml

Power off a specific outlet. Prompts for outlet number.

**Usage:**
```bash
ansible-playbook playbooks/outlet_off.yml
# Prompted for: outlet_number
```

---

#### outlet_cycle.yml

Power cycle (off → on) a specific outlet. Prompts for outlet number.

**Usage:**
```bash
ansible-playbook playbooks/outlet_cycle.yml
# Prompted for: outlet_number
```

**Note:** The PDU's cycle delay (`pdu_config.cycle_delay`) determines the off-to-on interval; default is ~10 seconds.

---

#### inlet_rename.yml

Rename a specific inlet. Prompts for inlet number and new name.

**Usage:**
```bash
ansible-playbook playbooks/inlet_rename.yml
# Prompted for: inlet_number, inlet_name
```

**Variables:**
- `inlet_number` (prompted, 1-based)
- `inlet_name` (prompted, max ~64 chars)

---

#### inlet_threshold.yml

Set upper warning/critical alert thresholds on an inlet sensor. Prompts for inlet number, sensor type, and threshold values.

**Usage:**
```bash
ansible-playbook playbooks/inlet_threshold.yml
# Prompted for: inlet_number, sensor (voltage/current/active_power/apparent_power/frequency/etc.)
#              upper_warning, upper_critical
```

**Supported sensors:** See `inlet_config` module reference for the full `SENSOR_MAP` (voltage, current, active_power, apparent_power, frequency, power_factor, three_phase_apparent_power, three_phase_active_power, residual_current, neutral_current, total_power_factor, total_active_power, total_apparent_power, total_current).

**Note:** Setting a threshold value automatically enables that threshold; use `unset_thresholds` in `inlet_config` to disable without losing the stored value.

---

#### outlet_threshold.yml

Set upper warning/critical alert thresholds on an outlet sensor. Prompts for outlet number, sensor type, and threshold values.

**Usage:**
```bash
ansible-playbook playbooks/outlet_threshold.yml
# Prompted for: outlet_number, sensor (voltage/current/active_power/apparent_power/power_factor)
#              upper_warning, upper_critical
```

**Supported sensors:** See `outlet_config` module reference for `SENSOR_MAP` (voltage, current, active_power, apparent_power, power_factor, maximum_current, inrush_current).

---

#### pdu_backup.yml

Download and save a PDU configuration backup locally. By default, generates a new timestamped file on each run (`changed=true` every time). Set `pdu_backup_filename` in `vars.yml` for a fixed filename (idempotent, `changed=false` when config hasn't drifted).

**Usage:**
```bash
ansible-playbook playbooks/pdu_backup.yml
# Default: writes timestamped file to ./backup/
```

**Variables (in `playbooks/vars.yml`):**
- `pdu_backup_path` (optional, default: `./backup`) — Backup directory
- `pdu_backup_filename` (optional, omit for timestamped) — Fixed filename for idempotent backups

---

#### monitoring_setup.yml

Set up event logging: creates a syslog action, SNMP trap action, and event rule that fires on any event.

**Usage:**
```bash
ansible-playbook playbooks/monitoring_setup.yml
```

**Creates:**
- Syslog action: sends event messages to a syslog server (prompts for server hostname/port)
- SNMP trap action: sends event traps to a trap destination (prompts for host)
- Event rule: triggers both actions on all events (`event_id: ["**"]`)

**Variables (prompted or in `vars.yml`):**
- `syslog_server` — Syslog server hostname/IP
- `syslog_port` (default: 514) — Syslog UDP port
- `snmp_trap_host` — SNMP trap destination hostname/IP
- `snmp_trap_port` (default: 162) — SNMP trap UDP port

---

#### snmpv3_user.yml

Create a user account with SNMPv3 auth_priv security (authentication + encryption). Prompts for username and password.

**Usage:**
```bash
ansible-playbook playbooks/snmpv3_user.yml
# Prompted for: target_user, new_password
```

**Configuration:**
- Security level: `auth_priv` (auth protocol: SHA-1, priv protocol: AES-128)
- Account password doubles as both authentication and privacy passphrase
- PDU requires admin credentials (in `vars.yml`) to create accounts
