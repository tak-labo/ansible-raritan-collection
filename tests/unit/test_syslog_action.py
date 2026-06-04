import pytest
from unittest.mock import patch, MagicMock
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/modules'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/module_utils'))

import syslog_action


def make_module(params, check_mode=False):
    m = MagicMock()
    m.params = params
    m.check_mode = check_mode
    return m


def base_params(**overrides):
    p = {
        'host': '192.168.1.1', 'username': 'admin', 'password': 'pw',
        'validate_certs': True,
        'name': 'Test Syslog',
        'server': '192.168.1.200',
        'port': 514,
        'message_format': '%m',
        'state': 'present',
    }
    p.update(overrides)
    return p


def make_kv(key, value):
    kv = MagicMock()
    kv.key = key
    kv.value = value
    return kv


def make_action(name='Test Syslog', server='192.168.1.200', port='514',
                msg_fmt='%m', action_id='act-1'):
    a = MagicMock()
    a.id = action_id
    a.name = name
    a.type = 'syslog'
    a.isSystem = False
    a.arguments = [
        make_kv('serverName', server),
        make_kv('serverPort', str(port)),
        make_kv('messageFormat', msg_fmt),
    ]
    return a


class TestSyslogAction:
    def _setup(self, mock_get_agent, mock_event, existing_actions=None):
        mock_get_agent.return_value = MagicMock()
        mock_engine = MagicMock()
        mock_event.Engine.return_value = mock_engine
        mock_engine.listActions.return_value = existing_actions or []
        mock_event.KeyValue.side_effect = make_kv
        return mock_engine

    def test_create_when_not_exists(self):
        module = make_module(base_params())
        with patch('syslog_action.get_agent') as mga, \
             patch('syslog_action.event') as mev:
            engine = self._setup(mga, mev, existing_actions=[])
            engine.addAction.return_value = (0, 'new-id')
            syslog_action.run_module(module)
        engine.addAction.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_no_change_when_exists_and_matches(self):
        module = make_module(base_params())
        existing = make_action(name='Test Syslog', server='192.168.1.200',
                               port='514', msg_fmt='%m')
        with patch('syslog_action.get_agent') as mga, \
             patch('syslog_action.event') as mev:
            engine = self._setup(mga, mev, existing_actions=[existing])
            syslog_action.run_module(module)
        engine.addAction.assert_not_called()
        engine.modifyAction.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    def test_update_when_server_differs(self):
        module = make_module(base_params(server='10.0.0.1'))
        existing = make_action(name='Test Syslog', server='192.168.1.200')
        with patch('syslog_action.get_agent') as mga, \
             patch('syslog_action.event') as mev:
            engine = self._setup(mga, mev, existing_actions=[existing])
            syslog_action.run_module(module)
        engine.modifyAction.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_update_when_port_differs(self):
        module = make_module(base_params(port=5140))
        existing = make_action(name='Test Syslog', port='514')
        with patch('syslog_action.get_agent') as mga, \
             patch('syslog_action.event') as mev:
            engine = self._setup(mga, mev, existing_actions=[existing])
            syslog_action.run_module(module)
        engine.modifyAction.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_absent_deletes_existing(self):
        module = make_module(base_params(state='absent'))
        existing = make_action(name='Test Syslog')
        with patch('syslog_action.get_agent') as mga, \
             patch('syslog_action.event') as mev:
            engine = self._setup(mga, mev, existing_actions=[existing])
            syslog_action.run_module(module)
        engine.deleteAction.assert_called_once_with('act-1')
        module.exit_json.assert_called_once_with(changed=True)

    def test_absent_no_change_when_not_exists(self):
        module = make_module(base_params(state='absent'))
        with patch('syslog_action.get_agent') as mga, \
             patch('syslog_action.event') as mev:
            engine = self._setup(mga, mev, existing_actions=[])
            syslog_action.run_module(module)
        engine.deleteAction.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    def test_check_mode_does_not_call_add(self):
        module = make_module(base_params(), check_mode=True)
        with patch('syslog_action.get_agent') as mga, \
             patch('syslog_action.event') as mev:
            engine = self._setup(mga, mev, existing_actions=[])
            syslog_action.run_module(module)
        engine.addAction.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)

    def test_fail_json_on_connection_error(self):
        module = make_module(base_params())
        with patch('syslog_action.get_agent', side_effect=Exception('timeout')):
            syslog_action.run_module(module)
        module.fail_json.assert_called_once()
        assert 'timeout' in module.fail_json.call_args[1]['msg']
