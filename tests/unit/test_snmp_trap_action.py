import pytest
from unittest.mock import patch, MagicMock
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/modules'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/module_utils'))

import snmp_trap_action


def make_module(params, check_mode=False):
    m = MagicMock()
    m.params = params
    m.check_mode = check_mode
    return m


def base_params(**overrides):
    p = {
        'host': '192.168.1.1', 'username': 'admin', 'password': 'pw',
        'validate_certs': True,
        'name': 'Test SNMP Trap',
        'notification_type': 'v2Trap',
        'destinations': [{'host': '10.0.0.1', 'port': 162, 'community': 'public'}],
        'state': 'present',
    }
    p.update(overrides)
    return p


def make_kv(key, value):
    kv = MagicMock()
    kv.key = key
    kv.value = value
    return kv


def make_action(name='Test SNMP Trap', notif_type='v2Trap',
                dest1='10.0.0.1:162:public', dest2=':162:', dest3=':162:',
                action_id='act-1'):
    a = MagicMock()
    a.id = action_id
    a.name = name
    a.type = 'SendSnmpTrap'
    a.isSystem = False
    a.arguments = [
        make_kv('SnmpNotfType', notif_type),
        make_kv('SnmpTrapDest1', dest1),
        make_kv('SnmpTrapDest2', dest2),
        make_kv('SnmpTrapDest3', dest3),
    ]
    return a


class TestSnmpTrapAction:
    def _setup(self, mock_get_agent, mock_event, existing_actions=None):
        mock_get_agent.return_value = MagicMock()
        mock_engine = MagicMock()
        mock_event.Engine.return_value = mock_engine
        mock_engine.listActions.return_value = existing_actions or []
        mock_event.KeyValue.side_effect = make_kv
        return mock_engine

    def test_create_when_not_exists(self):
        module = make_module(base_params())
        with patch('snmp_trap_action.get_agent') as mga, \
             patch('snmp_trap_action.event') as mev:
            engine = self._setup(mga, mev, existing_actions=[])
            snmp_trap_action.run_module(module)
        engine.addAction.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_no_change_when_exists_and_matches(self):
        module = make_module(base_params())
        existing = make_action()
        with patch('snmp_trap_action.get_agent') as mga, \
             patch('snmp_trap_action.event') as mev:
            engine = self._setup(mga, mev, existing_actions=[existing])
            snmp_trap_action.run_module(module)
        engine.addAction.assert_not_called()
        engine.modifyAction.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    def test_update_when_dest_differs(self):
        module = make_module(base_params(
            destinations=[{'host': '10.0.0.2', 'port': 162, 'community': 'public'}]
        ))
        existing = make_action(dest1='10.0.0.1:162:public')
        with patch('snmp_trap_action.get_agent') as mga, \
             patch('snmp_trap_action.event') as mev:
            engine = self._setup(mga, mev, existing_actions=[existing])
            snmp_trap_action.run_module(module)
        engine.modifyAction.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_update_when_notification_type_differs(self):
        module = make_module(base_params(notification_type='v3Trap'))
        existing = make_action(notif_type='v2Trap')
        with patch('snmp_trap_action.get_agent') as mga, \
             patch('snmp_trap_action.event') as mev:
            engine = self._setup(mga, mev, existing_actions=[existing])
            snmp_trap_action.run_module(module)
        engine.modifyAction.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_multiple_destinations(self):
        module = make_module(base_params(destinations=[
            {'host': '10.0.0.1', 'port': 162, 'community': 'public'},
            {'host': '10.0.0.2', 'port': 162, 'community': 'public'},
        ]))
        with patch('snmp_trap_action.get_agent') as mga, \
             patch('snmp_trap_action.event') as mev:
            engine = self._setup(mga, mev, existing_actions=[])
            snmp_trap_action.run_module(module)
        # Action() is mocked — inspect the keyword args passed to its constructor
        kwargs = mev.Engine.Action.call_args[1]
        args = {kv.key: kv.value for kv in kwargs['arguments']}
        assert args['SnmpTrapDest1'] == '10.0.0.1:162:public'
        assert args['SnmpTrapDest2'] == '10.0.0.2:162:public'
        assert args['SnmpTrapDest3'] == ':162:'

    def test_empty_destinations_uses_defaults(self):
        module = make_module(base_params(destinations=[]))
        with patch('snmp_trap_action.get_agent') as mga, \
             patch('snmp_trap_action.event') as mev:
            engine = self._setup(mga, mev, existing_actions=[])
            snmp_trap_action.run_module(module)
        kwargs = mev.Engine.Action.call_args[1]
        args = {kv.key: kv.value for kv in kwargs['arguments']}
        assert args['SnmpTrapDest1'] == ':162:'
        assert args['SnmpTrapDest2'] == ':162:'
        assert args['SnmpTrapDest3'] == ':162:'

    def test_absent_deletes_existing(self):
        module = make_module(base_params(state='absent'))
        existing = make_action()
        with patch('snmp_trap_action.get_agent') as mga, \
             patch('snmp_trap_action.event') as mev:
            engine = self._setup(mga, mev, existing_actions=[existing])
            snmp_trap_action.run_module(module)
        engine.deleteAction.assert_called_once_with('act-1')
        module.exit_json.assert_called_once_with(changed=True)

    def test_absent_no_change_when_not_exists(self):
        module = make_module(base_params(state='absent'))
        with patch('snmp_trap_action.get_agent') as mga, \
             patch('snmp_trap_action.event') as mev:
            engine = self._setup(mga, mev, existing_actions=[])
            snmp_trap_action.run_module(module)
        engine.deleteAction.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    def test_check_mode_does_not_call_add(self):
        module = make_module(base_params(), check_mode=True)
        with patch('snmp_trap_action.get_agent') as mga, \
             patch('snmp_trap_action.event') as mev:
            engine = self._setup(mga, mev, existing_actions=[])
            snmp_trap_action.run_module(module)
        engine.addAction.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)

    def test_fail_json_on_connection_error(self):
        module = make_module(base_params())
        with patch('snmp_trap_action.get_agent', side_effect=Exception('timeout')):
            snmp_trap_action.run_module(module)
        module.fail_json.assert_called_once()
        assert 'timeout' in module.fail_json.call_args[1]['msg']
