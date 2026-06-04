# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
- `pdu_config`, `outlet_config`, `snmp_config`, `syslog_action`, `snmp_trap_action`, `event_rule`, `dns_config`
- Pattern: `getSettings()` → diff current vs desired → `setSettings()` if changed
- Return `changed=True/False` only; no created/deleted semantics

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
