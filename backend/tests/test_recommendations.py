import pytest
from app.services.recommendation_service import get_recommendations, validate_llm_output
from unittest.mock import patch

# Unit test without LLM
def test_recommendations_structure():
    skills = ["Python", "SQL"]
    education = {"degree": "BS CS"}
    work_exp = [{"company": "X", "position": "Engineer", "duration": "2y"}]

    recs = get_recommendations(skills, education, work_exp, dry_run=True)
    assert "recommended_roles" in recs
    assert isinstance(recs["recommended_roles"], list)

# Test LLM output validation
def test_invalid_llm_output_rejected():
    bad_output = {"recommended_roles": [{"title": "ML Engineer"}]}  # missing reason
    with pytest.raises(ValueError):
        validate_llm_output(bad_output)

# Mock Groq API
@patch("app.services.recommendation_service.client.chat.completions.create")
def test_mock_llm(mock_groq):
    mock_groq.return_value.choices = [type('Obj', (), {'message': type('Msg', (), {'content': '{"recommended_roles":[{"title":"Data Analyst","reason":"skills match"}]}'})()})()]
    
    skills = ["Python"]
    education = {"degree": "BS"}
    work_exp = []
    recs = get_recommendations(skills, education, work_exp)
    
    assert recs["recommended_roles"][0]["title"] == "Data Analyst"

