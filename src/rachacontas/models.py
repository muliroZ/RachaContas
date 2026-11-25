from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Column, Enum, ForeignKey, MetaData, String, Table, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from rachacontas.enums import TipoAjuste, TipoComando, TipoDivisao


def coluna_enum(enum_cls: type[StrEnum]) -> Enum:
    """Grava o valor do enum ("igual"), não o nome ("IGUAL"), como texto."""
    return Enum(
        enum_cls,
        native_enum=False,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


class Base(DeclarativeBase):
    type_annotation_map = {cls: coluna_enum(cls) for cls in StrEnum.__subclasses__()}

    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


item_consumidor = Table(
    "item_consumidor",
    Base.metadata,
    Column("item_id", ForeignKey("item.id", ondelete="CASCADE"), primary_key=True),
    Column("participante_id", ForeignKey("participante.id", ondelete="CASCADE"), primary_key=True),
)


class Grupo(Base):
    __tablename__ = "grupo"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    limite_alerta: Mapped[int | None]

    participantes: Mapped[list["Participante"]] = relationship(back_populates="grupo")
    despesas: Mapped[list["Despesa"]] = relationship(back_populates="grupo")


class Participante(Base):
    __tablename__ = "participante"

    id: Mapped[int] = mapped_column(primary_key=True)
    grupo_id: Mapped[int] = mapped_column(ForeignKey("grupo.id"))
    nome: Mapped[str] = mapped_column(String(100))

    grupo: Mapped[Grupo] = relationship(back_populates="participantes")


class Despesa(Base):
    __tablename__ = "despesa"

    id: Mapped[int] = mapped_column(primary_key=True)
    grupo_id: Mapped[int] = mapped_column(ForeignKey("grupo.id"))
    pagador_id: Mapped[int] = mapped_column(ForeignKey("participante.id"))
    descricao: Mapped[str] = mapped_column(String(200))
    tipo_divisao: Mapped[TipoDivisao] = mapped_column(coluna_enum(TipoDivisao))
    params_divisao: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    excluida: Mapped[bool] = mapped_column(default=False)  # exclusão lógica (Command)
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())

    grupo: Mapped[Grupo] = relationship(back_populates="despesas")
    pagador: Mapped[Participante] = relationship()
    itens: Mapped[list["Item"]] = relationship(
        back_populates="despesa", cascade="all, delete-orphan"
    )
    ajustes: Mapped[list["Ajuste"]] = relationship(
        back_populates="despesa", cascade="all, delete-orphan", order_by="Ajuste.ordem"
    )


class Item(Base):
    __tablename__ = "item"

    id: Mapped[int] = mapped_column(primary_key=True)
    despesa_id: Mapped[int] = mapped_column(ForeignKey("despesa.id", ondelete="CASCADE"))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("item.id", ondelete="CASCADE"))
    nome: Mapped[str] = mapped_column(String(100))
    valor: Mapped[int | None]

    despesa: Mapped[Despesa] = relationship(back_populates="itens")
    pai: Mapped["Item | None"] = relationship(back_populates="filhos", remote_side=[id])
    filhos: Mapped[list["Item"]] = relationship(back_populates="pai")
    consumidores: Mapped[list[Participante]] = relationship(secondary=item_consumidor)


class Ajuste(Base):
    __tablename__ = "ajuste"

    id: Mapped[int] = mapped_column(primary_key=True)
    despesa_id: Mapped[int] = mapped_column(ForeignKey("despesa.id", ondelete="CASCADE"))
    tipo: Mapped[TipoAjuste] = mapped_column(coluna_enum(TipoAjuste))
    valor: Mapped[int]
    ordem: Mapped[int]

    despesa: Mapped[Despesa] = relationship(back_populates="ajustes")


class HistoricoComando(Base):
    __tablename__ = "historico_comando"

    id: Mapped[int] = mapped_column(primary_key=True)
    grupo_id: Mapped[int] = mapped_column(ForeignKey("grupo.id"))
    tipo: Mapped[TipoComando] = mapped_column(coluna_enum(TipoComando))
    estado_antes: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    estado_depois: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    desfeito: Mapped[bool] = mapped_column(default=False)
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())


class Notificacao(Base):
    __tablename__ = "notificacao"

    id: Mapped[int] = mapped_column(primary_key=True)
    participante_id: Mapped[int] = mapped_column(ForeignKey("participante.id"))
    mensagem: Mapped[str] = mapped_column(String(300))
    lida: Mapped[bool] = mapped_column(default=False)
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
