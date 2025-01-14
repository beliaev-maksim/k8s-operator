# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
"""Additions to tools missing from juju library."""

import json
import logging
from typing import Optional

from juju.model import Model
from tenacity import retry, stop_after_attempt, wait_fixed

log = logging.getLogger(__name__)


async def get_address(model: Model, app_name: str, unit_num: Optional[int] = None) -> str:
    """Find unit address for any application.

    Args:
        model: juju model
        app_name: string name of application
        unit_num: integer number of a juju unit

    Returns:
        unit address as a string
    """
    status = await model.get_status()
    app = status["applications"][app_name]
    return (
        app.public_address
        if unit_num is None
        else app["units"][f"{app_name}/{unit_num}"]["address"]
    )


async def get_nodes(k8s):
    """Return Node list

    Args:
        k8s: any k8s unit

    Returns:
        list of nodes
    """
    action = await k8s.run("k8s kubectl get nodes -o json")
    result = await action.wait()
    assert result.results["return-code"] == 0, "Failed to get nodes with kubectl"
    log.info("Parsing node list...")
    node_list = json.loads(result.results["stdout"])
    assert node_list["kind"] == "List", "Should have found a list of nodes"
    return node_list["items"]


@retry(reraise=True, stop=stop_after_attempt(12), wait=wait_fixed(15))
async def ready_nodes(k8s, expected_count):
    """Get a list of the ready nodes.

    Args:
        k8s: k8s unit
        expected_count: number of expected nodes
    """
    log.info("Finding all nodes...")
    nodes = await get_nodes(k8s)
    ready_nodes = {
        node["metadata"]["name"]: all(
            condition["status"] == "False"
            for condition in node["status"]["conditions"]
            if condition["type"] != "Ready"
        )
        for node in nodes
    }
    log.info("Found %d/%d nodes...", len(ready_nodes), expected_count)
    assert len(ready_nodes) == expected_count, f"Expect {expected_count} nodes in the list"
    for node, ready in ready_nodes.items():
        log.info("Node %s is %s..", node, "ready" if ready else "not ready")
        assert ready, f"Node not yet ready: {node}."
