# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Git Workflow

Never commit or push directly to `main`. Branch protection on `main` has `enforce_admins` enabled, so direct pushes (including by repo admins) are rejected server-side. Always work on a feature branch and open a PR:

```bash
git checkout -b <feature-branch>
# commit changes
git push -u origin <feature-branch>
gh pr create
```

## Commands

```bash
# Run all unit tests
uv run pytest

# Run a single test file
uv run pytest tests/unit/test_dns_config.py -v

# Run integration tests (requires real PDU at 192.168.200.13)
cp plugins/modules/*.py /tmp/ansible_collections/raritan/xerus/plugins/modules/
ANSIBLE_COLLECTIONS_PATH=/tmp/ansible_collections \
  uv run ansible-playbook examples/integration_test.yml -e @examples/integration_test_vars.yml

# Run integration tests from a specific task
ANSIBLE_COLLECTIONS_PATH=/tmp/ansible_collections \
  uv run ansible-playbook examples/integration_test.yml -e @examples/integration_test_vars.yml \
  --start-at-task "[dns_config] apply test settings"
```

After editing any module, copy it to the collection path before running integration tests:
```bash
cp plugins/modules/<module>.py /tmp/ansible_collections/raritan/xerus/plugins/modules/
```

## Architecture

### Module Patterns

Two distinct patterns based on resource type:

**Settings modules** (idempotent diff + apply):
- `pdu_config`, `outlet_config`, `inlet_config`, `snmp_config`, `syslog_action`, `snmp_trap_action`, `event_rule`, `dns_config`
- Pattern: `getSettings()` → diff current vs desired → `setSettings()` if changed
- Return `changed=True/False` only; no created/deleted semantics
- `inlet_config` and `outlet_config` additionally manage sensor alert thresholds via a parallel `getThresholds()`/`setThresholds()` pattern on the `<Inlet|Outlet>.Sensors.<sensor>` (`sensors.NumericSensor`) object selected by the `sensor` param (see each module's `SENSOR_MAP` — the two lists differ: outlets add `maximum_current`/`inrush_current` but lack the three-phase/residual-current sensors inlets have). Setting a threshold value (`upper_critical`/`upper_warning`/`lower_warning`/`lower_critical`) also flips its `*Active` enable flag to `True`. To disable a threshold without touching its stored value, list the field name in `unset_thresholds` instead — a field cannot appear in both a value option and `unset_thresholds` at once (`fail_json`). `setThresholds()` returns an int rc (0=OK) rather than raising, so the rc must be checked explicitly.
- `pdu_facts`'s `_read_thresholds()` helper (`plugins/modules/pdu_facts.py`) works against any `sensors.NumericSensor`, so it is already usable for all 21 sensors listed in `inlet_config.SENSOR_MAP`, not just the 4 currently exposed (`voltage`, `current`, `active_power`, `apparent_power`). Fetching thresholds for the full sensor set vs. only surfacing a subset in the returned facts dict are independent decisions — extending coverage is a matter of adding more `_read_thresholds(s.<sensor>)` calls in `_collect_inlet()`, not a structural change. `_collect_outlet()` doesn't call `_read_thresholds()` at all yet — outlet facts currently report readings only, no thresholds. Full sensor list and SDK API details: `docs/raritan-sdk-inlet-sensors.md` (inlets), `docs/raritan-sdk-outlet-sensors.md` (outlets). For the broader landscape (PDU body, circuits, OCP/breakers, outlet groups, power meters, transfer switches, external peripherals) and which of those have no module support yet, see `docs/raritan-sdk-sensor-coverage.md`. For everything in the SDK outside sensors — auth, security, network interfaces, firmware, peripherals, etc. — see `docs/raritan-sdk-module-coverage.md`.

**Resource modules** (state: present/absent):
- `user_account`
- Pattern: `getAccountNames()` → create/update/delete based on `state` param
- `createAccountFull` cannot set `AUTH_PRIV`/`AUTH_NO_PRIV` at creation time (API limitation, returns rc=5). Workaround: two-step — create with `uuid`-based temp password + blank `UserInfo()`, then immediately `updateAccountFull` with the real password and SNMPv3 settings.
- `updateAccountFull` returns rc=1 if the new password equals the current one; the two-step approach naturally avoids this.

### SDK Access Pattern

All modules use `raritan_client.get_agent()` from `plugins/module_utils/raritan_client.py`, then instantiate the appropriate RPC class:

```python
from raritan.rpc import net
agent = get_agent(host=..., username=..., password=..., validate_certs=...)
mgr = net.Net('/net', agent)          # DNS settings
settings = mgr.getSettings()
# ... mutate settings ...
rc = mgr.setSettings(settings)
```

### Key RPC Targets

| Module | RPC Class | Target Path |
|--------|-----------|-------------|
| `pdu_config` | `pdu.Pdu` | `/pdu/0` |
| `pdu_facts` | `pdumodel.Pdu` | `/model/pdu/0` |
| `outlet_config` | `outlet.Outlet` | `/outlet/<n>` |
| `inlet_config` | `pdumodel.Pdu` | `/model/pdu/0` (via `getInlets()`) |
| `snmp_config` | `snmp.Snmp` | `/snmp` |
| `syslog_action` / `snmp_trap_action` / `event_rule` | `eventengine.*` | `/eventengine` |
| `dns_config` | `net.Net` | `/net` (NOT `/net/manager`) |
| `datetime_config` | `datetime.DateTime` | `/datetime` |
| `user_account` | `usermgmt.UserManager` / `usermgmt.User` | `/auth/user` / `/auth/user/<name>` |

### Unit Test Pattern

Tests patch `<module>.get_agent` and the relevant SDK class:

```python
with patch('dns_config.get_agent') as mga, patch('dns_config.net') as mnet:
    mock_mgr = MagicMock()
    mnet.Net.return_value = mock_mgr
    mock_mgr.getSettings.return_value = <settings mock>
    mock_mgr.setSettings.return_value = 0  # success
    dns_config.run_module(module)
```

The module file imports `from raritan.rpc import net` at module level, so patch the whole `net` module as `<module_name>.net`.

### Integration Test Conventions

- `examples/integration_test.yml` is the single integration test playbook
- `examples/integration_test_vars.yml` holds real PDU credentials (gitignored); `integration_test_vars.yml.example` is the template
- `examples/vars.yml.example` is a simple user-facing sample (for `site.yml`)
- Test tasks use the naming convention `[module_name] <description>` for `--start-at-task` targeting
- Each section establishes a known state, tests idempotency, tests changes, then restores
