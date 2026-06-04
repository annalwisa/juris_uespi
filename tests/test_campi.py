from chatbot.campi import extract_campus


def test_cies_with_city_resolves_campus():
    assert extract_campus("coordenador de administração no CIES de Floriano") == "Floriano"
    assert extract_campus("cies em parnaiba") == "Parnaíba"
    assert extract_campus("cies clovis moura") == "Teresina"
    assert extract_campus("centro integrado de ensino superior em campo maior") == "Campo Maior"


def test_cies_without_city_does_not_resolve():
    assert extract_campus("coordenador do cies") is None


def test_regular_campus_aliases_still_work():
    assert extract_campus("coordenador de computação do ctu") == "Teresina"
    assert extract_campus("direito em piripiri") == "Piripiri"
