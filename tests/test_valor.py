from dataclasses import dataclass

import pytest
from flask import Flask
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from rachacontas.core.valor import (
    Couvert,
    Desconto,
    Gorjeta,
    GrupoItens,
    Item,
    TaxaServico,
    ValorInvalido,
    aplicar_ajustes,
    detalhamento,
    montar_arvore,
)
from rachacontas.enums import TipoAjuste, TipoDivisao
from rachacontas.models import Ajuste, Base, Despesa, Grupo, Item as ItemModel, Participante
from rachacontas.routes.valor import valor_bp
from rachacontas.schemas.valor import AjusteIn, ItemIn


@dataclass
class LinhaItemFalsa:
    id: int
    parent_id: int | None
    nome: str
    valor: int | None


@dataclass
class LinhaAjusteFalsa:
    tipo: TipoAjuste
    valor: int
    ordem: int


# --- Testes de Domínio e Schemas (Fases 0 e 1) ---


def test_composite_item_e_grupo_aninhado() -> None:
    prato = Item("Moqueca", 8500)
    suco = Item("Suco de Laranja", 1200)
    agua = Item("Água com Gás", 600)

    bebidas = GrupoItens("Bebidas", [suco, agua])
    pedido_mesa = GrupoItens("Mesa 4", [prato, bebidas])

    assert bebidas.total() == 1800
    assert pedido_mesa.total() == 10300


def test_montar_arvore_com_parent_id() -> None:
    linhas = [
        LinhaItemFalsa(id=1, parent_id=None, nome="Combo Jantar", valor=None),
        LinhaItemFalsa(id=2, parent_id=1, nome="Pizza Grande", valor=6000),
        LinhaItemFalsa(id=3, parent_id=1, nome="Bebidas", valor=None),
        LinhaItemFalsa(id=4, parent_id=3, nome="Refrigerante", valor=1000),
        LinhaItemFalsa(id=5, parent_id=3, nome="Cerveja", valor=1500),
        LinhaItemFalsa(id=6, parent_id=None, nome="Sobremesa", valor=2000),
    ]

    arvore = montar_arvore(linhas)

    assert isinstance(arvore, GrupoItens)
    assert arvore.total() == 10500
    combo = arvore.filhos[0]
    assert isinstance(combo, GrupoItens)
    assert combo.total() == 8500


def test_decoradores_pontos_base_arredondamento_meio_para_cima() -> None:
    # 1005 centavos * 10% (1000 bps) = 100,5 -> arredonda meio para cima -> 101
    base = Item("Lanche", 1005)
    com_taxa = TaxaServico(base, pontos_base=1000)
    assert com_taxa.total() == 1106

    # 1004 centavos * 10% (1000 bps) = 100,4 -> arredonda para baixo -> 100
    base_menor = Item("Café", 1004)
    com_gorjeta = Gorjeta(base_menor, pontos_base=1000)
    assert com_gorjeta.total() == 1104


def test_couvert_e_desconto() -> None:
    base = Item("Jantar", 10000)
    com_couvert = Couvert(base, valor=1500)
    com_desconto = Desconto(com_couvert, valor=2500)

    assert com_couvert.total() == 11500
    assert com_desconto.total() == 9000


def test_desconto_negativo_gera_valor_invalido() -> None:
    base = Item("Lanche", 3000)
    decorado = Desconto(base, valor=3001)

    with pytest.raises(ValorInvalido):
        decorado.total()


def test_ordem_dos_ajustes_altera_total() -> None:
    base = Item("Conta", 10000)

    # Ordem 1: Desconto de R$ 20,00 antes da Taxa de 10% -> (10000 - 2000) * 1.10 = 8800
    ajustes_desconto_primeiro = [
        LinhaAjusteFalsa(tipo=TipoAjuste.TAXA_SERVICO, valor=1000, ordem=2),
        LinhaAjusteFalsa(tipo=TipoAjuste.DESCONTO, valor=2000, ordem=1),
    ]

    # Ordem 2: Taxa de 10% antes do Desconto de R$ 20,00 -> (10000 * 1.10) - 2000 = 9000
    ajustes_taxa_primeiro = [
        LinhaAjusteFalsa(tipo=TipoAjuste.TAXA_SERVICO, valor=1000, ordem=1),
        LinhaAjusteFalsa(tipo=TipoAjuste.DESCONTO, valor=2000, ordem=2),
    ]

    total_1 = aplicar_ajustes(base, ajustes_desconto_primeiro).total()
    total_2 = aplicar_ajustes(base, ajustes_taxa_primeiro).total()

    assert total_1 == 8800
    assert total_2 == 9000
    assert total_1 != total_2


