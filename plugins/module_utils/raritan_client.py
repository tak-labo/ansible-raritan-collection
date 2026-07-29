"""Shared Raritan PDU client utilities for collection modules.

This module provides helpers for establishing and managing connections to Raritan PDU
JSON-RPC APIs, centralizing error handling and connection logic across all modules.
"""

from raritan.rpc import Agent


class RaritanClientError(Exception):
    """Exception raised when PDU connection or client initialization fails."""


def get_agent(host, username, password, validate_certs=True):
    """Create and return a raritan.rpc.Agent for JSON-RPC communication with PDU.

    Args:
        host (str): PDU hostname or IP address.
        username (str): PDU authentication username.
        password (str): PDU authentication password.
        validate_certs (bool, optional): Whether to validate TLS certificate.
            Defaults to True.

    Returns:
        raritan.rpc.Agent: An authenticated agent for JSON-RPC API calls.

    Raises:
        RaritanClientError: If connection fails (network error, auth failure, etc.).

    Example:
        >>> agent = get_agent('192.168.1.100', 'admin', 'password', validate_certs=True)
        >>> from raritan.rpc import pdu
        >>> mgr = pdu.Pdu('/pdu/0', agent)
        >>> settings = mgr.getSettings()
    """
    try:
        return Agent(
            'https',
            host,
            user=username,
            passwd=password,
            disable_certificate_verification=not validate_certs,
        )
    except Exception as e:
        raise RaritanClientError(str(e)) from e
