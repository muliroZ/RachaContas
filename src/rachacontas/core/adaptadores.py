import csv
import io
from collections.abc import Sequence
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from rachacontas.core.importacao import ErroImportacao, FonteGastos, GastoImportado


def decodificar_texto(arquivo: bytes) -> str:
    """Decodifica bytes de entrada tentando UTF-8 (com BOM) e fallback para Latin-1."""
    try:
        return arquivo.decode("utf-8-sig")
    except UnicodeDecodeError:
        return arquivo.decode("latin-1")


def reais_para_centavos(texto: str) -> int:
    """Converte um valor monetário em reais (ex.: 'R$ 45,90') para centavos inteiros."""
    limpo = texto.strip().replace("R$", "").replace("r$", "").replace(" ", "")
    if not limpo:
        raise ValueError("Valor monetário vazio.")

    if "," in limpo and "." in limpo:
        if limpo.rfind(",") > limpo.rfind("."):
            limpo = limpo.replace(".", "").replace(",", ".")
        else:
            limpo = limpo.replace(",", "")
    elif "," in limpo:
        limpo = limpo.replace(",", ".")

    try:
        valor_reais = Decimal(limpo)
    except InvalidOperation as erro:
        raise ValueError(f"Valor monetário inválido: {texto!r}") from erro

    if not valor_reais.is_finite():
        raise ValueError(f"Valor monetário inválido: {texto!r}")

    return int((valor_reais * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def detectar_delimitador(texto: str, candidatos: tuple[str, ...]) -> str:
    """Identifica o delimitador provável a partir da primeira linha não vazia."""
    primeira_linha = next((linha for linha in texto.splitlines() if linha.strip()), "")
    for delimitador in candidatos:
        if delimitador in primeira_linha:
            return delimitador
    return candidatos[0]


def _encontrar_coluna(cabecalhos: Sequence[str], candidatas: tuple[str, ...]) -> str:
    """Localiza o nome original da coluna correspondente ignorando caixa e espaços."""
    mapa = {nome.strip().lower(): nome for nome in cabecalhos if nome}
    for candidata in candidatas:
        if candidata in mapa:
            return mapa[candidata]
    raise ValueError(f"Coluna obrigatória não encontrada. Esperado um de: {', '.join(candidatas)}")


def _ler_tabela(
    arquivo: bytes,
    delimitadores: tuple[str, ...],
    colunas_descricao: tuple[str, ...],
    colunas_valor: tuple[str, ...],
    colunas_data: tuple[str, ...] | None = None,
    colunas_pagador: tuple[str, ...] | None = None,
) -> list[GastoImportado]:
    """Lê linhas tabulares e adapta para uma lista de GastoImportado."""
    texto = decodificar_texto(arquivo)
    if not texto.strip():
        return []

    delimitador = detectar_delimitador(texto, delimitadores)
    leitor = csv.DictReader(io.StringIO(texto), delimiter=delimitador)
    if not leitor.fieldnames:
        return []

    col_data = (
        _encontrar_coluna(leitor.fieldnames, colunas_data)
        if colunas_data is not None
        else None
    )
    col_descricao = _encontrar_coluna(leitor.fieldnames, colunas_descricao)
    col_valor = _encontrar_coluna(leitor.fieldnames, colunas_valor)
    col_pagador = (
        _encontrar_coluna(leitor.fieldnames, colunas_pagador)
        if colunas_pagador is not None
        else None
    )

    gastos: list[GastoImportado] = []
    erros: list[str] = []
    for linha in leitor:
        numero_linha = leitor.line_num
        if not any((valor or "").strip() for valor in linha.values()):
            continue

        linha_valida = True

        if col_data is not None and not (linha.get(col_data) or "").strip():
            erros.append(f"Linha {numero_linha}: data vazia.")
            linha_valida = False

        descricao = (linha.get(col_descricao) or "").strip()
        if not descricao:
            erros.append(f"Linha {numero_linha}: descrição vazia.")
            linha_valida = False

        valor_bruto = (linha.get(col_valor) or "").strip()
        valor_centavos: int | None = None
        try:
            valor_centavos = reais_para_centavos(valor_bruto)
        except ValueError as erro:
            erros.append(f"Linha {numero_linha}: {erro}")
            linha_valida = False

        pagador: str | None = None
        if col_pagador is not None:
            pagador = (linha.get(col_pagador) or "").strip()
            if not pagador:
                erros.append(f"Linha {numero_linha}: pagador vazio.")
                linha_valida = False

        if linha_valida and valor_centavos is not None:
            gastos.append(
                GastoImportado(
                    descricao=descricao,
                    valor=valor_centavos,
                    linha=numero_linha,
                    pagador=pagador,
                )
            )

    if erros:
        raise ErroImportacao(erros)

    return gastos


class AdaptadorCsvBanco(FonteGastos):
    """Adapter para arquivos CSV exportados de extratos ou faturas bancárias."""

    def ler(self, arquivo: bytes) -> list[GastoImportado]:
        return _ler_tabela(
            arquivo=arquivo,
            delimitadores=(";", ","),
            colunas_data=("data", "dt", "data_compra", "data da compra"),
            colunas_descricao=(
                "descricao",
                "descrição",
                "historico",
                "histórico",
                "estabelecimento",
            ),
            colunas_valor=("valor", "quantia", "total"),
        )


class AdaptadorPlanilhaGenerica(FonteGastos):
    """Adapter para planilhas tabulares genéricas (CSV/TSV)."""

    def ler(self, arquivo: bytes) -> list[GastoImportado]:
        return _ler_tabela(
            arquivo=arquivo,
            delimitadores=(";", ",", "\t"),
            colunas_descricao=("descricao", "descrição", "item", "nome"),
            colunas_valor=("valor", "preco", "preço", "total"),
            colunas_pagador=(
                "pagador",
                "nome do pagador",
                "nome_pagador",
                "responsavel",
                "responsável",
            ),
        )
