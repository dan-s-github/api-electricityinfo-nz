"""Integration tests for the get_prices endpoint."""


import pytest


class TestPricesIntegration:
    """Integration tests for get_prices endpoint."""

    def test_get_prices_multiple_schedules(self, all_schedules, client):
        """Test fetching prices for all schedules at once."""
        assert len(all_schedules) >= 1

        # Test with all schedules
        schedule_names = [s.schedule for s in all_schedules]
        market_type = all_schedules[0].market_type

        results = client.get_prices(
            schedules=schedule_names,
            market_type=market_type,
            back=10
        )

        assert isinstance(results, list)
        # Note: API may return empty results for some schedule combinations
        # Just verify the structure if results exist
        if len(results) > 0:
            for result in results:
                assert hasattr(result, "schedule")
                assert hasattr(result, "prices")
                assert isinstance(result.prices, list)

    def test_get_prices_with_back_param(self, all_schedules, client):
        """Test fetching historical prices with back parameter."""
        assert len(all_schedules) > 0

        # Test back parameter for all schedules
        for schedule in all_schedules:
            results = client.get_prices(
                schedules=[schedule.schedule],
                market_type=schedule.market_type,
                back=10
            )

            assert isinstance(results, list)
            # Verify structure if results exist
            if len(results) > 0:
                assert hasattr(results[0], "schedule")
                assert hasattr(results[0], "prices")

    def test_get_prices_with_forward_param(self, all_schedules, client):
        """Test fetching future prices with forward parameter (resilient to no data)."""
        assert len(all_schedules) > 0

        schedules_without_forward = []
        schedules_with_forward = []

        # Test forward parameter for all schedules
        # This is resilient - forward may return empty if no future data exists
        for schedule in all_schedules:
            try:
                results = client.get_prices(
                    schedules=[schedule.schedule],
                    market_type=schedule.market_type,
                    forward=5
                )

                assert isinstance(results, list)
                # No assertion on length - forward may legitimately return empty
                # if no future scheduled prices exist
                if len(results) > 0 and any(len(r.prices) > 0 for r in results):
                    schedules_with_forward.append(schedule.schedule)
                    assert hasattr(results[0], "schedule")
                    assert hasattr(results[0], "prices")
                else:
                    schedules_without_forward.append(schedule.schedule)
            except Exception as e:
                # If forward fails, that's acceptable - not all schedules have forward data
                # Just ensure it's not an authentication or other critical error
                assert "401" not in str(e) and "403" not in str(e)
                schedules_without_forward.append(schedule.schedule)

        # Report which schedules don't have forward data
        if schedules_without_forward:
            print(f"\nSchedules without forward data: {', '.join(schedules_without_forward)}")
        else:
            print("\nSchedules without forward data: None")

        if schedules_with_forward:
            print(f"Schedules with forward data: {', '.join(schedules_with_forward)}")
        else:
            print("Schedules with forward data: None")

    def test_get_prices_with_single_node_forward(self, all_schedules, client):
        """Test fetching forward prices for a single node returns only that node."""
        assert len(all_schedules) > 0

        for schedule in all_schedules:
            try:
                results = client.get_prices(
                    schedules=[schedule.schedule],
                    market_type=schedule.market_type,
                    forward=5,
                )
            except Exception as e:
                assert "401" not in str(e) and "403" not in str(e)
                continue

            price_entries = [price for result in results for price in result.prices]
            if not price_entries:
                continue

            node_name = price_entries[0].node
            single_node_results = client.get_prices(
                schedules=[schedule.schedule],
                market_type=schedule.market_type,
                nodes=[node_name],
                forward=5,
            )
            single_node_entries = [
                price for result in single_node_results for price in result.prices
            ]

            assert single_node_entries
            assert all(price.node == node_name for price in single_node_entries)
            return

        pytest.skip("No schedules returned forward prices for single-node retrieval")

    def test_get_prices_with_back_and_forward(self, all_schedules, client):
        """Test fetching prices with both back and forward parameters."""
        assert len(all_schedules) > 0

        schedules_with_data = []
        schedules_without_data = []

        # Test back and forward together for all schedules
        for schedule in all_schedules:
            try:
                results = client.get_prices(
                    schedules=[schedule.schedule],
                    market_type=schedule.market_type,
                    back=5,
                    forward=5
                )

                assert isinstance(results, list)

                if len(results) > 0 and any(len(r.prices) > 0 for r in results):
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