def test_detalhamento() -> None:
    base = GrupoItens("Mesa", [Item("Prato", 10000)])
    ajustes = [
        LinhaAjusteFalsa(tipo=TipoAjuste.COUVERT, valor=1000, ordem=1),
        LinhaAjusteFalsa(tipo=TipoAjuste.TAXA_SERVICO, valor=1000, ordem=2),
        LinhaAjusteFalsa(tipo=TipoAjuste.DESCONTO, valor=500, ordem=3),
    ]

    decorado = aplicar_ajustes(base, ajustes)
    info = detalhamento(decorado)

    assert info.subtotal == 10000
    assert len(info.ajustes) == 3
    assert info.ajustes[0].total_parcial == 11000
    assert info.ajustes[0].diferenca == 1000
    assert info.ajustes[1].total_parcial == 12100
    assert info.ajustes[1].diferenca == 1100
    assert info.ajustes[2].total_parcial == 11600
    assert info.ajustes[2].diferenca == -500
    assert info.total == 11600


def test_schemas_entrada_recursivos() -> None:
    payload = ItemIn(
        nome="Combo",
        filhos=[
            ItemIn(nome="Hambúrguer", valor=3500, consumidores=[1, 2]),
            ItemIn(nome="Batata", valor=1500),
        ],
    )
    ajuste = AjusteIn(tipo=TipoAjuste.TAXA_SERVICO, valor=1000, ordem=1)

    assert len(payload.filhos) == 2
    assert ajuste.valor == 1000

    with pytest.raises(ValidationError):
        ItemIn(nome="Item sem valor e sem filhos")


# --- Testes de Serviço e Rota Flask (Fase 2) ---


@pytest.fixture
def app_cliente():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SESSION_LOCAL"] = TestingSessionLocal
    app.register_blueprint(valor_bp)

    with TestingSessionLocal() as session:
        yield app.test_client(), session

    engine.dispose()


def _criar_despesa_base(session: Session, *, excluida: bool = False) -> Despesa:
    grupo = Grupo(nome="Viagem Praia")
    session.add(grupo)
    session.flush()

    pagador = Participante(grupo_id=grupo.id, nome="Gustavo")
    session.add(pagador)
    session.flush()

    despesa = Despesa(
        grupo_id=grupo.id,
        pagador_id=pagador.id,
        descricao="Almoço",
        tipo_divisao=TipoDivisao.IGUAL,
        params_divisao={},
        excluida=excluida,
    )
    session.add(despesa)
    session.flush()
    return despesa


def test_rota_valor_despesa_com_arvore_e_ajustes(app_cliente) -> None:
    client, session = app_cliente
    despesa = _criar_despesa_base(session)

    combo = ItemModel(despesa_id=despesa.id, parent_id=None, nome="Combo", valor=None)
    session.add(combo)
    session.flush()

    session.add_all(
        [
            ItemModel(despesa_id=despesa.id, parent_id=combo.id, nome="Prato", valor=8000),
            ItemModel(despesa_id=despesa.id, parent_id=combo.id, nome="Suco", valor=2000),
            Ajuste(despesa_id=despesa.id, tipo=TipoAjuste.COUVERT, valor=1000, ordem=1),
            Ajuste(despesa_id=despesa.id, tipo=TipoAjuste.TAXA_SERVICO, valor=1000, ordem=2),
            Ajuste(despesa_id=despesa.id, tipo=TipoAjuste.DESCONTO, valor=500, ordem=3),
        ]
    )
    session.commit()

    resposta = client.get(f"/despesas/{despesa.id}/valor")

    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados == {
        "despesa_id": despesa.id,
        "subtotal": 10000,
        "ajustes": [
            {
                "tipo": "couvert",
                "ordem": 1,
                "valor_ajuste": 1000,
                "diferenca": 1000,
                "total_parcial": 11000,
            },
            {
                "tipo": "taxa_servico",
                "ordem": 2,
                "valor_ajuste": 1000,
                "diferenca": 1100,
                "total_parcial": 12100,
            },
            {
                "tipo": "desconto",
                "ordem": 3,
                "valor_ajuste": 500,
                "diferenca": -500,
                "total_parcial": 11600,
            },
        ],
        "total": 11600,
    }


def test_rota_valor_despesa_inexistente_ou_excluida_retorna_404(app_cliente) -> None:
    client, session = app_cliente
    despesa_excluida = _criar_despesa_base(session, excluida=True)
    session.commit()

    assert client.get("/despesas/9999/valor").status_code == 404
    assert client.get(f"/despesas/{despesa_excluida.id}/valor").status_code == 404


def test_rota_valor_desconto_maior_que_subtotal_retorna_422(app_cliente) -> None:
    client, session = app_cliente
    despesa = _criar_despesa_base(session)
    session.add_all(
        [
            ItemModel(despesa_id=despesa.id, parent_id=None, nome="Café", valor=1000),
            Ajuste(despesa_id=despesa.id, tipo=TipoAjuste.DESCONTO, valor=1500, ordem=1),
        ]
    )
    session.commit()

    resposta = client.get(f"/despesas/{despesa.id}/valor")

    assert resposta.status_code == 422
    assert "erro" in resposta.get_json()