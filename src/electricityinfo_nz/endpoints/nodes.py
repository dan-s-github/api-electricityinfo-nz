from typing import List
import requests


def list_nodes(session: requests.Session, base_url: str) -> List[str]:
    url = f"{base_url}/nodes"
    resp = session.get(url)
    resp.raise_for_status()
    return resp.json()
