import pytest

from rachacontas.core.comandos import (
    CriarDespesa,
    EditarDespesa,
    Evento,
    ExcluirDespesa,
    GerenciadorComandos,
)
from rachacontas.core.falsos import ObservadorFalso, RepositorioDespesasEmMemoria
from rachacontas.enums import TipoEvento


def test_desfazer_criacao_marca_apenas_a_despesa_criada():
    repo = RepositorioDespesasEmMemoria()
    estado = {"descricao": "Mercado"}
    id_existente = repo.criar(estado)
    comando = CriarDespesa(repo, estado)

    comando.desfazer()
    comando.executar()
    comando.desfazer()

    assert repo.buscar(id_existente) == estado
    assert repo.buscar(id_existente + 1) == {**estado, "excluida": True}


def test_desfazer_exclusao_restaura_estado_original():
    repo = RepositorioDespesasEmMemoria()
    estado = {"descricao": "Mercado", "excluida": False}
    despesa_id = repo.criar(estado)
    comando = ExcluirDespesa(repo, despesa_id)

    comando.executar()
    assert repo.buscar(despesa_id) == {**estado, "excluida": True}

    comando.desfazer()
    assert repo.buscar(despesa_id) == estado


def test_editar_e_desfazer_estado_sem_flag_de_exclusao():
    repo = RepositorioDespesasEmMemoria()
    estado = {"descricao": "Mercado"}
    despesa_id = repo.criar(estado)
    novo_estado = {"descricao": "Feira"}
    comando = EditarDespesa(repo, despesa_id, novo_estado)

    comando.executar()
    assert repo.buscar(despesa_id) == novo_estado

    comando.desfazer()
    assert repo.buscar(despesa_id) == estado


@pytest.mark.parametrize(
    ("classe", "args"),
    [(EditarDespesa, ({"descricao": "Feira"},)), (ExcluirDespesa, ())],
)
def test_desfazer_sem_execucao_preserva_estado(classe, args):
    repo = RepositorioDespesasEmMemoria()
    estado = {"descricao": "Mercado", "excluida": False}
    despesa_id = repo.criar(estado)

    classe(repo, despesa_id, *args).desfazer()

    assert repo.buscar(despesa_id) == estado


@pytest.mark.parametrize(
    ("classe", "args"),
    [(EditarDespesa, ({"descricao": "Feira"},)), (ExcluirDespesa, ())],
)
def test_desfazer_apos_falha_ao_salvar_preserva_estado(monkeypatch, classe, args):
    repo = RepositorioDespesasEmMemoria()
    despesa_id = repo.criar({"descricao": "Mercado", "excluida": False})
    comando = classe(repo, despesa_id, *args)

    def falhar_ao_salvar(despesa_id, estado):
        raise OSError("falha ao salvar")

    with monkeypatch.context() as patch:
        patch.setattr(repo, "salvar", falhar_ao_salvar)
        with pytest.raises(OSError, match="falha ao salvar"):
            comando.executar()

    estado_atual = {"descricao": "Padaria", "excluida": False}
    repo.salvar(despesa_id, estado_atual)
    comando.desfazer()

    assert repo.buscar(despesa_id) == estado_atual


def test_observadores_recebem_eventos_de_execucao_desfazer_e_refazer():
    repo = RepositorioDespesasEmMemoria()
    gerenciador = GerenciadorComandos()
    primeiro, segundo = ObservadorFalso(), ObservadorFalso()
    gerenciador.inscrever(primeiro)
    gerenciador.inscrever(segundo)
    gerenciador.inscrever(segundo)
    grupo_id = 10

    criacao = gerenciador.executar(grupo_id, CriarDespesa(repo, {"descricao": "Mercado"}))
    assert criacao is not None
    despesa_id = criacao.despesa_id
    gerenciador.executar(grupo_id, EditarDespesa(repo, despesa_id, {"descricao": "Feira"}))
    gerenciador.executar(grupo_id, ExcluirDespesa(repo, despesa_id))

    assert repo.buscar(despesa_id) == {"descricao": "Feira", "excluida": True}
    gerenciador.desfazer(grupo_id)
    assert repo.buscar(despesa_id) == {"descricao": "Feira"}
    gerenciador.desfazer(grupo_id)
    assert repo.buscar(despesa_id) == {"descricao": "Mercado"}
    gerenciador.desfazer(grupo_id)
    assert repo.buscar(despesa_id) == {"descricao": "Mercado", "excluida": True}

    gerenciador.desinscrever(segundo)
    gerenciador.refazer(grupo_id)
    assert repo.buscar(despesa_id) == {"descricao": "Mercado"}
    assert repo.buscar(despesa_id + 1) is None
    gerenciador.refazer(grupo_id)
    gerenciador.refazer(grupo_id)
    assert repo.buscar(despesa_id) == {"descricao": "Feira", "excluida": True}

    tipos = [
        TipoEvento.DESPESA_CRIADA,
        TipoEvento.DESPESA_EDITADA,
        TipoEvento.DESPESA_EXCLUIDA,
        TipoEvento.DESPESA_RESTAURADA,
        TipoEvento.DESPESA_EDITADA,
        TipoEvento.DESPESA_EXCLUIDA,
        TipoEvento.DESPESA_RESTAURADA,
        TipoEvento.DESPESA_EDITADA,
        TipoEvento.DESPESA_EXCLUIDA,
    ]
    eventos = [Evento(tipo, grupo_id, despesa_id) for tipo in tipos]
    assert primeiro.eventos == eventos
    assert segundo.eventos == eventos[:6]


def test_comando_novo_limpa_refazer_apenas_do_proprio_grupo():
    repo = RepositorioDespesasEmMemoria()
    gerenciador = GerenciadorComandos()
    estado = {"descricao": "Mercado"}
    gerenciador.executar(10, CriarDespesa(repo, estado))
    evento_outro_grupo = gerenciador.executar(20, CriarDespesa(repo, estado))
    assert evento_outro_grupo is not None
    gerenciador.desfazer(10)
    gerenciador.desfazer(20)

    gerenciador.executar(10, CriarDespesa(repo, {"descricao": "Feira"}))

    assert gerenciador.refazer(10) is None
    assert gerenciador.refazer(20) == Evento(
        TipoEvento.DESPESA_RESTAURADA, 20, evento_outro_grupo.despesa_id
    )


def test_operacao_sem_alteracao_ou_com_falha_preserva_refazer_e_nao_notifica(monkeypatch):
    repo = RepositorioDespesasEmMemoria()
    gerenciador = GerenciadorComandos()
    observador = ObservadorFalso()
    gerenciador.inscrever(observador)
    criacao = gerenciador.executar(10, CriarDespesa(repo, {"descricao": "Mercado"}))
    assert criacao is not None
    despesa_id = criacao.despesa_id
    exclusao = gerenciador.desfazer(10)

    assert gerenciador.executar(10, ExcluirDespesa(repo, despesa_id)) is None
    assert gerenciador.executar(10, EditarDespesa(repo, despesa_id + 1, {})) is None
    assert gerenciador.desfazer(10) is None

    def falhar_ao_salvar(despesa_id, estado):
        raise OSError("falha ao salvar")

    with monkeypatch.context() as patch:
        patch.setattr(repo, "salvar", falhar_ao_salvar)
        with pytest.raises(OSError, match="falha ao salvar"):
            gerenciador.refazer(10)

    assert observador.eventos == [criacao, exclusao]
    assert gerenciador.refazer(10) == Evento(TipoEvento.DESPESA_RESTAURADA, 10, despesa_id)
