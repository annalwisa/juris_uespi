from chatbot.cursos import (
    _iter_courses,
    format_cursos_context,
    get_cursos_context,
    is_cursos_centro_question,
)


def test_detects_center_questions():
    assert is_cursos_centro_question("a qual centro pertence o bacharelado em direito?")
    assert is_cursos_centro_question("quais bacharelados tem no CTU?")
    assert is_cursos_centro_question("o curso de medicina fica em qual centro?")
    assert is_cursos_centro_question("quais licenciaturas tem em picos?")


def test_ignores_unrelated_questions():
    assert not is_cursos_centro_question("quantas faltas posso ter?")
    assert get_cursos_context("qual o valor da bolsa?") == "(Não se aplica a esta pergunta.)"


def test_course_center_grade_mapping():
    pares = {(curso, sigla, grau) for _, _, sigla, _, curso, grau in _iter_courses()}
    assert ("Ciências da Computação", "CTU", "Bacharelado") in pares
    assert ("Medicina", "CCS", "Bacharelado") in pares
    assert ("Direito", "CCSA", "Bacharelado") in pares
    assert ("Pedagogia", "CCECA", "Licenciatura") in pares
    # tecnólogos do CTU
    assert ("Energias Renováveis", "CTU", "Tecnologia") in pares
    assert ("Sistemas para Internet", "CTU", "Tecnologia") in pares
    # cursos sem rótulo na página (Parnaíba)
    assert ("Filosofia", "CIES", "Não informado") in pares
    assert ("Ciências Sociais", "CIES", "Não informado") in pares


def test_context_lists_all_grades():
    ctx = format_cursos_context("cursos por centro")
    assert "Bacharelados:" in ctx
    assert "Licenciaturas:" in ctx
    assert "Tecnólogos:" in ctx
    assert "Outros (grau não informado na página):" in ctx
    assert "Energias Renováveis" in ctx
    assert "Filosofia" in ctx
