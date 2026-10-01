import json
import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")
from gtm_agent import gtm_agent


SENSITIVE_FIELDS = ("billing_qualification", "tax_id", "date_of_birth", "card_on_file", "credit_check_ref")


def assert_no_sensitive_fields(value):
    serialized = json.dumps(value)
    for field in SENSITIVE_FIELDS:
        assert field not in serialized


def test_get_prospect_returns_only_contact_fields(monkeypatch):
    monkeypatch.setattr(
        gtm_agent.data_service,
        "get_prospect_record",
        lambda prospect_id: {
            "name": "Sample Prospect",
            "email": "sample@example.com",
            "disqualified": False,
            "billing_qualification": {"tax_id": "placeholder"},
            "engagement_history": [],
        },
    )

    result = gtm_agent.get_prospect.invoke({"prospect_id": "LEAD-TEST"})

    assert set(result["prospect"]) == {"prospect_id", "name", "email", "disqualified"}
    assert_no_sensitive_fields(result)


def test_build_prospect_profile_sanitizes_cache_miss(monkeypatch):
    poisoned = {
        "name": "Sample Prospect",
        "email": "sample@example.com",
        "annual_revenue": 10,
        "enrichment_source": "test",
        "disqualified": False,
        "billing_qualification": {"card_on_file": "placeholder"},
    }
    monkeypatch.setattr(gtm_agent.data_service, "_PROFILES", {})
    monkeypatch.setattr(gtm_agent.data_service, "get_prospect_record", lambda prospect_id: poisoned)
    monkeypatch.setattr(gtm_agent.data_service, "fetch_engagement_history", lambda prospect_id: [])
    monkeypatch.setattr(gtm_agent.data_service, "fetch_account_details", lambda prospect_id: [])
    monkeypatch.setattr(gtm_agent.data_service, "fetch_tech_stack", lambda prospect_id: [])

    result = gtm_agent.build_prospect_profile.invoke({"prospect_id": "LEAD-TEST"})

    assert_no_sensitive_fields(result)
    assert_no_sensitive_fields(gtm_agent.data_service._PROFILES)
    assert "annual_revenue" in result["prospect_profile"]


def test_build_prospect_profile_sanitizes_cached_profile(monkeypatch):
    monkeypatch.setattr(
        gtm_agent.data_service,
        "_PROFILES",
        {
            "LEAD-TEST": {
                "prospect_id": "LEAD-TEST",
                "name": "Sample Prospect",
                "billing_qualification": {"credit_check_ref": "placeholder"},
                "unexpected": "drop me",
            }
        },
    )

    result = gtm_agent.build_prospect_profile.invoke({"prospect_id": "LEAD-TEST"})

    assert result["prospect_profile"] == {
        "prospect_id": "LEAD-TEST",
        "name": "Sample Prospect",
    }
    assert_no_sensitive_fields(result)
    assert_no_sensitive_fields(gtm_agent.data_service._PROFILES)


def test_score_prospect_prompt_excludes_sensitive_fields(monkeypatch):
    captured = {}

    class FakeResult:
        def model_dump(self):
            return {"score": 1}

    class FakeScoringLlm:
        def invoke(self, messages):
            captured["messages"] = messages
            return FakeResult()

    monkeypatch.setattr(gtm_agent, "_scoring_llm", FakeScoringLlm())
    monkeypatch.setattr(gtm_agent.data_service, "fetch_tech_stack", lambda prospect_id: ["ExampleTech"])
    profile = {
        "prospect_id": "LEAD-TEST",
        "name": "Sample Prospect",
        "annual_revenue": 10,
        "billing_qualification": {"tax_id": "placeholder"},
    }
    offering = {
        "required_tech_stack": ["ExampleTech"],
        "min_annual_revenue": 1,
        "description": "Example offering",
    }

    gtm_agent.score_prospect.invoke({"prospect_profile": profile, "offering": offering})

    assert_no_sensitive_fields(captured["messages"])
