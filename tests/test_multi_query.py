import unittest
from unittest.mock import MagicMock, patch

import chatbot.config as config
from chatbot.multi_query import generate_query_variations


class TestMultiQuery(unittest.TestCase):
    @patch("chatbot.multi_query.ChatOpenAI")
    def test_returns_original_when_disabled(self, mock_llm):
        old = config.MULTI_QUERY_ENABLED
        config.MULTI_QUERY_ENABLED = False
        try:
            result = generate_query_variations("pergunta teste")
            self.assertEqual(result, ["pergunta teste"])
            mock_llm.assert_not_called()
        finally:
            config.MULTI_QUERY_ENABLED = old

    @patch("chatbot.multi_query.ChatOpenAI")
    def test_parses_variations(self, mock_llm):
        old_enabled = config.MULTI_QUERY_ENABLED
        old_key = config.OPENAI_API_KEY
        config.MULTI_QUERY_ENABLED = True
        config.OPENAI_API_KEY = "test-key"
        try:
            instance = MagicMock()
            instance.invoke.return_value.content = (
                '{"queries": ["variacao 1", "variacao 2"]}'
            )
            mock_llm.return_value = instance
            result = generate_query_variations("pergunta original", n=2)
            self.assertEqual(result[0], "pergunta original")
            self.assertIn("variacao 1", result)
        finally:
            config.MULTI_QUERY_ENABLED = old_enabled
            config.OPENAI_API_KEY = old_key


if __name__ == "__main__":
    unittest.main()
