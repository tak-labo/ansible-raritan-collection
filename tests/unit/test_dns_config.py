import pytest
from unittest.mock import patch, MagicMock
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/modules'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/module_utils'))

import dns_config


def make_module(params, check_mode=False):
    m = MagicMock()
    m.params = params
    m.check_mode = check_mode
    return m


def base_params(**overrides):
    p = {
        'host': '192.168.1.1', 'username': 'admin', 'password': 'pw',
        'validate_certs': True,
        'servers': None,
        'search_suffixes': None,
        'prefer_ipv6': None,
    }
    p.update(overrides)
    return p


def make_dns_settings(servers=None, suffixes=None, prefer_ipv6=False):
    s = MagicMock()
    s.serverAddrs = servers or []
    s.searchSuffixes = suffixes or []
    s.resolverPrefersIPv6 = prefer_ipv6
    return s


def make_settings(dns=None):
    settings = MagicMock()
    settings.common.dns = dns or make_dns_settings()
    return settings


class TestDnsConfig:
    def _setup(self, mock_get_agent, mock_net, settings=None):
        mock_get_agent.return_value = MagicMock()
        mock_mgr = MagicMock()
        mock_net.Net.return_value = mock_mgr
        mock_mgr.getSettings.return_value = settings or make_settings()
        mock_mgr.setSettings.return_value = 0
        mock_net.Net.ERR_DNS_TOO_MANY_SERVERS = 100
        mock_net.Net.ERR_DNS_INVALID_SERVER = 101
        mock_net.Net.ERR_DNS_TOO_MANY_SEARCH_SUFFIXES = 102
        mock_net.Net.ERR_DNS_INVALID_SEARCH_SUFFIX = 103
        return mock_mgr

    def test_no_change_when_matches(self):
        settings = make_settings(make_dns_settings(
            servers=['8.8.8.8'], suffixes=['example.com'], prefer_ipv6=False
        ))
        module = make_module(base_params(
            servers=['8.8.8.8'], search_suffixes=['example.com'], prefer_ipv6=False
        ))
        with patch('dns_config.get_agent') as mga, patch('dns_config.net') as mnet:
            mgr = self._setup(mga, mnet, settings)
            dns_config.run_module(module)
        mgr.setSettings.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    def test_servers_change(self):
        settings = make_settings(make_dns_settings(servers=['1.1.1.1']))
        module = make_module(base_params(servers=['8.8.8.8', '8.8.4.4']))
        with patch('dns_config.get_agent') as mga, patch('dns_config.net') as mnet:
            mgr = self._setup(mga, mnet, settings)
            dns_config.run_module(module)
        mgr.setSettings.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_servers_order_insensitive(self):
        settings = make_settings(make_dns_settings(servers=['8.8.4.4', '8.8.8.8']))
        module = make_module(base_params(servers=['8.8.8.8', '8.8.4.4']))
        with patch('dns_config.get_agent') as mga, patch('dns_config.net') as mnet:
            mgr = self._setup(mga, mnet, settings)
            dns_config.run_module(module)
        mgr.setSettings.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    def test_search_suffixes_change(self):
        settings = make_settings(make_dns_settings(suffixes=[]))
        module = make_module(base_params(search_suffixes=['example.com']))
        with patch('dns_config.get_agent') as mga, patch('dns_config.net') as mnet:
            mgr = self._setup(mga, mnet, settings)
            dns_config.run_module(module)
        mgr.setSettings.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_prefer_ipv6_change(self):
        settings = make_settings(make_dns_settings(prefer_ipv6=False))
        module = make_module(base_params(prefer_ipv6=True))
        with patch('dns_config.get_agent') as mga, patch('dns_config.net') as mnet:
            mgr = self._setup(mga, mnet, settings)
            dns_config.run_module(module)
        mgr.setSettings.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_check_mode_does_not_call_set(self):
        settings = make_settings(make_dns_settings(servers=[]))
        module = make_module(base_params(servers=['8.8.8.8']), check_mode=True)
        with patch('dns_config.get_agent') as mga, patch('dns_config.net') as mnet:
            mgr = self._setup(mga, mnet, settings)
            dns_config.run_module(module)
        mgr.setSettings.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)

    def test_set_error_code_fails(self):
        settings = make_settings(make_dns_settings(servers=[]))
        module = make_module(base_params(servers=['bad']))
        with patch('dns_config.get_agent') as mga, patch('dns_config.net') as mnet:
            mgr = self._setup(mga, mnet, settings)
            mgr.setSettings.return_value = 101  # ERR_DNS_INVALID_SERVER
            dns_config.run_module(module)
        module.fail_json.assert_called_once()
        assert 'invalid DNS server' in module.fail_json.call_args[1]['msg']

    def test_connection_error(self):
        module = make_module(base_params())
        with patch('dns_config.get_agent', side_effect=Exception('timeout')):
            dns_config.run_module(module)
        module.fail_json.assert_called_once()
        assert 'timeout' in module.fail_json.call_args[1]['msg']

    def test_get_settings_error(self):
        module = make_module(base_params(servers=['8.8.8.8']))
        with patch('dns_config.get_agent') as mga, patch('dns_config.net') as mnet:
            mgr = self._setup(mga, mnet)
            mgr.getSettings.side_effect = Exception('network error')
            dns_config.run_module(module)
        module.fail_json.assert_called_once()
