import pytest

from rachacontas.core.comandos import CriarDespesa, EditarDespesa, ExcluirDespesa
from rachacontas.core.falsos import RepositorioDespesasEmMemoria


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
