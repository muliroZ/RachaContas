from flask import Blueprint, current_app, g, jsonify
from sqlalchemy.orm import Session

from rachacontas.core.valor import ErroDominio
from rachacontas.db import SessionLocal
from rachacontas.services.fechamento import GrupoNaoEncontrado, fechar_grupo

fechamento_bp = Blueprint("fechamento", __name__)


@fechamento_bp.errorhandler(GrupoNaoEncontrado)
def _tratar_grupo_nao_encontrado(erro: GrupoNaoEncontrado):
    return jsonify({"erro": str(erro)}), 404


@fechamento_bp.errorhandler(ErroDominio)
@fechamento_bp.errorhandler(ValueError)
def _tratar_erro_validacao(erro: Exception):
    return jsonify({"erro": str(erro)}), 422


@fechamento_bp.get("/grupos/<int:grupo_id>/fechamento")
def obter_fechamento_grupo(grupo_id: int):
    sessao_g: Session | None = g.get("db")
    if sessao_g is not None:
        resultado = fechar_grupo(sessao_g, grupo_id)
        return jsonify(resultado.model_dump(mode="json")), 200

    session_factory = current_app.config.get("SESSION_LOCAL", SessionLocal)
    with session_factory() as db:
        resultado = fechar_grupo(db, grupo_id)
        return jsonify(resultado.model_dump(mode="json")), 200
