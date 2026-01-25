"""Integration tests for the get_nodes endpoint."""


class TestNodesIntegration:
    """Integration tests for nodes endpoint."""

    def test_get_nodes(self, client):
        """Test fetching nodes from the real API."""
        nodes = client.get_nodes()

        assert isinstance(nodes, list)
        assert len(nodes) > 0

        # Check that nodes are dictionaries with expected fields
        first_node = nodes[0]
        assert isinstance(first_node, dict)
        assert "node" in first_node
        assert "island" in first_node
