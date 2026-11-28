from pydantic import BaseModel

from rachacontas.enums import FormatoImportacao


class GastoImportadoOut(BaseModel):
    descricao: str
    valor: int
    linha: int
    pagador: str | None = None


class ImportacaoOut(BaseModel):
    grupo_id: int
    formato: FormatoImportacao
    total_importados: int
    gastos: list[GastoImportadoOut]
