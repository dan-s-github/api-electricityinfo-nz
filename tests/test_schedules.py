"""Integration tests for the get_schedules endpoint."""


class TestSchedulesIntegration:
    """Integration tests for schedules endpoint."""

    def test_get_schedules(self, client):
        """Test fetching schedules from the real API."""
        schedules = client.get_schedules()

        assert isinstance(schedules, list)
        assert len(schedules) > 0

        # Check all schedules have expected attributes
        for schedule in schedules:
            assert hasattr(schedule, "schedule")
            assert hasattr(schedule, "run_type")
            assert hasattr(schedule, "market_type")
            assert schedule.schedule is not None
