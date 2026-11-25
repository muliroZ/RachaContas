from enum import StrEnum


class TipoAjuste(StrEnum):
    COUVERT = "couvert"
    DESCONTO = "desconto"
    GORJETA = "gorjeta"
    TAXA_SERVICO = "taxa_servico"


class TipoComando(StrEnum):
    CRIAR_DESPESA = "criar_despesa"
    EDITAR_DESPESA = "editar_despesa"
    EXCLUIR_DESPESA = "excluir_despesa"


class TipoDivisao(StrEnum):
    COM_EXCLUSAO = "com_exclusao"
    IGUAL = "igual"
    PERCENTUAL = "percentual"
    POR_CONSUMO = "por_consumo"


class TipoEvento(StrEnum):
    DESPESA_CRIADA = "despesa_criada"
    DESPESA_EDITADA = "despesa_editada"
    DESPESA_EXCLUIDA = "despesa_excluida"
    DESPESA_RESTAURADA = "despesa_restaurada"


class FormatoImportacao(StrEnum):
    CSV_BANCO = "csv_banco"
    PLANILHA_GENERICA = "planilha_generica"
