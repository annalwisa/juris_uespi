import unittest
from unittest.mock import patch

from chatbot.evaluation import (
    _cosine,
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)


class TestEvaluationMetrics(unittest.TestCase):
    @patch("chatbot.evaluation._decompose_statements")
    @patch("chatbot.evaluation._ask_json")
    def test_faithfulness(self, mock_ask, mock_decompose):
        mock_decompose.return_value = ["afirmacao A", "afirmacao B"]
        mock_ask.return_value = {"verdicts": [1, 0]}
        score = faithfulness("resposta", ["contexto"])
        self.assertAlmostEqual(score, 0.5)

    @patch("chatbot.evaluation._decompose_statements")
    @patch("chatbot.evaluation._ask_json")
    def test_context_recall(self, mock_ask, mock_decompose):
        mock_decompose.return_value = ["fato 1", "fato 2"]
        mock_ask.return_value = {"verdicts": [1, 1]}
        score = context_recall("referencia", ["trecho"])
        self.assertAlmostEqual(score, 1.0)

    @patch("chatbot.evaluation._ask_json")
    def test_context_precision(self, mock_ask):
        mock_ask.return_value = {"relevances": [1, 0, 1]}
        score = context_precision("pergunta", ["a", "b", "c"], "referencia")
        # AP: pos1 prec=1, pos3 prec=2/3 -> média (1 + 2/3) / 2
        self.assertAlmostEqual(score, (1.0 + 2 / 3) / 2, places=3)

    @patch("chatbot.evaluation._embeddings")
    @patch("chatbot.evaluation._ask_json")
    def test_answer_relevancy(self, mock_ask, mock_emb):
        mock_ask.return_value = {"questions": ["q1", "q2"]}
        mock_emb.return_value.embed_documents.return_value = [
            [1.0, 0.0],
            [1.0, 0.0],
            [0.0, 1.0],
        ]
        score = answer_relevancy("pergunta original", "resposta longa")
        self.assertAlmostEqual(score, 0.5)


class TestCosine(unittest.TestCase):
    def test_orthogonal_vectors(self):
        self.assertAlmostEqual(_cosine([1, 0], [0, 1]), 0.0)

    def test_identical_vectors(self):
        self.assertAlmostEqual(_cosine([1, 1], [1, 1]), 1.0)


if __name__ == "__main__":
    unittest.main()
