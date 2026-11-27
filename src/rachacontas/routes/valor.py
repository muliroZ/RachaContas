from flask import Blueprint, current_app, g, jsonify
from sqlalchemy.orm import Session

from rachacontas.core.valor import ErroDominio
from rachacontas.db import SessionLocal
from rachacontas.services.valor import DespesaNaoEncontrada, calcular_valor_despesa

valor_bp = Blueprint("valor", __name__)


@valor_bp.errorhandler(DespesaNaoEncontrada)
def _tratar_despesa_nao_encontrada(erro: DespesaNaoEncontrada):
    return jsonify({"erro": str(erro)}), 404


@valor_bp.errorhandler(ErroDominio)
def _tratar_erro_dominio(erro: ErroDominio):
    return jsonify({"erro": str(erro)}), 422


@valor_bp.get("/despesas/<int:despesa_id>/valor")
def obter_valor_despesa(despesa_id: int):
    sessao_g: Session | None = g.get("db")
    if sessao_g is not None:
        resultado = calcular_valor_despesa(sessao_g, despesa_id)
        return jsonify(resultado.model_dump(mode="json")), 200

    session_factory = current_app.config.get("SESSION_LOCAL", SessionLocal)
    with session_factory() as db:
        resultado = calcular_valor_despesa(db, despesa_id)
        return jsonify(resultado.model_dump(mode="json")), 200