from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from rachacontas.core.valor import (
    ComponenteDespesa,
    ErroDominio,
    aplicar_ajustes,
    detalhamento,
    montar_arvore,
)
from rachacontas.models import Despesa
from rachacontas.schemas.valor import DetalheAjusteOut, ValorDespesaOut


class DespesaNaoEncontrada(ErroDominio):
    """Lançada quando a despesa não existe ou foi excluída logicamente."""


def _buscar_despesa_ativa(db: Session, despesa_id: int) -> Despesa:
    stmt = (
        select(Despesa)
        .options(selectinload(Despesa.itens), selectinload(Despesa.ajustes))
        .where(Despesa.id == despesa_id)
    )
    despesa = db.scalar(stmt)
    if despesa is None or despesa.excluida:
        raise DespesaNaoEncontrada(f"Despesa {despesa_id} não encontrada.")
    return despesa


def construir_componente_despesa(db: Session, despesa_id: int) -> ComponenteDespesa:
    """Monta a árvore Composite de itens e aplica os Decorators de ajuste da despesa."""
    despesa = _buscar_despesa_ativa(db, despesa_id)
    arvore = montar_arvore(despesa.itens)
    return aplicar_ajustes(arvore, despesa.ajustes)


def calcular_valor_despesa(db: Session, despesa_id: int) -> ValorDespesaOut:
    """Calcula subtotal, passos de ajuste e total final em centavos para uma despesa."""
    componente = construir_componente_despesa(db, despesa_id)
    info = detalhamento(componente)

    return ValorDespesaOut(
        despesa_id=despesa_id,
        subtotal=info.subtotal,
        ajustes=[
            DetalheAjusteOut(
                tipo=passo.tipo,
                ordem=passo.ordem,
                valor_ajuste=passo.valor_ajuste,
                diferenca=passo.diferenca,
                total_parcial=passo.total_parcial,
            )
            for passo in info.ajustes
        ],
        total=info.total,
    )