import pytest

from rachacontas.core.falsos import ValorFixo
from rachacontas.core.fechamento import (
    DespesaFechamento,
    FacadeFechamento,
    ResultadoFechamento,
    Transferencia,
    calcular_saldos,
    quitar,
)


def test_calcular_saldos_com_falsos_soma_sempre_zero() -> None:
    despesas = [
        DespesaFechamento(pagador_id=1, componente=ValorFixo(9000), participantes=[1, 2, 3]),
        DespesaFechamento(pagador_id=2, componente=ValorFixo(3000), participantes=[1, 2, 3]),
    ]

    saldos = calcular_saldos(despesas, participantes=[1, 2, 3])

    assert saldos == {1: 5000, 2: -1000, 3: -4000}
    assert sum(saldos.values()) == 0


def test_calcular_saldos_ignora_despesas_excluidas() -> None:
    despesas = [
        DespesaFechamento(pagador_id=1, componente=ValorFixo(6000), participantes=[1, 2]),
        DespesaFechamento(
            pagador_id=2,
            componente=ValorFixo(4000),
            participantes=[1, 2],
            excluida=True,
        ),
    ]

    saldos = calcular_saldos(despesas, participantes=[1, 2])

    assert saldos == {1: 3000, 2: -3000}
    assert sum(saldos.values()) == 0


def test_quitar_cenario_fixo_tres_pessoas_maximo_n_menos_1_transferencias() -> None:
    saldos = {1: 6000, 2: -3000, 3: -3000}

    transferencias = quitar(saldos)

    assert len(transferencias) <= len(saldos) - 1
    assert transferencias == [
        Transferencia(de=2, para=1, valor=3000),
        Transferencia(de=3, para=1, valor=3000),
    ]


def test_quitar_guloso_pareia_maior_credor_com_maior_devedor() -> None:
    saldos = {1: 5000, 2: 2000, 3: -4000, 4: -3000}

    transferencias = quitar(saldos)

    assert len(transferencias) <= len(saldos) - 1
    assert transferencias[0] == Transferencia(de=3, para=1, valor=4000)

    saldos_finais = dict(saldos)
    for t in transferencias:
        saldos_finais[t.de] += t.valor
        saldos_finais[t.para] -= t.valor
    assert all(valor == 0 for valor in saldos_finais.values())


def test_quitar_com_saldos_zerados_retorna_vazio() -> None:
    assert quitar({1: 0, 2: 0, 3: 0}) == []


def test_quitar_soma_nao_zero_gera_erro() -> None:
    with pytest.raises(ValueError, match="soma dos saldos"):
        quitar({1: 100, 2: -50})


def test_facade_fechamento_calcula_saldos_e_quitacao() -> None:
    facade = FacadeFechamento()
    despesas = [
        DespesaFechamento(pagador_id=1, componente=ValorFixo(10000), participantes=[1, 2, 3]),
    ]

    resultado = facade.fechar(despesas, participantes=[1, 2, 3])

    assert isinstance(resultado, ResultadoFechamento)
    assert sum(resultado.saldos.values()) == 0
    assert resultado.saldos == {1: 6666, 2: -3333, 3: -3333}
    assert resultado.transferencias == [
        Transferencia(de=2, para=1, valor=3333),
        Transferencia(de=3, para=1, valor=3333),
    ]
