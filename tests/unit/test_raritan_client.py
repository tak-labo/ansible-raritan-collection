import pytest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../plugins/module_utils'))

from raritan_client import get_agent, RaritanClientError


class TestGetAgent:
    def test_returns_agent_with_correct_params(self):
        with patch('raritan_client.Agent') as mock_agent_cls:
            mock_agent = MagicMock()
            mock_agent_cls.return_value = mock_agent

            agent = get_agent(
                host='192.168.1.1',
                username='admin',
                password='secret',
                validate_certs=True,
            )

            mock_agent_cls.assert_called_once_with(
                'https',
                '192.168.1.1',
                user='admin',
                passwd='secret',
                disable_certificate_verification=False,
            )
            assert agent is mock_agent

    def test_validate_certs_false_disables_verification(self):
        with patch('raritan_client.Agent') as mock_agent_cls:
            get_agent(
                host='192.168.1.1',
                username='admin',
                password='secret',
                validate_certs=False,
            )
            mock_agent_cls.assert_called_once_with(
                'https',
                '192.168.1.1',
                user='admin',
                passwd='secret',
                disable_certificate_verification=True,
            )

    def test_raises_on_agent_instantiation_failure(self):
        with patch('raritan_client.Agent', side_effect=Exception('Connection refused')):
            with pytest.raises(RaritanClientError, match='Connection refused'):
                get_agent(
                    host='192.168.1.1',
                    username='admin',
                    password='secret',
                    validate_certs=True,
                )
