from collections.abc import Mapping

import requests

from ..constants import DEFAULT_TIMEOUT
from ..exceptions import ResponseFormatError
from ..models import NodeInfo


def list_nodes(
    session: requests.Session,
    base_url: str,
    *,
    headers: Mapping[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> list[NodeInfo]:
    """Return supported nodes from the API."""
    url = f"{base_url}/nodes"
    resp = session.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    payload = resp.json()
    if not isinstance(payload, list):
        raise ResponseFormatError("Invalid nodes payload in API response")

    nodes: list[NodeInfo] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ResponseFormatError("Invalid node entry in API response")

        node = item.get("node")
        island = item.get("island")
        if not isinstance(node, str) or not node:
            raise ResponseFormatError("Invalid or missing 'node' in API response")
        if not isinstance(island, str) or not island:
            raise ResponseFormatError("Invalid or missing 'island' in API response")

        nodes.append({"node": node, "island": island})

    return nodes
