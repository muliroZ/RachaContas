from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from rachacontas.core.divisao import EstrategiaDivisao, ItemDivisao
from rachacontas.core.falsos import IgualFalsa
from rachacontas.core.valor import ComponenteDespesa


@dataclass(frozen=True)
class Transferencia:
    de: int
    para: int
    valor: int


@dataclass(frozen=True)
class DespesaFechamento:
    pagador_id: int
    componente: ComponenteDespesa
    participantes: list[int]
    itens: Sequence[ItemDivisao] = ()
    params_divisao: dict[str, object] = field(default_factory=dict)
    estrategia: EstrategiaDivisao | None = None
    excluida: bool = False


@dataclass(frozen=True)
class ResultadoFechamento:
    saldos: dict[int, int]
    transferencias: list[Transferencia]


def calcular_saldos(
    despesas: Iterable[DespesaFechamento],
    participantes: Iterable[int] = (),
    estrategia_padrao: EstrategiaDivisao | None = None,
) -> dict[int, int]:
    """Calcula o saldo líquido (pago - devido) de cada participante em centavos."""
    saldos: dict[int, int] = {pid: 0 for pid in dict.fromkeys(participantes)}
    estrategia_default = estrategia_padrao or IgualFalsa()

    for despesa in despesas:
        if despesa.excluida:
            continue

        total = despesa.componente.total()
        if total < 0:
            raise ValueError("O total da despesa não pode ser negativo.")

        estrategia = despesa.estrategia or estrategia_default
        ids_participantes = despesa.participantes or list(saldos.keys())
        parcelas = estrategia.dividir(
            total=total,
            participantes=ids_participantes,
            itens=despesa.itens,
            params=despesa.params_divisao,
        )

        saldos.setdefault(despesa.pagador_id, 0)
        saldos[despesa.pagador_id] += total

        for participante_id, valor_devido in parcelas.items():
            saldos.setdefault(participante_id, 0)
            saldos[participante_id] -= valor_devido

    return saldos


def quitar(saldos: dict[int, int]) -> list[Transferencia]:
    """Calcula as transferências mínimas pelo algoritmo guloso (maior credor com maior devedor)."""
    if sum(saldos.values()) != 0:
        raise ValueError("A soma dos saldos deve ser zero para realizar a quitação.")

    credores: list[list[int]] = [[pid, saldo] for pid, saldo in saldos.items() if saldo > 0]
    devedores: list[list[int]] = [[pid, -saldo] for pid, saldo in saldos.items() if saldo < 0]

    transferencias: list[Transferencia] = []
    while credores and devedores:
        credores.sort(key=lambda item: (-item[1], item[0]))
        devedores.sort(key=lambda item: (-item[1], item[0]))

        credor_id, credito = credores[0]
        devedor_id, debito = devedores[0]
        valor = min(credito, debito)

        transferencias.append(Transferencia(de=devedor_id, para=credor_id, valor=valor))

        if credito == valor:
            credores.pop(0)
        else:
            credores[0][1] -= valor

        if debito == valor:
            devedores.pop(0)
        else:
            devedores[0][1] -= valor

    return transferencias


class FacadeFechamento:
    """Facade de domínio para cálculo de saldos e quitação de um grupo."""

    def __init__(self, estrategia_padrao: EstrategiaDivisao | None = None) -> None:
        self.estrategia_padrao = estrategia_padrao or IgualFalsa()

    def calcular_saldos(
        self,
        despesas: Iterable[DespesaFechamento],
        participantes: Iterable[int] = (),
    ) -> dict[int, int]:
        return calcular_saldos(
            despesas=despesas,
            participantes=participantes,
            estrategia_padrao=self.estrategia_padrao,
        )

    def fechar(
        self,
        despesas: Iterable[DespesaFechamento],
        participantes: Iterable[int] = (),
    ) -> ResultadoFechamento:
        saldos = self.calcular_saldos(despesas=despesas, participantes=participantes)
        transferencias = quitar(saldos)
        return ResultadoFechamento(saldos=saldos, transferencias=transferencias)
