"""
Quick offline sanity checks for tools/llm.py — mocks requests.post so
no network / real API keys are needed. Run with:  python3 test_llm.py
"""

import unittest
from unittest.mock import patch, MagicMock

import llm


def fake_resp(status_code=200, json_data=None, text=""):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data or {}
    r.text = text
    return r


class TestLLMBroker(unittest.TestCase):

    def setUp(self):
        # pretend both keys are configured
        llm.GROQ_API_KEY = "fake-groq-key"
        llm.GEMINI_API_KEY = "fake-gemini-key"
        llm.BASE_DELAY = 0.01  # speed up retry sleeps during tests

    @patch("llm.requests.post")
    def test_groq_success_first_try(self, mock_post):
        mock_post.return_value = fake_resp(
            200, {"choices": [{"message": {"content": "hello from groq"}}]}
        )
        result = llm.complete("hi")
        self.assertEqual(result, "hello from groq")
        self.assertEqual(mock_post.call_count, 1)

    @patch("llm.requests.post")
    def test_groq_fails_falls_back_to_gemini(self, mock_post):
        def side_effect(url, **kwargs):
            if "groq" in url:
                return fake_resp(500, text="groq down")
            return fake_resp(
                200,
                {"candidates": [{"content": {"parts": [{"text": "hello from gemini"}]}}]},
            )
        mock_post.side_effect = side_effect
        result = llm.complete("hi")
        self.assertEqual(result, "hello from gemini")
        # 3 groq retries + 1 gemini success
        self.assertEqual(mock_post.call_count, llm.MAX_RETRIES + 1)

    @patch("llm.requests.post")
    def test_both_providers_fail_raises_llmerror(self, mock_post):
        mock_post.return_value = fake_resp(500, text="down")
        with self.assertRaises(llm.LLMError):
            llm.complete("hi")

    def test_empty_prompt_raises_immediately(self):
        with self.assertRaises(llm.LLMError):
            llm.complete("")

    def test_register_calls_registry_register(self):
        fake_registry = MagicMock()
        llm.register(fake_registry)
        fake_registry.register.assert_called_once_with("llm_complete", llm.complete)


if __name__ == "__main__":
    unittest.main(verbosity=2)
