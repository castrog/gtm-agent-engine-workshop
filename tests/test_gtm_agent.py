import unittest
from unittest.mock import patch

from gtm_agent.gtm_agent import send_prospect_email


class SendProspectEmailTests(unittest.TestCase):
    def test_disqualified_prospect_is_blocked_without_sending(self):
        with patch("gtm_agent.gtm_agent.uuid.uuid4") as uuid4:
            result = send_prospect_email.func(
                {"prospect_id": "LEAD-50001", "email": "priya@example.com"},
                "Subject",
                "Body",
                runtime=None,
                from_rep={"email": "rep@example.com"},
            )

        self.assertEqual(
            result,
            {"status": "blocked", "reason": "disqualified", "to": "priya@example.com"},
        )
        uuid4.assert_not_called()

    def test_qualified_prospect_is_sent(self):
        result = send_prospect_email.func(
            {"prospect_id": "LEAD-71001", "email": "noah@example.com"},
            "Subject",
            "Body",
            runtime=None,
            from_rep={"email": "rep@example.com", "name": "Rep"},
        )

        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["to"], "noah@example.com")
