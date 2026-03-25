"""
Integration tests: verify that the career level produced by parse-and-recommend
is correctly enforced when filtering jobs in jobs/match.

These tests exercise the full seniority pipeline without hitting any external API:
  1. infer_job_level  — detects the level of a job posting
  2. level_compatible — checks whether that level suits the candidate
  3. The combined filter loop used in find_matching_jobs

"parse-and-recommend career level" is represented here as the ``candidate_level``
string (e.g. "entry") that gets stored on ResumeDB and later read by jobs/match.
"""
import pytest
from app.services.experience_level_service import infer_job_level, level_compatible, LEVEL_ORDER


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _job(title: str, description: str = "") -> dict:
    """Minimal job dict that mirrors what find_matching_jobs works with."""
    return {"title": title, "description_snippet": description}


def _apply_level_filter(jobs: list[dict], candidate_level: str) -> list[dict]:
    """
    Mirror of the level-filter loop inside find_matching_jobs.
    Tags each job with job_level then keeps only compatible ones.
    """
    tagged = []
    for job in jobs:
        level, min_yoe = infer_job_level(
            job.get("description_snippet") or "",
            job.get("title") or "",
        )
        job = dict(job)
        job["job_level"] = level
        if min_yoe is not None:
            job["job_min_yoe"] = min_yoe
        tagged.append(job)

    if candidate_level:
        return [j for j in tagged if level_compatible(candidate_level, j.get("job_level"))]
    return tagged


# ---------------------------------------------------------------------------
# Entry-level candidate (parse-and-recommend → "entry")
# ---------------------------------------------------------------------------
class TestEntryLevelCandidate:
    CANDIDATE = "entry"

    def test_entry_job_is_included(self):
        jobs = [_job("Junior Software Engineer")]
        result = _apply_level_filter(jobs, self.CANDIDATE)
        assert len(result) == 1
        assert result[0]["job_level"] == "entry"

    def test_mid_job_is_included(self):
        # 1 level away → stretch, still shown
        jobs = [_job("Software Engineer", "2+ years of experience required")]
        result = _apply_level_filter(jobs, self.CANDIDATE)
        assert len(result) == 1

    def test_senior_by_title_is_excluded(self):
        jobs = [_job("Senior Software Engineer")]
        result = _apply_level_filter(jobs, self.CANDIDATE)
        assert len(result) == 0

    def test_senior_by_yoe_description_is_excluded(self):
        jobs = [_job("Software Engineer", "Minimum 5 years of experience required.")]
        result = _apply_level_filter(jobs, self.CANDIDATE)
        assert len(result) == 0

    def test_senior_by_yoe_abbreviation_is_excluded(self):
        jobs = [_job("Software Engineer", "5+ yoe required")]
        result = _apply_level_filter(jobs, self.CANDIDATE)
        assert len(result) == 0

    def test_senior_by_description_keyword_is_excluded(self):
        jobs = [_job("Software Engineer", "Looking for a seasoned professional with deep expertise.")]
        result = _apply_level_filter(jobs, self.CANDIDATE)
        assert len(result) == 0

    def test_untagged_job_treated_as_mid_and_included(self):
        # No level signals → defaults to "mid" → entry (2) vs mid (3) = diff 1 → compatible
        jobs = [_job("Software Engineer", "Build cool stuff.")]
        result = _apply_level_filter(jobs, self.CANDIDATE)
        assert len(result) == 1
        assert result[0]["job_level"] is None  # raw inferred level is still None

    def test_mixed_batch_filters_correctly(self):
        jobs = [
            _job("Junior Backend Engineer"),                              # entry → keep
            _job("Backend Engineer", "2+ years of experience"),          # mid → keep
            _job("Senior Backend Engineer"),                              # senior → drop
            _job("Staff Backend Engineer"),                               # senior → drop
            _job("Backend Engineer", "Minimum 6 years of experience"),   # senior → drop
            _job("Backend Engineer", "Build APIs"),                       # untagged→mid → keep
        ]
        result = _apply_level_filter(jobs, self.CANDIDATE)
        kept_titles = [j["title"] for j in result]
        assert "Junior Backend Engineer" in kept_titles
        assert "Senior Backend Engineer" not in kept_titles
        assert "Staff Backend Engineer" not in kept_titles
        # 3 jobs kept: junior, mid yoe, untagged
        assert len(result) == 3


