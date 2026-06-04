import unittest

from chatbot.retrieval import (
    _doc_has_ref,
    build_lexical_matchers,
    extract_articles,
)


class TestExtractArticles(unittest.TestCase):
    def test_deduplicates_and_limits(self):
        text = "Art. 46 e Artigo 3º. Art. 46 de novo. Art. 12."
        self.assertEqual(
            extract_articles(text, limit=3),
            ["Art. 46", "Art. 3º", "Art. 12"],
        )


class TestLexicalMatchers(unittest.TestCase):
    def test_article_match(self):
        matchers = build_lexical_matchers("qual o Art. 46?")
        self.assertTrue(_doc_has_ref("... Art. 46 trata do cancelamento ...", matchers))
        self.assertFalse(_doc_has_ref("texto sem referencia", matchers))

    def test_article_does_not_match_longer_number(self):
        matchers = build_lexical_matchers("Art. 46")
        self.assertFalse(_doc_has_ref("Art. 460 outro assunto", matchers))

    def test_resolution_number(self):
        matchers = build_lexical_matchers("Resolucao CEPEX 004/2021")
        self.assertTrue(_doc_has_ref("conforme Resolucao CEPEX 004/2021", matchers))

    def test_law_number(self):
        matchers = build_lexical_matchers("Lei 11.788")
        self.assertTrue(_doc_has_ref("Lei Federal 11.788/2008", matchers))

    def test_no_matchers_for_generic_question(self):
        self.assertEqual(build_lexical_matchers("quantas faltas posso ter?"), [])


if __name__ == "__main__":
    unittest.main()
