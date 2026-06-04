# tak_labo.raritan_xerus

Ansible Collection for managing Raritan PDU and other devices.

## Requirements

- Python >= 3.9
- `raritan` pip package >= 4.3.0 (tested with 4.3.13)
- Raritan PDU firmware (tested with 4.3.13.5-52458 on PX3-5138JR)

## Installation

    ansible-galaxy collection install tak_labo.raritan_xerus

Install Python dependency:

    pip install raritan>=4.3.0

## Modules

| Module | Description |
|---|---|
| `tak_labo.raritan_xerus.datetime_config` | Configure NTP servers and timezone |
| `tak_labo.raritan_xerus.dns_config` | Configure DNS server addresses, search suffixes, and IPv6 resolver preference |
| `tak_labo.raritan_xerus.event_rule` | Manage event engine rules (bind actions to event conditions) |
| `tak_labo.raritan_xerus.outlet_config` | Configure individual outlets and control power state (on/off/cycle) |
| `tak_labo.raritan_xerus.pdu_config` | Configure PDU-wide settings (name, startup state, cycle delay) |
| `tak_labo.raritan_xerus.pdu_facts` | Collect PDU facts (model, firmware, inlet sensors, outlet states) |
| `tak_labo.raritan_xerus.snmp_config` | Configure SNMP v2/v3 settings |
| `tak_labo.raritan_xerus.snmp_trap_action` | Manage SNMP trap event actions in the PDU event engine |
| `tak_labo.raritan_xerus.syslog_action` | Manage syslog event actions in the PDU event engine |
| `tak_labo.raritan_xerus.user_account` | Manage PDU user accounts with SNMPv3 settings (create/update/delete) |

All modules are idempotent and support `check_mode`. `pdu_facts` is read-only and always returns `changed=false`.

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

`state: cycle` always reports `changed: true`.

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
| `inlets[]` | List of inlet sensor readings (`voltage_v`, `current_a`, `active_power_w`, `apparent_power_va`, `power_factor`, `line_frequency_hz`, `active_energy_wh`) |
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
| `message_format` | str | no | Syslog message format string |
| `state` | str | no (default: present) | `present` to create/update, `absent` to delete |

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

Ready-to-use playbooks are in `playbooks/`.
Copy `playbooks/vars.yml.example` to `playbooks/vars.yml`, fill in your PDU credentials, then run any playbook directly.

| Playbook | Description |
|---|---|
| `playbooks/pdu_facts.yml` | Display PDU hardware info and current sensor readings |
| `playbooks/outlet_on.yml` | Power on a specific outlet (prompted for outlet number) |
| `playbooks/outlet_off.yml` | Power off a specific outlet (prompted for outlet number) |
| `playbooks/outlet_cycle.yml` | Power cycle a specific outlet (prompted for outlet number) |
| `playbooks/monitoring_setup.yml` | Configure syslog action + SNMP trap action + event rule |
| `playbooks/snmpv3_user.yml` | Create a user account with SNMPv3 auth_priv (prompted for username/password) |

```bash
cp playbooks/vars.yml.example playbooks/vars.yml
ansible-playbook playbooks/pdu_facts.yml
ansible-playbook playbooks/outlet_on.yml
```
