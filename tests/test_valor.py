from dataclasses import dataclass

import pytest
from pydantic import ValidationError

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
from rachacontas.enums import TipoAjuste
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