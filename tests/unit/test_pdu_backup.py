import pytest
from unittest.mock import patch, MagicMock
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/modules'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/module_utils'))

import pdu_backup


def make_module(params, check_mode=False):
    m = MagicMock()
    m.params = params
    m.check_mode = check_mode
    return m


def base_params(backup_path, **overrides):
    p = {
        'host': '192.168.1.1', 'username': 'admin', 'password': 'pw',
        'validate_certs': True, 'backup_path': backup_path,
        'filename': None, 'method': 'raw',
        'bulk_password': None, 'bulk_filter_profile': '',
    }
    p.update(overrides)
    return p


class TestPduBackup:
    def _setup_mocks(self, mock_get_agent, mock_rawcfg=None, mock_bulkcfg=None, raw_data=b'CFG-DATA'):
        mock_agent = MagicMock()
        mock_get_agent.return_value = mock_agent
        if mock_rawcfg is not None:
            mock_rawcfg.download.return_value = raw_data
        if mock_bulkcfg is not None:
            mock_bulkcfg.download.return_value = raw_data
        return mock_agent

    def test_raw_backup_creates_file(self, tmp_path):
        module = make_module(base_params(str(tmp_path)))
        with patch('pdu_backup.get_agent') as mga, \
             patch('pdu_backup.rawcfg') as mraw:
            self._setup_mocks(mga, mock_rawcfg=mraw)
            pdu_backup.run_module(module)

        files = list(tmp_path.iterdir())
        assert len(files) == 1
        assert files[0].read_bytes() == b'CFG-DATA'
        module.exit_json.assert_called_once()
        assert module.exit_json.call_args[1]['changed'] is True

    def test_bulk_backup_calls_bulkcfg_with_options(self, tmp_path):
        module = make_module(base_params(
            str(tmp_path), method='bulk', bulk_password='secret', bulk_filter_profile='http_settings'))
        with patch('pdu_backup.get_agent') as mga, \
             patch('pdu_backup.bulkcfg') as mbulk:
            self._setup_mocks(mga, mock_bulkcfg=mbulk)
            pdu_backup.run_module(module)

        mbulk.download.assert_called_once_with(
            mga.return_value, backup=True, password='secret',
            clear_text=False, filter_profile='http_settings')
        module.exit_json.assert_called_once()
        assert module.exit_json.call_args[1]['changed'] is True

    def test_check_mode_does_not_write_file(self, tmp_path):
        module = make_module(base_params(str(tmp_path)), check_mode=True)
        with patch('pdu_backup.get_agent') as mga, \
             patch('pdu_backup.rawcfg') as mraw:
            self._setup_mocks(mga, mock_rawcfg=mraw)
            pdu_backup.run_module(module)

        assert list(tmp_path.iterdir()) == []
        module.exit_json.assert_called_once()
        assert module.exit_json.call_args[1]['changed'] is True

    def test_fixed_filename_no_change_when_content_matches(self, tmp_path):
        existing = tmp_path / 'fixed.cfg'
        existing.write_bytes(b'CFG-DATA')
        module = make_module(base_params(str(tmp_path), filename='fixed.cfg'))
        with patch('pdu_backup.get_agent') as mga, \
             patch('pdu_backup.rawcfg') as mraw:
            self._setup_mocks(mga, mock_rawcfg=mraw)
            pdu_backup.run_module(module)

        module.exit_json.assert_called_once()
        assert module.exit_json.call_args[1]['changed'] is False

    def test_fixed_filename_changed_when_content_differs(self, tmp_path):
        existing = tmp_path / 'fixed.cfg'
        existing.write_bytes(b'OLD-DATA')
        module = make_module(base_params(str(tmp_path), filename='fixed.cfg'))
        with patch('pdu_backup.get_agent') as mga, \
             patch('pdu_backup.rawcfg') as mraw:
            self._setup_mocks(mga, mock_rawcfg=mraw)
            pdu_backup.run_module(module)

        assert existing.read_bytes() == b'CFG-DATA'
        module.exit_json.assert_called_once()
        assert module.exit_json.call_args[1]['changed'] is True

    def test_backup_path_auto_created(self, tmp_path):
        nested = tmp_path / 'nested' / 'dir'
        module = make_module(base_params(str(nested)))
        with patch('pdu_backup.get_agent') as mga, \
             patch('pdu_backup.rawcfg') as mraw:
            self._setup_mocks(mga, mock_rawcfg=mraw)
            pdu_backup.run_module(module)

        assert nested.is_dir()
        assert len(list(nested.iterdir())) == 1
        module.exit_json.assert_called_once()

    def test_fail_json_on_download_error(self, tmp_path):
        module = make_module(base_params(str(tmp_path)))
        with patch('pdu_backup.get_agent') as mga, \
             patch('pdu_backup.rawcfg') as mraw:
            mga.return_value = MagicMock()
            mraw.download.side_effect = Exception('timeout')
            pdu_backup.run_module(module)

        module.fail_json.assert_called_once()
        assert 'timeout' in module.fail_json.call_args[1]['msg']

    def test_fail_json_on_connection_error(self, tmp_path):
        module = make_module(base_params(str(tmp_path)))
        with patch('pdu_backup.get_agent', side_effect=Exception('auth failed')):
            pdu_backup.run_module(module)

        module.fail_json.assert_called_once()
        assert 'auth failed' in module.fail_json.call_args[1]['msg']
