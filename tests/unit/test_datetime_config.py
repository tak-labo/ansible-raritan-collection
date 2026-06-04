import pytest
from unittest.mock import patch, MagicMock
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/modules'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/module_utils'))

import datetime_config


def make_module(params, check_mode=False):
    m = MagicMock()
    m.params = params
    m.check_mode = check_mode
    return m


def base_params(**overrides):
    p = {
        'host': '192.168.1.1', 'username': 'admin', 'password': 'pw',
        'validate_certs': True,
        'timezone': None,
        'protocol': None,
        'ntp_server1': None,
        'ntp_server2': None,
    }
    p.update(overrides)
    return p


def make_zone(id, name):
    z = MagicMock()
    z.id = id
    z.name = name
    return z


def make_ntp_cfg(server1='', server2=''):
    n = MagicMock()
    n.server1 = server1
    n.server2 = server2
    return n


def make_zone_cfg(id=76, name='(UTC+09:00) Osaka, Sapporo, Tokyo'):
    z = MagicMock()
    z.id = id
    z.name = name
    return z


def make_cfg(zone_cfg=None, protocol=None, ntp_cfg=None):
    from raritan.rpc import datetime as dt_mod
    cfg = MagicMock()
    cfg.zoneCfg = zone_cfg or make_zone_cfg()
    cfg.protocol = protocol or dt_mod.DateTime.Protocol.NTP
    cfg.ntpCfg = ntp_cfg or make_ntp_cfg()
    return cfg


ZONES = [
    make_zone(76, '(UTC+09:00) Osaka, Sapporo, Tokyo'),
    make_zone(77, '(UTC+09:00) Seoul'),
    make_zone(1, '(UTC-12:00) International Date Line West'),
]


class TestDatetimeConfig:
    def _setup(self, mock_get_agent, mock_dt, cfg=None):
        mock_get_agent.return_value = MagicMock()
        mock_mgr = MagicMock()
        mock_dt.DateTime.return_value = mock_mgr
        mock_mgr.getCfg.return_value = cfg or make_cfg()
        mock_mgr.getZoneInfos.return_value = ZONES
        mock_mgr.setCfg.return_value = 0
        return mock_mgr

    def test_no_change_when_matches(self):
        from raritan.rpc import datetime as dt_mod
        cfg = make_cfg(
            zone_cfg=make_zone_cfg(76, '(UTC+09:00) Osaka, Sapporo, Tokyo'),
            protocol=dt_mod.DateTime.Protocol.NTP,
            ntp_cfg=make_ntp_cfg('ntp.example.com', ''),
        )
        module = make_module(base_params(
            timezone='(UTC+09:00) Osaka, Sapporo, Tokyo',
            protocol='ntp',
            ntp_server1='ntp.example.com',
            ntp_server2='',
        ))
        with patch('datetime_config.get_agent') as mga, patch('datetime_config.dt_mod') as mdt:
            mgr = self._setup(mga, mdt, cfg)
            datetime_config.run_module(module)
        mgr.setCfg.assert_not_called()
        module.exit_json.assert_called_once_with(changed=False)

    def test_timezone_change(self):
        module = make_module(base_params(timezone='(UTC+09:00) Seoul'))
        with patch('datetime_config.get_agent') as mga, patch('datetime_config.dt_mod') as mdt:
            mgr = self._setup(mga, mdt)
            datetime_config.run_module(module)
        mgr.setCfg.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_protocol_change(self):
        from raritan.rpc import datetime as dt_mod
        cfg = make_cfg(protocol=dt_mod.DateTime.Protocol.NTP)
        module = make_module(base_params(protocol='static'))
        with patch('datetime_config.get_agent') as mga, patch('datetime_config.dt_mod') as mdt:
            mgr = self._setup(mga, mdt, cfg)
            mdt.DateTime.Protocol.STATIC = dt_mod.DateTime.Protocol.STATIC
            mdt.DateTime.Protocol.NTP = dt_mod.DateTime.Protocol.NTP
            datetime_config.run_module(module)
        mgr.setCfg.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_ntp_server1_change(self):
        cfg = make_cfg(ntp_cfg=make_ntp_cfg('old.ntp.com', ''))
        module = make_module(base_params(ntp_server1='new.ntp.com'))
        with patch('datetime_config.get_agent') as mga, patch('datetime_config.dt_mod') as mdt:
            mgr = self._setup(mga, mdt, cfg)
            datetime_config.run_module(module)
        mgr.setCfg.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_ntp_server2_change(self):
        cfg = make_cfg(ntp_cfg=make_ntp_cfg('ntp.example.com', ''))
        module = make_module(base_params(ntp_server2='ntp2.example.com'))
        with patch('datetime_config.get_agent') as mga, patch('datetime_config.dt_mod') as mdt:
            mgr = self._setup(mga, mdt, cfg)
            datetime_config.run_module(module)
        mgr.setCfg.assert_called_once()
        module.exit_json.assert_called_once_with(changed=True)

    def test_check_mode_does_not_call_set(self):
        module = make_module(base_params(ntp_server1='ntp.example.com'), check_mode=True)
        with patch('datetime_config.get_agent') as mga, patch('datetime_config.dt_mod') as mdt:
            mgr = self._setup(mga, mdt)
            datetime_config.run_module(module)
        mgr.setCfg.assert_not_called()
        module.exit_json.assert_called_once_with(changed=True)

    def test_unknown_timezone_fails(self):
        module = make_module(base_params(timezone='(UTC+99:00) Nowhere'))
        with patch('datetime_config.get_agent') as mga, patch('datetime_config.dt_mod') as mdt:
            self._setup(mga, mdt)
            datetime_config.run_module(module)
        module.fail_json.assert_called_once()
        assert 'Unknown timezone' in module.fail_json.call_args[1]['msg']

    def test_set_cfg_error_code_fails(self):
        module = make_module(base_params(ntp_server1='bad.ntp'))
        with patch('datetime_config.get_agent') as mga, patch('datetime_config.dt_mod') as mdt:
            mgr = self._setup(mga, mdt)
            mgr.setCfg.return_value = 1
            datetime_config.run_module(module)
        module.fail_json.assert_called_once()
        assert 'error code' in module.fail_json.call_args[1]['msg']

    def test_connection_error(self):
        module = make_module(base_params())
        with patch('datetime_config.get_agent', side_effect=Exception('timeout')):
            datetime_config.run_module(module)
        module.fail_json.assert_called_once()
        assert 'timeout' in module.fail_json.call_args[1]['msg']

    def test_get_cfg_error(self):
        module = make_module(base_params(ntp_server1='ntp.example.com'))
        with patch('datetime_config.get_agent') as mga, patch('datetime_config.dt_mod') as mdt:
            mgr = self._setup(mga, mdt)
            mgr.getCfg.side_effect = Exception('network error')
            datetime_config.run_module(module)
        module.fail_json.assert_called_once()
