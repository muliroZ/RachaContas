from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from rachacontas.core.fechamento import DespesaFechamento, FacadeFechamento
from rachacontas.core.valor import ErroDominio, aplicar_ajustes, montar_arvore
from rachacontas.models import Despesa, Grupo, Item
from rachacontas.schemas.fechamento import FechamentoOut, TransferenciaOut


class GrupoNaoEncontrado(ErroDominio):
    """Lançada quando o grupo solicitado não existe."""


def _buscar_grupo_completo(db: Session, grupo_id: int) -> Grupo:
    stmt = (
        select(Grupo)
        .options(
            selectinload(Grupo.participantes),
            selectinload(Grupo.despesas).selectinload(Despesa.itens).selectinload(Item.consumidores),
            selectinload(Grupo.despesas).selectinload(Despesa.ajustes),
        )
        .where(Grupo.id == grupo_id)
    )
    grupo = db.scalar(stmt)
    if grupo is None:
        raise GrupoNaoEncontrado(f"Grupo {grupo_id} não encontrado.")
    return grupo


def fechar_grupo(db: Session, grupo_id: int) -> FechamentoOut:
    """Calcula saldos e transferências mínimas para quitar as despesas de um grupo."""
    grupo = _buscar_grupo_completo(db, grupo_id)
    participantes_ids = [participante.id for participante in grupo.participantes]

    despesas_fechamento = [
        DespesaFechamento(
            pagador_id=despesa.pagador_id,
            componente=aplicar_ajustes(montar_arvore(despesa.itens), despesa.ajustes),
            participantes=participantes_ids,
            itens=despesa.itens,
            params_divisao=despesa.params_divisao,
            excluida=despesa.excluida,
            tipo_divisao=despesa.tipo_divisao,
        )
        for despesa in grupo.despesas
        if not despesa.excluida
    ]

    resultado = FacadeFechamento().fechar(
        despesas=despesas_fechamento,
        participantes=participantes_ids,
    )

    return FechamentoOut(
        grupo_id=grupo_id,
        saldos=resultado.saldos,
        transferencias=[
            TransferenciaOut(de=t.de, para=t.para, valor=t.valor)
            for t in resultado.transferencias
        ],
    )
