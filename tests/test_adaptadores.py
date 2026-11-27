import pytest

from rachacontas.core.adaptadores import (
    AdaptadorCsvBanco,
    AdaptadorPlanilhaGenerica,
    reais_para_centavos,
)
from rachacontas.core.importacao import GastoImportado


def test_reais_para_centavos_formatos_comuns() -> None:
    assert reais_para_centavos("45,90") == 4590
    assert reais_para_centavos("45.90") == 4590
    assert reais_para_centavos("R$ 1.234,56") == 123456
    assert reais_para_centavos("1,234.56") == 123456
    assert reais_para_centavos("19.99") == 1999


def test_reais_para_centavos_invalido_gera_erro() -> None:
    with pytest.raises(ValueError):
        reais_para_centavos("")
    with pytest.raises(ValueError):
        reais_para_centavos("abc")


def test_adaptador_csv_banco_retorna_gastos_em_centavos() -> None:
    conteudo = (
        "data;estabelecimento;valor\n"
        "2026-11-26;Bar do Zé;R$ 89,50\n"
        "\n"
        "2026-11-26;Uber volta;24,00\n"
    ).encode("utf-8")

    gastos = AdaptadorCsvBanco().ler(conteudo)

    assert gastos == [
        GastoImportado(descricao="Bar do Zé", valor=8950, linha=2),
        GastoImportado(descricao="Uber volta", valor=2400, linha=4),
    ]


def test_adaptador_csv_banco_aceita_latin1() -> None:
    conteudo = 'Descrição,Valor\nAçaí da praça,"15,50"\n'.encode("latin-1")

    gastos = AdaptadorCsvBanco().ler(conteudo)

    assert gastos == [GastoImportado(descricao="Açaí da praça", valor=1550, linha=2)]


def test_adaptador_planilha_generica_aceita_separador_virgula() -> None:
    conteudo = (
        "item,preco\n"
        "Porção de batata,35.00\n"
        "Cerveja,18.50\n"
    ).encode("utf-8")

    gastos = AdaptadorPlanilhaGenerica().ler(conteudo)

    assert gastos == [
        GastoImportado(descricao="Porção de batata", valor=3500, linha=2),
        GastoImportado(descricao="Cerveja", valor=1850, linha=3),
    ]


def test_adaptador_planilha_generica_aceita_tsv_e_arquivo_vazio() -> None:
    conteudo = "Nome\tTotal\nÁgua\t5,00\n".encode("utf-8")

    assert AdaptadorPlanilhaGenerica().ler(conteudo) == [
        GastoImportado(descricao="Água", valor=500, linha=2),
    ]
    assert AdaptadorPlanilhaGenerica().ler(b"   \n") == []


def test_adaptador_erro_quando_falta_coluna_ou_valor_invalido() -> None:
    with pytest.raises(ValueError, match="Coluna obrigatória"):
        AdaptadorCsvBanco().ler("data;outro\n2026-11-26;10,00\n".encode("utf-8"))

    with pytest.raises(ValueError, match="Linha 2"):
        AdaptadorPlanilhaGenerica().ler("item;valor\nCerveja;gratis\n".encode("utf-8"))