# ---------------------------------------------------------------------------
# Intern/student candidate (parse-and-recommend → "intern")
# ---------------------------------------------------------------------------
class TestInternCandidate:
    CANDIDATE = "intern"

    def test_intern_job_is_included(self):
        jobs = [_job("Software Engineering Intern")]
        result = _apply_level_filter(jobs, self.CANDIDATE)
        assert len(result) == 1

    def test_entry_job_is_included(self):
        # 1 level above intern → compatible
        jobs = [_job("Junior Software Engineer")]
        result = _apply_level_filter(jobs, self.CANDIDATE)
        assert len(result) == 1

    def test_mid_job_is_excluded(self):
        # 2 levels above intern → incompatible
        jobs = [_job("Software Engineer", "3+ years of experience")]
        result = _apply_level_filter(jobs, self.CANDIDATE)
        assert len(result) == 0

    def test_senior_job_is_excluded(self):
        jobs = [_job("Senior Software Engineer")]
        result = _apply_level_filter(jobs, self.CANDIDATE)
        assert len(result) == 0

    def test_untagged_job_treated_as_mid_and_excluded(self):
        # No signals → defaults to "mid" → intern (1) vs mid (3) = diff 2 → incompatible
        jobs = [_job("Software Engineer", "Build cool stuff.")]
        result = _apply_level_filter(jobs, self.CANDIDATE)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Mid-level candidate (parse-and-recommend → "mid")
# ---------------------------------------------------------------------------
class TestMidLevelCandidate:
    CANDIDATE = "mid"

    def test_mid_job_is_included(self):
        jobs = [_job("Software Engineer", "3+ years of experience required")]
        result = _apply_level_filter(jobs, self.CANDIDATE)
        assert len(result) == 1

    def test_entry_job_is_included(self):
        jobs = [_job("Junior Software Engineer")]
        result = _apply_level_filter(jobs, self.CANDIDATE)
        assert len(result) == 1

    def test_senior_job_is_included(self):
        jobs = [_job("Senior Software Engineer")]
        result = _apply_level_filter(jobs, self.CANDIDATE)
        assert len(result) == 1

    def test_intern_job_is_excluded(self):
        # 2 levels below mid → incompatible
        jobs = [_job("Software Engineering Intern")]
        result = _apply_level_filter(jobs, self.CANDIDATE)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Senior candidate (parse-and-recommend → "senior")
# ---------------------------------------------------------------------------
class TestSeniorCandidate:
    CANDIDATE = "senior"

    def test_senior_job_is_included(self):
        jobs = [_job("Senior Software Engineer")]
        result = _apply_level_filter(jobs, self.CANDIDATE)
        assert len(result) == 1

    def test_mid_job_is_included(self):
        jobs = [_job("Software Engineer", "2+ years of experience")]
        result = _apply_level_filter(jobs, self.CANDIDATE)
        assert len(result) == 1

    def test_entry_job_is_excluded(self):
        # 2 levels below senior → incompatible
        jobs = [_job("Junior Software Engineer")]
        result = _apply_level_filter(jobs, self.CANDIDATE)
        assert len(result) == 0

    def test_intern_job_is_excluded(self):
        jobs = [_job("Software Engineering Intern")]
        result = _apply_level_filter(jobs, self.CANDIDATE)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# No candidate level (parse-and-recommend could not determine level)
# ---------------------------------------------------------------------------
class TestUnknownCandidateLevel:
    def test_all_jobs_pass_when_candidate_level_is_none(self):
        jobs = [
            _job("Software Engineering Intern"),
            _job("Junior Software Engineer"),
            _job("Software Engineer", "3+ years of experience"),
            _job("Senior Software Engineer"),
        ]
        result = _apply_level_filter(jobs, None)
        assert len(result) == 4

    def test_all_jobs_pass_when_candidate_level_is_empty_string(self):
        jobs = [_job("Senior Software Engineer"), _job("Junior Developer")]
        result = _apply_level_filter(jobs, "")
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Cross-check: inferred job_level matches what parse-and-recommend would store
# ---------------------------------------------------------------------------
class TestJobLevelInferenceAlignedWithCandidateLevel:
    """
    Spot-check that infer_job_level returns a level string that is a valid key
    in LEVEL_ORDER — guaranteeing level_compatible arithmetic will work correctly.
    """
    @pytest.mark.parametrize("title,desc,expected_level", [
        ("Senior Data Engineer",             "",                                    "senior"),
        ("Staff ML Engineer",                "",                                    "senior"),
        ("Data Engineer",                    "Requires 5+ years of experience.",    "senior"),
        ("Data Engineer",                    "At least 5 yoe required.",            "senior"),
        ("Data Engineer",                    "3+ years of experience.",             "mid"),
        ("Junior Data Engineer",             "",                                    "entry"),
        ("Data Engineering Intern",          "",                                    "intern"),
        ("Data Engineer",                    "New grad or entry-level welcome.",    "entry"),
        ("Data Engineer",                    "Build data pipelines.",               None),  # no signal
    ])
    def test_inferred_level(self, title, desc, expected_level):
        level, _ = infer_job_level(desc, title)
        assert level == expected_level
        if level is not None:
            assert level in LEVEL_ORDER, f"'{level}' not in LEVEL_ORDER"
