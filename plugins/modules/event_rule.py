DOCUMENTATION = r"""
---
module: event_rule
short_description: Manage a Raritan PDU event engine rule
description:
  - Creates, updates, or deletes an event rule in the PDU event engine.
  - Identified by rule name. Idempotent for present/absent states.
  - Actions are referenced by name and resolved to IDs automatically.
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
  name:
    description: Rule name used as the idempotency key.
    required: true
    type: str
  action_names:
    description: List of action names to execute when the rule fires.
    type: list
    elements: str
  event_id:
    description:
      - Event ID pattern list. Use ["**"] to match all events.
      - Each element corresponds to a component of the event path.
    type: list
    elements: str
    default: ["**"]
  match_type:
    description: When to fire the rule relative to event state transitions.
    type: str
    choices: [asserted, deasserted, both]
    default: both
  enabled:
    description: Whether the rule is active.
    type: bool
    default: true
  auto_rearm:
    description: Automatically rearm the rule after it fires.
    type: bool
    default: true
  state:
    description: Whether the rule should exist.
    type: str
    choices: [present, absent]
    default: present
"""

EXAMPLES = r"""
- name: Create event rule to send syslog on any event
  taklabo.raritan_xerus.event_rule:
    host: 192.168.1.100
    username: admin
    password: secret
    validate_certs: false
    name: "All events to syslog"
    action_names:
      - "Alert to syslog"
    event_id: ["**"]
    match_type: both
    state: present

- name: Delete event rule
  taklabo.raritan_xerus.event_rule:
    host: 192.168.1.100
    username: admin
    password: secret
    validate_certs: false
    name: "All events to syslog"
    state: absent
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

from raritan.rpc import event

ENGINE_TARGET = '/event_engine'

MATCH_TYPE_MAP = {
    'asserted':   event.Engine.Condition.MatchType.ASSERTED,
    'deasserted': event.Engine.Condition.MatchType.DEASSERTED,
    'both':       event.Engine.Condition.MatchType.BOTH,
}


def _resolve_action_ids(action_names, all_actions, module):
    name_to_id = {a.name: a.id for a in all_actions}
    ids = []
    for n in action_names:
        if n not in name_to_id:
            module.fail_json(msg='Action not found: {!r}'.format(n))
            return None
        ids.append(name_to_id[n])
    return ids


def _rule_matches(rule, action_ids, event_id, match_type, enabled, auto_rearm):
    c = rule.condition
    return (
        sorted(rule.actionIds) == sorted(action_ids) and
        sorted(c.eventId) == sorted(event_id) and
        c.matchType == match_type and
        rule.isEnabled == enabled and
        rule.isAutoRearm == auto_rearm
    )


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

    engine = event.Engine(ENGINE_TARGET, agent)

    try:
        all_actions = engine.listActions()
        rules = engine.listRules()
    except Exception as e:
        module.fail_json(msg='Failed to list engine objects: {}'.format(e))
        return

    existing = next((r for r in rules if r.name == p['name']), None)
    state = p.get('state', 'present')

    if state == 'absent':
        if existing is None:
            module.exit_json(changed=False)
            return
        if not module.check_mode:
            try:
                engine.deleteRule(existing.id)
            except Exception as e:
                module.fail_json(msg='Failed to delete rule: {}'.format(e))
                return
        module.exit_json(changed=True)
        return

    # state == 'present'
    action_ids = _resolve_action_ids(p.get('action_names') or [], all_actions, module)
    if action_ids is None:
        return

    event_id = p.get('event_id') or ['**']
    match_type = MATCH_TYPE_MAP[p.get('match_type', 'both')]
    enabled = p.get('enabled', True)
    auto_rearm = p.get('auto_rearm', True)

    if existing is None:
        if not module.check_mode:
            condition = event.Engine.Condition(
                eventId=event_id,
                matchType=match_type,
                negate=False,
                operation=event.Engine.Condition.Op.AND,
                conditions=[],
            )
            new_rule = event.Engine.Rule(
                id='',
                name=p['name'],
                isSystem=False,
                isEnabled=enabled,
                isAutoRearm=auto_rearm,
                actionIds=action_ids,
                arguments=[],
                condition=condition,
                hasMatched=False,
            )
            try:
                engine.addRule(new_rule)
            except Exception as e:
                module.fail_json(msg='Failed to add rule: {}'.format(e))
                return
        module.exit_json(changed=True)
        return

    if _rule_matches(existing, action_ids, event_id, match_type, enabled, auto_rearm):
        module.exit_json(changed=False)
        return

    condition = event.Engine.Condition(
        eventId=event_id,
        matchType=match_type,
        negate=existing.condition.negate,
        operation=existing.condition.operation,
        conditions=[],
    )
    updated = event.Engine.Rule(
        id=existing.id,
        name=existing.name,
        isSystem=existing.isSystem,
        isEnabled=enabled,
        isAutoRearm=auto_rearm,
        actionIds=action_ids,
        arguments=existing.arguments,
        condition=condition,
        hasMatched=existing.hasMatched,
    )
    if not module.check_mode:
        try:
            engine.modifyRule(updated)
        except Exception as e:
            module.fail_json(msg='Failed to modify rule: {}'.format(e))
            return
    module.exit_json(changed=True)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            host=dict(type='str', required=True),
            username=dict(type='str', required=True),
            password=dict(type='str', required=True, no_log=True),
            validate_certs=dict(type='bool', default=True),
            name=dict(type='str', required=True),
            action_names=dict(type='list', elements='str'),
            event_id=dict(type='list', elements='str', default=['**']),
            match_type=dict(type='str', choices=['asserted', 'deasserted', 'both'], default='both'),
            enabled=dict(type='bool', default=True),
            auto_rearm=dict(type='bool', default=True),
            state=dict(type='str', choices=['present', 'absent'], default='present'),
        ),
        supports_check_mode=True,
    )
    run_module(module)


if __name__ == '__main__':
    main()
