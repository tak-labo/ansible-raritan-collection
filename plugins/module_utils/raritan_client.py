from raritan.rpc import Agent


class RaritanClientError(Exception):
    pass


def get_agent(host, username, password, validate_certs=True):
    """raritan.rpc.Agent を生成して返す。失敗時は RaritanClientError を送出する。"""
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
