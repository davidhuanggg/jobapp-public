"""
Tests for the 3-day freshness filter inside find_matching_jobs.

We test the filter logic directly (date arithmetic + keep/drop rules) so we
don't need to mock the job-board APIs.
"""
from datetime import date, datetime, timedelta, timezone


# ---------------------------------------------------------------------------
# Helpers duplicated from job_matching_service so we can test the logic
# in isolation without triggering API imports.
# ---------------------------------------------------------------------------
MAX_DAYS = 3


def apply_freshness_filter(jobs: list[dict], today: date) -> list[dict]:
    """Mirror of the freshness block in find_matching_jobs."""
    fresh = []
    for j in jobs:
        raw_date = j.get("posted_date")
        if raw_date:
            try:
                posted = datetime.strptime(str(raw_date)[:10], "%Y-%m-%d").date()
                days_ago = (today - posted).days
                j = dict(j)          # don't mutate the original
                j["days_since_posted"] = days_ago
                if days_ago <= MAX_DAYS:
                    fresh.append(j)
            except ValueError:
                j = dict(j)
                j["days_since_posted"] = None
                fresh.append(j)
        else:
            j = dict(j)
            j["days_since_posted"] = None
            fresh.append(j)
    return fresh


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestFreshnessFilter:
    @property
    def today(self) -> date:
        return date(2025, 3, 18)   # fixed anchor so tests are deterministic

    def _job(self, days_ago: int | None) -> dict:
        if days_ago is None:
            return {"job_id": "x", "title": "Test Job", "posted_date": None}
        d = self.today - timedelta(days=days_ago)
        return {"job_id": str(days_ago), "title": "Test Job", "posted_date": d.isoformat()}

    # -- kept --
    def test_posted_today_is_kept(self):
        result = apply_freshness_filter([self._job(0)], self.today)
        assert len(result) == 1
        assert result[0]["days_since_posted"] == 0

    def test_posted_1_day_ago_is_kept(self):
        result = apply_freshness_filter([self._job(1)], self.today)
        assert len(result) == 1

    def test_posted_2_days_ago_is_kept(self):
        result = apply_freshness_filter([self._job(2)], self.today)
        assert len(result) == 1

    def test_posted_3_days_ago_is_kept(self):
        result = apply_freshness_filter([self._job(3)], self.today)
        assert len(result) == 1

    # -- dropped --
    def test_posted_4_days_ago_is_dropped(self):
        result = apply_freshness_filter([self._job(4)], self.today)
        assert len(result) == 0

    def test_posted_30_days_ago_is_dropped(self):
        result = apply_freshness_filter([self._job(30)], self.today)
        assert len(result) == 0

    # -- no date → keep --
    def test_no_posted_date_is_kept(self):
        result = apply_freshness_filter([self._job(None)], self.today)
        assert len(result) == 1
        assert result[0]["days_since_posted"] is None

    # -- bad date format → keep --
    def test_unparseable_date_is_kept(self):
        job = {"job_id": "bad", "title": "Test", "posted_date": "not-a-date"}
        result = apply_freshness_filter([job], self.today)
        assert len(result) == 1
        assert result[0]["days_since_posted"] is None

    # -- mixed batch --
    def test_mixed_batch_filters_correctly(self):
        jobs = [self._job(d) for d in [0, 1, 2, 3, 4, 7, 30]] + [self._job(None)]
        result = apply_freshness_filter(jobs, self.today)
        # 0,1,2,3 days + None → 5 kept; 4,7,30 → dropped
        assert len(result) == 5
        kept_ages = [j["days_since_posted"] for j in result if j["days_since_posted"] is not None]
        assert max(kept_ages) == 3

    def test_days_since_posted_attached_correctly(self):
        jobs = [self._job(2)]
        result = apply_freshness_filter(jobs, self.today)
        assert result[0]["days_since_posted"] == 2
