import pytest

from rachacontas.core.adaptadores import (
    AdaptadorCsvBanco,
    AdaptadorPlanilhaGenerica,
    reais_para_centavos,
)
from rachacontas.core.importacao import ErroImportacao, GastoImportado


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
    conteudo = 'Data,Descrição,Valor\n26/11/2026,Açaí da praça,"15,50"\n'.encode("latin-1")

    gastos = AdaptadorCsvBanco().ler(conteudo)

    assert gastos == [GastoImportado(descricao="Açaí da praça", valor=1550, linha=2)]


def test_adaptador_planilha_generica_aceita_separador_virgula() -> None:
    conteudo = (
        "item,preco,pagador\n"
        "Porção de batata,35.00,Carol\n"
        "Cerveja,18.50,Murilo\n"
    ).encode("utf-8")

    gastos = AdaptadorPlanilhaGenerica().ler(conteudo)

    assert gastos == [
        GastoImportado(descricao="Porção de batata", valor=3500, linha=2, pagador="Carol"),
        GastoImportado(descricao="Cerveja", valor=1850, linha=3, pagador="Murilo"),
    ]


def test_adaptador_planilha_generica_aceita_tsv_e_arquivo_vazio() -> None:
    conteudo = "Nome\tTotal\tNome do Pagador\nÁgua\t5,00\tGustavo\n".encode("utf-8")

    assert AdaptadorPlanilhaGenerica().ler(conteudo) == [
        GastoImportado(descricao="Água", valor=500, linha=2, pagador="Gustavo"),
    ]
    assert AdaptadorPlanilhaGenerica().ler(b"   \n") == []


def test_adaptador_erro_quando_falta_coluna_obrigatoria() -> None:
    with pytest.raises(ValueError, match="Coluna obrigatória"):
        AdaptadorCsvBanco().ler("data;outro\n2026-11-26;10,00\n".encode("utf-8"))

    with pytest.raises(ValueError, match="Coluna obrigatória"):
        AdaptadorCsvBanco().ler("descricao;valor\nAlmoço;10,00\n".encode("utf-8"))

    with pytest.raises(ValueError, match="Coluna obrigatória"):
        AdaptadorPlanilhaGenerica().ler("item;valor\nCerveja;10,00\n".encode("utf-8"))


def test_adaptador_acumula_erros_por_linha_em_erro_importacao() -> None:
    conteudo = (
        "item;valor;pagador\n"
        ";10,00;Carol\n"
        "Cerveja;gratis;Murilo\n"
        "Pizza;50,00;\n"
    ).encode("utf-8")

    with pytest.raises(ErroImportacao) as exc_info:
        AdaptadorPlanilhaGenerica().ler(conteudo)

    assert len(exc_info.value.erros) == 3
    assert "Linha 2" in exc_info.value.erros[0]
    assert "Linha 3" in exc_info.value.erros[1]
    assert "Linha 4" in exc_info.value.erros[2]


def test_gasto_importado_mantem_compatibilidade_sem_pagador() -> None:
    gasto = GastoImportado("Almoço", 1000, 1)
    assert gasto.pagador is None
