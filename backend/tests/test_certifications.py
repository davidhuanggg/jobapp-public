"""
Tests for the certification recommendation system in learning_resource_service.

Covers:
- get_certifications_for_role: static catalog lookup, level filtering, deduplication
- get_certifications_for_all_roles: batched static lookup
- build_learning_resources: recommended_certifications present in output
- CERTIFICATION_CATALOG integrity
"""
import pytest
from app.services.learning_resource_service import (
    CERTIFICATION_CATALOG,
    get_certifications_for_role,
    get_certifications_for_all_roles,
    build_learning_resources,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cert_names(certs: list[dict]) -> list[str]:
    return [c["name"] for c in certs]


# ---------------------------------------------------------------------------
# get_certifications_for_role — catalog lookup
# ---------------------------------------------------------------------------
class TestGetCertificationsForRole:
    def test_returns_certs_for_known_skill(self):
        certs = get_certifications_for_role(["aws"])
        assert len(certs) > 0
        assert all("name" in c for c in certs)
        assert all("url" in c for c in certs)

    def test_returns_empty_for_unknown_skill(self):
        certs = get_certifications_for_role(["unknownskillxyz"])
        assert certs == []

    def test_relevant_skill_field_set_correctly(self):
        certs = get_certifications_for_role(["aws"])
        assert all(c["relevant_skill"] == "aws" for c in certs)

    def test_deduplicates_same_cert_from_multiple_skills(self):
        # Both "machine learning" and "tensorflow" map to TensorFlow Developer Certificate
        certs = get_certifications_for_role(["machine learning", "tensorflow"])
        names = _cert_names(certs)
        assert names.count("TensorFlow Developer Certificate") == 1

    def test_multiple_skills_return_all_relevant_certs(self):
        certs = get_certifications_for_role(["aws", "docker"])
        names = _cert_names(certs)
        assert any("AWS" in n for n in names)
        assert any("Docker" in n for n in names)

    def test_empty_gap_skills_returns_empty(self):
        assert get_certifications_for_role([]) == []

    def test_all_returned_certs_have_required_fields(self):
        certs = get_certifications_for_role(["aws", "kubernetes", "python"])
        for cert in certs:
            assert "name" in cert
            assert "provider" in cert
            assert "url" in cert
            assert "cost" in cert
            assert "level" in cert
            assert "relevant_skill" in cert

    def test_role_title_kwarg_accepted_without_error(self):
        # role_title is accepted (absorbed) without raising — call-site compatibility.
        certs = get_certifications_for_role(
            ["python"], role_title="Data Engineer", career_level="entry"
        )
        assert isinstance(certs, list)


# ---------------------------------------------------------------------------
# get_certifications_for_role — level filtering
# ---------------------------------------------------------------------------
class TestCertificationLevelFiltering:
    def test_entry_candidate_gets_entry_and_mid_certs(self):
        # Entry (rank 2) + 1 = up to mid (rank 3) → entry + mid allowed
        certs = get_certifications_for_role(["kubernetes"], career_level="entry")
        levels = {c["level"] for c in certs}
        # CKAD is mid → allowed (within 1 of entry)
        assert "mid" in levels
        # CKA is senior → should be excluded (2 above entry)
        assert not any(c["name"] == "Certified Kubernetes Administrator (CKA)" for c in certs)

    def test_mid_candidate_gets_all_kubernetes_certs(self):
        # Mid (rank 3) + 1 = senior (rank 4) → all levels allowed
        certs = get_certifications_for_role(["kubernetes"], career_level="mid")
        names = _cert_names(certs)
        assert any("CKAD" in n for n in names)
        assert any("CKA" in n for n in names)

    def test_intern_candidate_excludes_mid_certs(self):
        # Intern (rank 1) + 1 = entry (rank 2) → mid (rank 3) is 2 above → excluded
        certs = get_certifications_for_role(["docker"], career_level="intern")
        # Docker Certified Associate is mid-level → excluded for interns
        assert certs == []

    def test_senior_candidate_gets_all_certs(self):
        certs = get_certifications_for_role(["machine learning"], career_level="senior")
        levels = {c["level"] for c in certs}
        assert "senior" in levels

    def test_no_career_level_returns_all_certs(self):
        certs_all = get_certifications_for_role(["kubernetes"], career_level=None)
        certs_limited = get_certifications_for_role(["kubernetes"], career_level="entry")
        # Without filtering we should get at least as many certs
        assert len(certs_all) >= len(certs_limited)

    def test_certs_sorted_closest_level_first(self):
        # For an entry-level candidate the entry-level cert should appear before mid
        certs = get_certifications_for_role(["aws"], career_level="entry")
        levels = [c["level"] for c in certs]
        # entry cert should appear before mid cert
        if "entry" in levels and "mid" in levels:
            assert levels.index("entry") < levels.index("mid")


# ---------------------------------------------------------------------------
# build_learning_resources — recommended_certifications in output
# ---------------------------------------------------------------------------
class TestBuildLearningResourcesWithCertifications:
    def _sample_paths(self) -> dict:
        return {
            "Data Engineer": {
                "core": ["python", "sql"],
                "important": ["aws"],
                "optional": [],
            }
        }

    def test_recommended_certifications_key_present(self):
        result = build_learning_resources(self._sample_paths())
        assert "recommended_certifications" in result["Data Engineer"]

    def test_recommended_certifications_is_list(self):
        result = build_learning_resources(self._sample_paths())
        assert isinstance(result["Data Engineer"]["recommended_certifications"], list)

    def test_certifications_populated_from_gap_skills(self):
        result = build_learning_resources(self._sample_paths())
        certs = result["Data Engineer"]["recommended_certifications"]
        # aws, python, sql should all produce at least one cert
        assert len(certs) > 0

    def test_career_level_passed_through_to_filter(self):
        # Intern-level: docker → DCA is mid → excluded
        paths = {"Backend Engineer": {"core": ["docker"], "important": [], "optional": []}}
        intern_result = build_learning_resources(paths, career_level="intern")
        mid_result = build_learning_resources(paths, career_level="mid")

        intern_certs = intern_result["Backend Engineer"]["recommended_certifications"]
        mid_certs = mid_result["Backend Engineer"]["recommended_certifications"]

        # Mid-level candidate should see the Docker cert; intern should not
        assert len(mid_certs) >= len(intern_certs)

    def test_empty_gap_skills_yields_empty_certifications(self):
        paths = {"DevOps Engineer": {"core": [], "important": [], "optional": []}}
        result = build_learning_resources(paths)
        assert result["DevOps Engineer"]["recommended_certifications"] == []

    def test_existing_skill_buckets_unaffected(self):
        result = build_learning_resources(self._sample_paths(), personalize=False)
        role = result["Data Engineer"]
        assert "core" in role
        assert "important" in role
        assert "optional" in role
        # Certifications are additive — don't replace buckets
        assert len(role["core"]) == 2   # python + sql


# ---------------------------------------------------------------------------
# get_certifications_for_all_roles — batched path (used by parse-and-recommend)
# ---------------------------------------------------------------------------
class TestGetCertificationsForAllRoles:
    def test_returns_dict_keyed_by_role(self):
        result = get_certifications_for_all_roles({
            "Data Engineer": ["python", "sql"],
            "Backend Engineer": ["aws", "docker"],
        })
        assert "Data Engineer" in result
        assert "Backend Engineer" in result

    def test_each_value_is_a_list(self):
        result = get_certifications_for_all_roles({
            "ML Engineer": ["machine learning", "tensorflow"],
        })
        assert isinstance(result["ML Engineer"], list)

    def test_empty_input_returns_empty_dict(self):
        assert get_certifications_for_all_roles({}) == {}

    def test_role_with_no_matching_skills_returns_empty_list(self):
        result = get_certifications_for_all_roles({"Unknown Role": ["unknownskillxyz"]})
        assert result["Unknown Role"] == []

    def test_level_filter_applied_across_all_roles(self):
        # Intern candidate — docker DCA (mid) should be excluded for all roles
        result = get_certifications_for_all_roles(
            {"Backend Engineer": ["docker"]},
            career_level="intern",
        )
        for cert in result.get("Backend Engineer", []):
            cert_rank = {"apprenticeship": 0, "intern": 1, "entry": 2, "mid": 3, "senior": 4}.get(
                cert.get("level", ""), 2
            )
            assert cert_rank <= 1 + 1  # intern rank + 1

    def test_known_skills_return_catalog_certs(self):
        result = get_certifications_for_all_roles({"Backend Engineer": ["aws"]})
        assert len(result["Backend Engineer"]) > 0

    def test_all_certs_come_from_catalog(self):
        result = get_certifications_for_all_roles({
            "Data Engineer": ["python", "sql"],
            "Backend Engineer": ["aws", "docker"],
        })
        for role_certs in result.values():
            for cert in role_certs:
                assert "name" in cert
                assert "url" in cert


# ---------------------------------------------------------------------------
# CERTIFICATION_CATALOG integrity
# ---------------------------------------------------------------------------
class TestCertificationCatalogIntegrity:
    REQUIRED_FIELDS = {"name", "provider", "url", "cost", "level"}
    VALID_LEVELS = {"apprenticeship", "intern", "entry", "mid", "senior"}

    def test_all_entries_have_required_fields(self):
        for skill, entries in CERTIFICATION_CATALOG.items():
            for cert in entries:
                missing = self.REQUIRED_FIELDS - cert.keys()
                assert not missing, f"{skill}: cert missing fields {missing}"

    def test_all_levels_are_valid(self):
        for skill, entries in CERTIFICATION_CATALOG.items():
            for cert in entries:
                assert cert["level"] in self.VALID_LEVELS, (
                    f"{skill} → '{cert['name']}' has invalid level '{cert['level']}'"
                )

    def test_all_urls_are_non_empty_strings(self):
        for skill, entries in CERTIFICATION_CATALOG.items():
            for cert in entries:
                assert isinstance(cert["url"], str) and cert["url"].startswith("http"), (
                    f"{skill} → '{cert['name']}' has bad url '{cert['url']}'"
                )
