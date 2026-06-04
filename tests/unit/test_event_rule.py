import pytest
from unittest.mock import patch, MagicMock
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/modules'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/module_utils'))

import event_rule


def make_module(params, check_mode=False):
    m = MagicMock()
    m.params = params
    m.check_mode = check_mode
    return m


def base_params(**overrides):
    p = {
        'host': '192.168.1.1', 'username': 'admin', 'password': 'pw',
        'validate_certs': True,
        'name': 'Test Rule',
        'action_names': ['Test Syslog Action'],
        'event_id': ['**'],
        'match_type': 'both',
        'enabled': True,
        'auto_rearm': True,
        'state': 'present',
    }
    p.update(overrides)
    return p


def make_action(name='Test Syslog Action', action_id='action-001'):
    a = MagicMock()
    a.id = action_id
    a.name = name
    return a


def make_condition(event_id=None, match_type=None):
    c = MagicMock()
    c.eventId = event_id or ['**']
    c.matchType = match_type
    c.negate = False
    c.operation = MagicMock()
    c.conditions = []
    return c


def make_rule(name='Test Rule', action_ids=None, event_id=None,
              match_type=None, enabled=True, auto_rearm=True, rule_id='rule-001'):
    r = MagicMock()
    r.id = rule_id
    r.name = name
    r.isSystem = False
    r.isEnabled = enabled
    r.isAutoRearm = auto_rearm
    r.hasMatched = False
    r.actionIds = action_ids or ['action-001']
    r.arguments = []
    r.condition = make_condition(event_id or ['**'], match_type)
    return r


class TestEventRule:
    def _setup(self, mock_get_agent, mock_event,
               existing_actions=None, existing_rules=None):
        mock_get_agent.return_value = MagicMock()
        mock_engine = MagicMock()
        mock_event.Engine.return_value = mock_engine
        mock_engine.listActions.return_value = existing_actions or [make_action()]
        mock_engine.listRules.return_value = existing_rules or []

        mt = MagicMock()
        mt.ASSERTED = 'ASSERTED'
        mt.DEASSERTED = 'DEASSERTED'
        mt.BOTH = 'BOTH'
        mock_event.Engine.Condition.MatchType = mt

        op = MagicMock()
        op.AND = 'AND'
        mock_event.Engine.Condition.Op = op

        return mock_engine

    def test_create_when_not_exists(self):
        module = make_module(base_params())
        with patch('event_rule.get_agent') as mga, \
             patch('event_rule.event') as mev:
            engine = self._setup(mga, mev)
            event_rule.run_module(module)
        engine.addRule.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_no_change_when_matches(self):
        module = make_module(base_params())
        existing = make_rule(match_type='BOTH')
        with patch('event_rule.get_agent') as mga, \
             patch('event_rule.event') as mev, \
             patch.dict(event_rule.MATCH_TYPE_MAP, {'both': 'BOTH'}):
            engine = self._setup(mga, mev, existing_rules=[existing])
            mev.Engine.Condition.MatchType.BOTH = 'BOTH'
            event_rule.run_module(module)
        engine.addRule.assert_not_called()
        engine.modifyRule.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    def test_update_when_action_differs(self):
        module = make_module(base_params(action_names=['Other Action']))
        other_action = make_action(name='Other Action', action_id='action-002')
        existing = make_rule(action_ids=['action-001'], match_type='BOTH')
        with patch('event_rule.get_agent') as mga, \
             patch('event_rule.event') as mev, \
             patch.dict(event_rule.MATCH_TYPE_MAP, {'both': 'BOTH'}):
            engine = self._setup(mga, mev,
                                 existing_actions=[make_action(), other_action],
                                 existing_rules=[existing])
            event_rule.run_module(module)
        engine.modifyRule.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_update_when_event_id_differs(self):
        module = make_module(base_params(event_id=['Outlet', '*', 'State']))
        existing = make_rule(event_id=['**'], match_type='BOTH')
        with patch('event_rule.get_agent') as mga, \
             patch('event_rule.event') as mev, \
             patch.dict(event_rule.MATCH_TYPE_MAP, {'both': 'BOTH'}):
            engine = self._setup(mga, mev, existing_rules=[existing])
            event_rule.run_module(module)
        engine.modifyRule.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_update_when_enabled_differs(self):
        module = make_module(base_params(enabled=False))
        existing = make_rule(enabled=True, match_type='BOTH')
        with patch('event_rule.get_agent') as mga, \
             patch('event_rule.event') as mev, \
             patch.dict(event_rule.MATCH_TYPE_MAP, {'both': 'BOTH'}):
            engine = self._setup(mga, mev, existing_rules=[existing])
            event_rule.run_module(module)
        engine.modifyRule.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_absent_deletes_existing(self):
        module = make_module(base_params(state='absent'))
        existing = make_rule()
        with patch('event_rule.get_agent') as mga, \
             patch('event_rule.event') as mev:
            engine = self._setup(mga, mev, existing_rules=[existing])
            event_rule.run_module(module)
        engine.deleteRule.assert_called_once_with('rule-001')
        module.exit_json.assert_called_once_with(changed=True)

    def test_absent_no_change_when_not_exists(self):
        module = make_module(base_params(state='absent'))
        with patch('event_rule.get_agent') as mga, \
             patch('event_rule.event') as mev:
            engine = self._setup(mga, mev)
            event_rule.run_module(module)
        engine.deleteRule.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    def test_fail_when_action_not_found(self):
        module = make_module(base_params(action_names=['Nonexistent Action']))
        with patch('event_rule.get_agent') as mga, \
             patch('event_rule.event') as mev:
            engine = self._setup(mga, mev)
            event_rule.run_module(module)
        module.fail_json.assert_called_once()
        assert 'Nonexistent Action' in module.fail_json.call_args[1]['msg']

    def test_check_mode_does_not_call_add(self):
        module = make_module(base_params(), check_mode=True)
        with patch('event_rule.get_agent') as mga, \
             patch('event_rule.event') as mev:
            engine = self._setup(mga, mev)
            event_rule.run_module(module)
        engine.addRule.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)

    def test_fail_json_on_connection_error(self):
        module = make_module(base_params())
        with patch('event_rule.get_agent', side_effect=Exception('timeout')):
            event_rule.run_module(module)
        module.fail_json.assert_called_once()
        assert 'timeout' in module.fail_json.call_args[1]['msg']
