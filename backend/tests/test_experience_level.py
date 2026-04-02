"""
Tests for experience_level_service — YoE extraction, candidate resolution,
and job compatibility.
"""
import pytest
from app.services.experience_level_service import (
    extract_min_yoe,
    infer_title_min_yoe,
    resolve_candidate_yoe,
    yoe_compatible,
)


# ---------------------------------------------------------------------------
# extract_min_yoe
# ---------------------------------------------------------------------------
class TestExtractMinYoE:
    def test_simple_years(self):
        assert extract_min_yoe("2+ years of experience") == 2.0

    def test_yoe_abbreviation(self):
        assert extract_min_yoe("5+ yoe required") == 5.0

    def test_yrs_abbreviation(self):
        assert extract_min_yoe("3 yrs experience") == 3.0

    def test_minimum_qualifier(self):
        assert extract_min_yoe("Minimum 5 years of experience") == 5.0

    def test_at_least_qualifier(self):
        assert extract_min_yoe("At least 3 years of experience") == 3.0

    def test_picks_minimum_from_multiple(self):
        assert extract_min_yoe("3+ years preferred, 5+ years ideal") == 3.0

    def test_decimal_yoe(self):
        assert extract_min_yoe("1.5 years of experience") == 1.5

    def test_range_with_to(self):
        assert extract_min_yoe("2 to 5 years of experience") == 2.0

    def test_hyphenated_range(self):
        assert extract_min_yoe("8-12 years experience") == 8.0

    def test_hyphenated_range_picks_lowest(self):
        desc = "Bachelor's and 8-12 years experience or Masters and 6-10 years experience"
        assert extract_min_yoe(desc) == 6.0

    def test_en_dash_range(self):
        assert extract_min_yoe("3–5 years of experience") == 3.0

    def test_no_yoe_mentioned(self):
        assert extract_min_yoe("Build cool stuff with Python") is None

    def test_empty_string(self):
        assert extract_min_yoe("") is None

    def test_none_input(self):
        assert extract_min_yoe(None) is None


# ---------------------------------------------------------------------------
# yoe_compatible
# ---------------------------------------------------------------------------
class TestYoeCompatible:
    def test_zero_yoe_vs_two_year_requirement(self):
        assert yoe_compatible(0.0, "2+ years of experience required") is False

    def test_zero_yoe_vs_five_year_requirement(self):
        assert yoe_compatible(0.0, "Minimum 5 years of experience") is False

    def test_sufficient_yoe(self):
        assert yoe_compatible(3.0, "2+ years of experience required") is True

    def test_exact_match(self):
        assert yoe_compatible(2.0, "2+ years of experience required") is True

    def test_no_requirement_in_description(self):
        assert yoe_compatible(0.0, "Build cool products with Python") is True

    def test_candidate_yoe_unknown(self):
        assert yoe_compatible(None, "5+ years of experience") is True

    def test_both_unknown(self):
        assert yoe_compatible(None, "No experience info") is True

    def test_yoe_in_title(self):
        assert yoe_compatible(0.0, "", "Senior Engineer (5+ years)") is False

    def test_description_and_title_combined(self):
        assert yoe_compatible(1.0, "Great team", "Engineer (3+ yrs exp)") is False
        assert yoe_compatible(3.0, "Great team", "Engineer (3+ yrs exp)") is True

    def test_qualifications_checked(self):
        quals = ["Candidates should have over 3 years of experience in data analysis"]
        assert yoe_compatible(0.0, "Great data role", qualifications=quals) is False
        assert yoe_compatible(3.0, "Great data role", qualifications=quals) is True

    def test_twelve_year_requirement_blocked_for_entry(self):
        desc = (
            "A minimum 12 years of experience in SQL programming in platforms "
            "with large data assets within an OLTP, OLAP, and MPP architecture."
        )
        assert yoe_compatible(0.0, desc) is False

    # Layer 2 — title keyword fallback (no explicit YoE in text) ----------
    def test_senior_title_no_yoe_text_blocks_entry_candidate(self):
        # "Senior Data Analyst" has no numeric YoE in the description,
        # but the title keyword implies 4 yrs.
        assert yoe_compatible(0.0, "Great opportunity to work with data.", "Senior Data Analyst") is False

    def test_senior_title_no_yoe_text_blocks_one_year_candidate(self):
        assert yoe_compatible(1.0, "Work with data teams.", "Senior Software Engineer") is False

    def test_senior_title_passes_four_year_candidate(self):
        assert yoe_compatible(4.0, "Work with data teams.", "Senior Software Engineer") is True

    def test_lead_title_blocks_entry_candidate(self):
        assert yoe_compatible(0.0, "Lead exciting projects.", "Lead Data Engineer") is False

    def test_principal_title_blocks_one_year_candidate(self):
        assert yoe_compatible(1.0, "Build systems.", "Principal Engineer") is False

    def test_manager_title_blocks_entry_candidate(self):
        assert yoe_compatible(0.0, "Manage the team.", "Engineering Manager") is False

    def test_junior_title_passes_zero_yoe_candidate(self):
        # "Junior" in title → floor is 0 → anyone qualifies.
        assert yoe_compatible(0.0, "Build cool stuff.", "Junior Developer") is True

    def test_entry_level_title_passes_zero_yoe(self):
        assert yoe_compatible(0.0, "Fun startup role.", "Entry Level Data Analyst") is True

    def test_no_keyword_title_passes_zero_yoe(self):
        # Plain "Data Analyst" has no seniority keyword → no opinion → keep.
        assert yoe_compatible(0.0, "Analyse data.", "Data Analyst") is True

    def test_explicit_yoe_overrides_title_keyword(self):
        # Title says "Senior" (→ 4 yrs implied) but description explicitly
        # says "1+ years" — the explicit number wins.
        assert yoe_compatible(1.0, "1+ years of experience required.", "Senior Analyst") is True


