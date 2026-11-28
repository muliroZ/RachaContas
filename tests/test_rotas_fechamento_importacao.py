import io

import pytest
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from rachacontas.enums import TipoAjuste, TipoDivisao
from rachacontas.models import Ajuste, Base, Despesa, Grupo, Item, Participante
from rachacontas.routes.fechamento import fechamento_bp
from rachacontas.routes.importacao import importacao_bp


@pytest.fixture()
def app_cliente():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    app = Flask("test_rotas")
    app.config["SESSION_LOCAL"] = TestingSessionLocal
    app.register_blueprint(fechamento_bp)
    app.register_blueprint(importacao_bp)

    with TestingSessionLocal() as session:
        yield app.test_client(), session

    engine.dispose()


def _criar_grupo_com_participantes(session: Session) -> tuple[Grupo, Participante, Participante]:
    grupo = Grupo(nome="Bar de Sexta")
    session.add(grupo)
    session.flush()

    severo = Participante(grupo_id=grupo.id, nome="Severo")
    murilo = Participante(grupo_id=grupo.id, nome="Murilo")
    session.add_all([severo, murilo])
    session.flush()
    return grupo, severo, murilo


def test_rota_fechamento_calcula_saldos_e_transferencias(app_cliente) -> None:
    client, session = app_cliente
    grupo, severo, murilo = _criar_grupo_com_participantes(session)

    despesa = Despesa(
        grupo_id=grupo.id,
        pagador_id=severo.id,
        descricao="Chopp e petisco",
        tipo_divisao=TipoDivisao.IGUAL,
        params_divisao={},
    )
    session.add(despesa)
    session.flush()

    session.add_all(
        [
            Item(despesa_id=despesa.id, parent_id=None, nome="Conta", valor=10000),
            Ajuste(despesa_id=despesa.id, tipo=TipoAjuste.TAXA_SERVICO, valor=1000, ordem=1),
        ]
    )
    session.commit()

    resposta = client.get(f"/grupos/{grupo.id}/fechamento")

    assert resposta.status_code == 200
    assert resposta.get_json() == {
        "grupo_id": grupo.id,
        "saldos": {str(severo.id): 5500, str(murilo.id): -5500},
        "transferencias": [{"de": murilo.id, "para": severo.id, "valor": 5500}],
    }


def test_rota_fechamento_grupo_inexistente_retorna_404(app_cliente) -> None:
    client, _ = app_cliente
    resposta = client.get("/grupos/9999/fechamento")
    assert resposta.status_code == 404
    assert "erro" in resposta.get_json()


def test_rota_importacao_planilha_persiste_e_reflete_no_fechamento(app_cliente) -> None:
    client, session = app_cliente
    grupo, severo, murilo = _criar_grupo_com_participantes(session)
    session.commit()

    planilha = (
        "item;valor;pagador\n"
        "Cerveja;80,00;Severo\n"
        "Batata;20,00;Murilo\n"
    ).encode("utf-8")

    resposta = client.post(
        f"/grupos/{grupo.id}/importar",
        data={
            "formato": "planilha_generica",
            "arquivo": (io.BytesIO(planilha), "gastos.csv"),
        },
        content_type="multipart/form-data",
    )

    assert resposta.status_code == 201
    dados = resposta.get_json()
    assert dados["total_importados"] == 2
    assert dados["gastos"][0] == {
        "descricao": "Cerveja",
        "valor": 8000,
        "linha": 2,
        "pagador": "Severo",
    }

    fechamento = client.get(f"/grupos/{grupo.id}/fechamento")
    assert fechamento.status_code == 200
    assert fechamento.get_json()["transferencias"] == [
        {"de": murilo.id, "para": severo.id, "valor": 3000}
    ]


def test_rota_importacao_csv_banco_com_pagador_id(app_cliente) -> None:
    client, session = app_cliente
    grupo, severo, _ = _criar_grupo_com_participantes(session)
    session.commit()

    csv_banco = (
        "data;estabelecimento;valor\n"
        "2026-11-28;Bar do Zé;R$ 60,00\n"
    ).encode("utf-8")

    resposta = client.post(
        f"/grupos/{grupo.id}/importar",
        data={
            "formato": "csv_banco",
            "pagador_id": str(severo.id),
            "arquivo": (io.BytesIO(csv_banco), "extrato.csv"),
        },
        content_type="multipart/form-data",
    )

    assert resposta.status_code == 201
    assert resposta.get_json()["total_importados"] == 1


def test_rota_importacao_erros_validacao(app_cliente) -> None:
    client, session = app_cliente
    grupo, _, _ = _criar_grupo_com_participantes(session)
    session.commit()

    # Sem arquivo -> 400
    assert (
        client.post(f"/grupos/{grupo.id}/importar", data={"formato": "csv_banco"}).status_code
        == 400
    )

    # Grupo inexistente -> 404
    resp_404 = client.post(
        "/grupos/9999/importar",
        data={
            "formato": "planilha_generica",
            "arquivo": (io.BytesIO(b"item;valor;pagador\nAgua;5,00;Severo\n"), "a.csv"),
        },
        content_type="multipart/form-data",
    )
    assert resp_404.status_code == 404

    # Erro de validação no arquivo -> 422 com detalhes
    resp_422 = client.post(
        f"/grupos/{grupo.id}/importar",
        data={
            "formato": "planilha_generica",
            "arquivo": (io.BytesIO(b"item;valor;pagador\nAgua;abc;Severo\n"), "a.csv"),
        },
        content_type="multipart/form-data",
    )
    assert resp_422.status_code == 422
    assert "detalhes" in resp_422.get_json()
