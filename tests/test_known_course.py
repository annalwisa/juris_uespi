from chatbot.campi import parse_academic_staff_context
from chatbot.cursos import extract_known_course
from chatbot.history import build_retrieval_query
from chatbot.programs import enhance_retrieval_query
from chatbot.sigaa import get_sigaa_context_for_question


def test_extract_known_course_computacao():
    assert extract_known_course("de computação em teresina") == "computacao"


def test_extract_known_course_direito():
    assert extract_known_course("de direito em picos") == "direito"


def test_extract_known_course_ignores_generic():
    assert extract_known_course("quais cursos em teresina") is None


def test_followup_extracts_course_from_current_question():
    hist = [
        {"role": "user", "content": "quem é o coordenador?"},
        {"role": "assistant", "content": "Informe o curso e a sede."},
    ]
    q = "de computação em teresina"
    sq = enhance_retrieval_query(q, build_retrieval_query(q, hist))
    ctx = parse_academic_staff_context(sq)
    assert ctx["course"] == "computacao"
    assert ctx["campus"] == "Teresina"


def test_followup_sigaa_returns_single_computacao():
    hist = [
        {"role": "user", "content": "quem é o coordenador?"},
        {"role": "assistant", "content": "Informe o curso e a sede."},
    ]
    q = "de computação em teresina"
    sq = enhance_retrieval_query(q, build_retrieval_query(q, hist))
    sigaa = get_sigaa_context_for_question(sq)
    assert "Registros encontrados: 1" in sigaa
    assert "LILIAM BARROSO LEAL" in sigaa
    assert "CIÊNCIA DA COMPUTAÇÃO" in sigaa or "COMPUTA" in sigaa.upper()
