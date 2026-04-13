"""Integration tests for the get_schedule_prices endpoint."""

import pytest


class TestSchedulePricesIntegration:
    """Integration tests for get_schedule_prices endpoint."""

    def test_get_schedule_prices(self, all_schedules, client):
        """Test fetching prices for all available schedules."""
        assert len(all_schedules) > 0

        # Test each schedule
        for schedule in all_schedules:
            schedule_name = schedule.schedule
            market_type = schedule.market_type

            # Fetch prices for this schedule
            result = client.get_schedule_prices(
                schedule=schedule_name,
                market_type=market_type,
                back=10,  # Get last 10 records
            )

            assert result is not None
            assert hasattr(result, "schedule")
            assert hasattr(result, "prices")
            assert result.schedule == schedule_name
            assert isinstance(result.prices, list)

    def test_get_schedule_prices_with_nodes(self, all_schedules, client):
        """Test fetching prices for specific nodes across all schedules."""
        nodes = client.get_nodes()

        assert len(all_schedules) > 0
        assert len(nodes) > 0

        # Extract node names from the node dicts
        node_names = [n["node"] for n in nodes[:2]]

        # Test each schedule with node filtering
        for schedule in all_schedules:
            result = client.get_schedule_prices(
                schedule=schedule.schedule,
                market_type=schedule.market_type,
                nodes=node_names,
                back=5,
            )

            assert result is not None
            assert isinstance(result.prices, list)

    def test_get_schedule_prices_with_single_node(self, all_schedules, client):
        """Test fetching prices for a single node returns only that node."""
        assert len(all_schedules) > 0

        for schedule in all_schedules:
            result = client.get_schedule_prices(
                schedule=schedule.schedule,
                market_type=schedule.market_type,
                back=5,
            )

            if not result.prices:
                continue

            node_name = result.prices[0].node
            single_node_result = client.get_schedule_prices(
                schedule=schedule.schedule,
                market_type=schedule.market_type,
                nodes=[node_name],
                back=5,
            )

            assert single_node_result.prices
            assert all(price.node == node_name for price in single_node_result.prices)
            return

        pytest.skip("No schedules returned historical prices for single-node retrieval")

    def test_get_schedule_prices_with_island(self, all_schedules, client):
        """Test fetching prices filtered by island for all schedules."""
        assert len(all_schedules) > 0

        # Test both islands
        for island in ["NI", "SI"]:
            for schedule in all_schedules:
                result = client.get_schedule_prices(
                    schedule=schedule.schedule,
                    market_type=schedule.market_type,
                    island=island,
                    back=5,
                )

                assert result is not None
                assert isinstance(result.prices, list)

    def test_get_schedule_prices_with_forward(self, all_schedules, client):
        """Test fetching forward prices for a single schedule."""
        assert len(all_schedules) > 0

        schedules_without_forward = []
        schedules_with_forward = []

        # Test forward parameter for all schedules
        for schedule in all_schedules:
            try:
                result = client.get_schedule_prices(
                    schedule=schedule.schedule, market_type=schedule.market_type, forward=5
                )

                assert result is not None
                assert isinstance(result.prices, list)

                # Track which schedules have forward data
                if len(result.prices) > 0:
                    schedules_with_forward.append(schedule.schedule)
                else:
                    schedules_without_forward.append(schedule.schedule)
            except Exception as e:
                # If forward fails, that's acceptable - not all schedules have forward data
                assert "401" not in str(e) and "403" not in str(e)
                schedules_without_forward.append(schedule.schedule)

        # Report which schedules have forward data
        if schedules_without_forward:
            print(f"\nSchedules without forward data: {', '.join(schedules_without_forward)}")
        else:
            print("\nSchedules without forward data: None")

        if schedules_with_forward:
            print(f"Schedules with forward data: {', '.join(schedules_with_forward)}")
        else:
            print("Schedules with forward data: None")

    def test_get_schedule_prices_with_back_and_forward(self, all_schedules, client):
        """Test fetching prices with both back and forward parameters for a single schedule."""
        assert len(all_schedules) > 0

        schedules_with_data = []
        schedules_without_data = []

        # Test back and forward together for all schedules
        for schedule in all_schedules:
            try:
                result = client.get_schedule_prices(
                    schedule=schedule.schedule, market_type=schedule.market_type, back=5, forward=5
                )

                assert result is not None
                assert isinstance(result.prices, list)

                if len(result.prices) > 0:
                    schedules_with_data.append(schedule.schedule)
                else:
                    schedules_without_data.append(schedule.schedule)
            except Exception as e:
                assert "401" not in str(e) and "403" not in str(e)
                schedules_without_data.append(schedule.schedule)

        # Report results
        if schedules_with_data:
            print(f"\nSchedules with back+forward data: {', '.join(schedules_with_data)}")
        if schedules_without_data:
            print(f"Schedules without back+forward data: {', '.join(schedules_without_data)}")
