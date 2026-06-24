from chatbot.gestao import (
    clear_data_cache,
    format_gestao_context,
    get_gestao_context,
    is_gestao_question,
    load_gestao_data,
    parse_agenda_html,
    parse_gestao_context,
)

AGENDA_FIXTURE = """
<html><body>
<h2>Contatos</h2>
<h2>Direções de Campi</h2>
<h4>CTU- Centro de Tecnologia e Urbanismo</h4>
<p>Diretora: Artemaria Coelho de Andrade</p>
<p>E-mail:direcao@ctu.uespi.br| artemaria.andadre@ctu.uespi.br</p>
<p>Diretora: Simonelly Valéria dos Santos Melo</p>
<p>E-mail:direcao@ccm.uespi.br| simonellyvaleria@ccm.uespi.br</p>
<h4>Barras</h4>
<p>Coordenadora: Maria José de Oliveira Calaça Araújo</p>
<p>E-mail: mariajose.calaca@uespi.br</p>
</body></html>
"""


def _use_fixture(monkeypatch, tmp_path):
    cache_file = tmp_path / "gestao_agenda.json"
    monkeypatch.setattr("chatbot.gestao.CACHE_FILE", cache_file)
    monkeypatch.setattr(
        "chatbot.gestao._fetch_agenda_html", lambda: AGENDA_FIXTURE
    )
    clear_data_cache()


def test_parse_agenda_html_extracts_centro_campus_nucleo():
    data = parse_agenda_html(AGENDA_FIXTURE)
    assert len(data["centros"]) == 1
    assert data["centros"][0]["sigla"] == "CTU"
    assert data["centros"][0]["nome_pessoa"] == "Artemaria Coelho de Andrade"
    assert len(data["campi"]) == 1
    assert data["campi"][0]["cidade"] == "Teresina"
    assert "Simonelly" in data["campi"][0]["nome_pessoa"]
    assert len(data["nucleos"]) == 1
    assert data["nucleos"][0]["cidade"] == "Barras"


def test_is_gestao_question_ctu():
    assert is_gestao_question("quem é o diretor do CTU?")
    assert is_gestao_question("quem é a diretora do CTU?")
    assert is_gestao_question("diretor do centro de tecnologia e urbanismo")


def test_is_not_gestao_for_coordenador():
    assert not is_gestao_question("quem é o coordenador do curso de computação?")
    assert not is_gestao_question("coordenadora de direito no campus de Piripiri")


def test_is_not_gestao_for_reitoria():
    assert not is_gestao_question("quem é o reitor da UESPI?")


def test_ctu_director_in_context(monkeypatch, tmp_path):
    _use_fixture(monkeypatch, tmp_path)
    ctx = format_gestao_context("quem é a diretora do CTU?")
    assert "Artemaria Coelho de Andrade" in ctx
    assert "CTU" in ctx
    assert "Diretora" in ctx
    assert "agenda telefônica" in ctx.lower() or "agenda telefonica" in ctx.lower()


def test_get_gestao_context_applies(monkeypatch, tmp_path):
    _use_fixture(monkeypatch, tmp_path)
    ctx = get_gestao_context("quem é o diretor do CTU?")
    assert "Artemaria Coelho de Andrade" in ctx
    assert "Não se aplica" not in ctx


def test_get_gestao_context_skips_irrelevant(monkeypatch, tmp_path):
    _use_fixture(monkeypatch, tmp_path)
    ctx = get_gestao_context("quantas faltas posso ter?")
    assert "Não se aplica" in ctx


def test_parse_gestao_context_finds_ctu(monkeypatch, tmp_path):
    _use_fixture(monkeypatch, tmp_path)
    ctx = parse_gestao_context("diretora do CTU")
    assert ctx["is_gestao"]
    assert ctx["centro"]["sigla"] == "CTU"


def test_load_gestao_data_uses_cache(monkeypatch, tmp_path):
    _use_fixture(monkeypatch, tmp_path)
    first = load_gestao_data(force_refresh=True)
    calls = {"n": 0}

    def boom():
        calls["n"] += 1
        raise RuntimeError("should use cache")

    monkeypatch.setattr("chatbot.gestao._fetch_agenda_html", boom)
    second = load_gestao_data()
    assert calls["n"] == 0
    assert second["centros"][0]["sigla"] == first["centros"][0]["sigla"]
