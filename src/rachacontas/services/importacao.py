from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from rachacontas.core.adaptadores import AdaptadorCsvBanco, AdaptadorPlanilhaGenerica
from rachacontas.core.importacao import ErroImportacao, FonteGastos, GastoImportado
from rachacontas.enums import FormatoImportacao, TipoDivisao
from rachacontas.models import Despesa, Grupo, Item
from rachacontas.schemas.importacao import GastoImportadoOut, ImportacaoOut
from rachacontas.services.fechamento import GrupoNaoEncontrado

ADAPTADORES_POR_FORMATO: dict[FormatoImportacao, type[FonteGastos]] = {
    FormatoImportacao.CSV_BANCO: AdaptadorCsvBanco,
    FormatoImportacao.PLANILHA_GENERICA: AdaptadorPlanilhaGenerica,
}


def _resolver_pagador_id(
    gasto: GastoImportado,
    participantes_por_nome: dict[str, int],
    pagador_padrao_id: int | None,
) -> int:
    if gasto.pagador is not None:
        chave = gasto.pagador.strip().lower()
        if chave in participantes_por_nome:
            return participantes_por_nome[chave]
        raise ErroImportacao(
            [f"Linha {gasto.linha}: pagador '{gasto.pagador}' não encontrado no grupo."]
        )

    if pagador_padrao_id is not None:
        return pagador_padrao_id

    raise ErroImportacao(
        [f"Linha {gasto.linha}: informe 'pagador_id' quando o arquivo não trouxer pagador."]
    )


def importar_gastos_grupo(
    db: Session,
    grupo_id: int,
    formato: FormatoImportacao,
    arquivo: bytes,
    pagador_padrao_id: int | None = None,
) -> ImportacaoOut:
    """Adapta um arquivo de gastos e persiste as despesas no grupo informado."""
    stmt = select(Grupo).options(selectinload(Grupo.participantes)).where(Grupo.id == grupo_id)
    grupo = db.scalar(stmt)
    if grupo is None:
        raise GrupoNaoEncontrado(f"Grupo {grupo_id} não encontrado.")

    participantes_por_nome = {p.nome.strip().lower(): p.id for p in grupo.participantes}
    if pagador_padrao_id is not None and pagador_padrao_id not in participantes_por_nome.values():
        raise ValueError(f"Pagador {pagador_padrao_id} não pertence ao grupo {grupo_id}.")

    adaptador = ADAPTADORES_POR_FORMATO[formato]()
    gastos = adaptador.ler(arquivo)

    for gasto in gastos:
        pagador_id = _resolver_pagador_id(gasto, participantes_por_nome, pagador_padrao_id)
        despesa = Despesa(
            grupo_id=grupo.id,
            pagador_id=pagador_id,
            descricao=gasto.descricao,
            tipo_divisao=TipoDivisao.IGUAL,
            params_divisao={},
        )
        db.add(despesa)
        db.add(Item(despesa=despesa, nome=gasto.descricao, valor=gasto.valor))

    db.commit()

    return ImportacaoOut(
        grupo_id=grupo_id,
        formato=formato,
        total_importados=len(gastos),
        gastos=[
            GastoImportadoOut(
                descricao=g.descricao,
                valor=g.valor,
                linha=g.linha,
                pagador=g.pagador,
            )
            for g in gastos
        ],
    )
