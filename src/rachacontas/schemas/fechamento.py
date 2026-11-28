from pydantic import BaseModel


class TransferenciaOut(BaseModel):
    de: int
    para: int
    valor: int


class FechamentoOut(BaseModel):
    grupo_id: int
    saldos: dict[int, int]
    transferencias: list[TransferenciaOut]