# ---------------------------------------------------------------------------
# infer_title_min_yoe
# ---------------------------------------------------------------------------
class TestInferTitleMinYoe:
    def test_senior_returns_four(self):
        assert infer_title_min_yoe("Senior Data Analyst") == 4.0

    def test_sr_abbreviation(self):
        assert infer_title_min_yoe("Sr. Software Engineer") == 4.0

    def test_lead(self):
        assert infer_title_min_yoe("Lead Backend Engineer") == 4.0

    def test_staff(self):
        assert infer_title_min_yoe("Staff Engineer") == 4.0

    def test_principal(self):
        assert infer_title_min_yoe("Principal Product Manager") == 4.0

    def test_manager(self):
        assert infer_title_min_yoe("Engineering Manager") == 4.0

    def test_director(self):
        assert infer_title_min_yoe("Director of Engineering") == 4.0

    def test_vp(self):
        assert infer_title_min_yoe("VP of Engineering") == 4.0

    def test_junior_returns_zero(self):
        assert infer_title_min_yoe("Junior Developer") == 0.0

    def test_jr_abbreviation(self):
        assert infer_title_min_yoe("Jr. Software Engineer") == 0.0

    def test_entry_level(self):
        assert infer_title_min_yoe("Entry Level Data Analyst") == 0.0

    def test_intern(self):
        assert infer_title_min_yoe("Software Engineering Intern") == 0.0

    def test_mid_returns_two(self):
        assert infer_title_min_yoe("Mid-Level Software Engineer") == 2.0

    def test_intermediate(self):
        assert infer_title_min_yoe("Intermediate Data Scientist") == 2.0

    def test_plain_title_returns_none(self):
        assert infer_title_min_yoe("Data Analyst") is None

    def test_plain_engineer_returns_none(self):
        assert infer_title_min_yoe("Software Engineer") is None

    def test_empty_returns_none(self):
        assert infer_title_min_yoe("") is None


# ---------------------------------------------------------------------------
# resolve_candidate_yoe
# ---------------------------------------------------------------------------
class TestResolveCandidateYoe:
    def test_explicit_yoe_takes_priority(self):
        assert resolve_candidate_yoe(3.5, "entry") == 3.5

    def test_explicit_zero_is_kept(self):
        # Zero is a valid measured value, not the same as None.
        assert resolve_candidate_yoe(0.0, "entry") == 0.0

    def test_entry_level_no_yoe_returns_zero(self):
        assert resolve_candidate_yoe(None, "entry") == 0.0

    def test_intern_no_yoe_returns_zero(self):
        assert resolve_candidate_yoe(None, "intern") == 0.0

    def test_apprenticeship_no_yoe_returns_zero(self):
        assert resolve_candidate_yoe(None, "apprenticeship") == 0.0

    def test_mid_no_yoe_returns_two(self):
        assert resolve_candidate_yoe(None, "mid") == 2.0

    def test_senior_no_yoe_returns_four(self):
        assert resolve_candidate_yoe(None, "senior") == 4.0

    def test_unknown_level_no_yoe_returns_none(self):
        # We have no data at all — do not filter (returns None).
        assert resolve_candidate_yoe(None, None) is None

    def test_unrecognised_level_returns_none(self):
        assert resolve_candidate_yoe(None, "wizard") is None

    # Integration: resolve then filter ---
    def test_entry_candidate_blocked_by_five_year_job(self):
        effective = resolve_candidate_yoe(None, "entry")
        assert yoe_compatible(effective, "5+ years of experience required") is False

    def test_entry_candidate_allowed_through_no_req(self):
        effective = resolve_candidate_yoe(None, "entry")
        assert yoe_compatible(effective, "Passionate about Python and data") is True

    def test_mid_candidate_blocked_by_ten_year_job(self):
        effective = resolve_candidate_yoe(None, "mid")
        assert yoe_compatible(effective, "10+ years of experience required") is False

    def test_mid_candidate_passes_two_year_requirement(self):
        effective = resolve_candidate_yoe(None, "mid")
        assert yoe_compatible(effective, "2+ years of experience") is True
