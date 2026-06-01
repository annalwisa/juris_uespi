import unittest

from chatbot.moderation import contains_prohibited_language, is_message_allowed


class TestModeration(unittest.TestCase):
    def test_clean_academic_question(self):
        self.assertFalse(contains_prohibited_language("Qual o máximo de faltas na UESPI?"))
        self.assertTrue(is_message_allowed("Onde fica o campus de Teresina?"))

    def test_blocks_profanity(self):
        self.assertTrue(contains_prohibited_language("que porra de edital"))
        self.assertFalse(is_message_allowed("vai se foder"))

    def test_blocks_leetspeak(self):
        self.assertTrue(contains_prohibited_language("p0rra"))

    def test_curso_not_blocked(self):
        self.assertFalse(contains_prohibited_language("lista de cursos da UESPI"))


if __name__ == "__main__":
    unittest.main()
