from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy.orm import Session

from rachacontas.core.importacao import ErroImportacao
from rachacontas.db import SessionLocal
from rachacontas.enums import FormatoImportacao
from rachacontas.services.fechamento import GrupoNaoEncontrado
from rachacontas.services.importacao import importar_gastos_grupo

importacao_bp = Blueprint("importacao", __name__)


@importacao_bp.errorhandler(GrupoNaoEncontrado)
def _tratar_grupo_nao_encontrado(erro: GrupoNaoEncontrado):
    return jsonify({"erro": str(erro)}), 404


@importacao_bp.errorhandler(ErroImportacao)
def _tratar_erro_importacao(erro: ErroImportacao):
    return jsonify({"erro": str(erro), "detalhes": erro.erros}), 422


@importacao_bp.errorhandler(ValueError)
def _tratar_erro_valor(erro: ValueError):
    return jsonify({"erro": str(erro)}), 422


@importacao_bp.post("/grupos/<int:grupo_id>/importar")
def importar_gastos(grupo_id: int):
    arquivo = request.files.get("arquivo")
    if arquivo is None:
        return jsonify({"erro": "Envie o arquivo no campo 'arquivo'."}), 400

    formato_raw = (request.form.get("formato") or "").strip()
    if not formato_raw:
        return jsonify({"erro": "Informe o campo 'formato'."}), 400

    formato = FormatoImportacao(formato_raw)

    pagador_id_raw = request.form.get("pagador_id")
    pagador_padrao_id = int(pagador_id_raw) if pagador_id_raw else None
    conteudo = arquivo.read()

    sessao_g: Session | None = g.get("db")
    if sessao_g is not None:
        resultado = importar_gastos_grupo(
            db=sessao_g,
            grupo_id=grupo_id,
            formato=formato,
            arquivo=conteudo,
            pagador_padrao_id=pagador_padrao_id,
        )
        return jsonify(resultado.model_dump(mode="json")), 201

    session_factory = current_app.config.get("SESSION_LOCAL", SessionLocal)
    with session_factory() as db:
        resultado = importar_gastos_grupo(
            db=db,
            grupo_id=grupo_id,
            formato=formato,
            arquivo=conteudo,
            pagador_padrao_id=pagador_padrao_id,
        )
        return jsonify(resultado.model_dump(mode="json")), 201
