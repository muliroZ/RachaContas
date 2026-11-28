from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from rachacontas.enums import TipoAjuste


class ItemIn(BaseModel):
    nome: str = Field(min_length=1)
    valor: int | None = Field(default=None, ge=0)
    consumidores: list[int] = Field(default_factory=list)
    filhos: list[ItemIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def validar_folha_ou_grupo(self) -> ItemIn:
        if not self.filhos and self.valor is None:
            raise ValueError("Item folha precisa ter 'valor' informado em centavos.")
        return self


ItemIn.model_rebuild()


class AjusteIn(BaseModel):
    tipo: TipoAjuste
    valor: int = Field(ge=0)
    ordem: int = 0


class DetalheAjusteOut(BaseModel):
    tipo: TipoAjuste
    ordem: int
    valor_ajuste: int
    diferenca: int
    total_parcial: int


class ValorDespesaOut(BaseModel):
    despesa_id: int
    subtotal: int
    ajustes: list[DetalheAjusteOut]
    total: int