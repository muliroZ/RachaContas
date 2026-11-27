from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from rachacontas.enums import TipoAjuste


class ErroDominio(Exception):
    """Exceção base para violações de regra de negócio no domínio."""


class ValorInvalido(ErroDominio):
    """Lançada quando valores monetários, ajustes ou árvore de itens são inválidos."""


class ComponenteDespesa(ABC):
    @abstractmethod
    def total(self) -> int:
        """Retorna o total em centavos."""


# --- Padrão Composite ---


class Item(ComponenteDespesa):
    """Folha do Composite representando um item individual com valor em centavos."""

    def __init__(self, nome: str, valor: int) -> None:
        if valor < 0:
            raise ValorInvalido("O valor do item não pode ser negativo.")
        self.nome = nome
        self.valor = valor

    def total(self) -> int:
        return self.valor


class GrupoItens(ComponenteDespesa):
    """Composto que agrupa itens folha ou outros grupos aninhados."""

    def __init__(self, nome: str, filhos: Iterable[ComponenteDespesa] = ()) -> None:
        self.nome = nome
        self.filhos: list[ComponenteDespesa] = list(filhos)

    def adicionar(self, componente: ComponenteDespesa) -> None:
        self.filhos.append(componente)

    def remover(self, componente: ComponenteDespesa) -> None:
        self.filhos.remove(componente)

    def total(self) -> int:
        return sum(filho.total() for filho in self.filhos)


def _ler_campo(registro: object, campo: str, padrao: object = None) -> object:
    if isinstance(registro, Mapping):
        return registro.get(campo, padrao)
    return getattr(registro, campo, padrao)


def montar_arvore(itens: Sequence[object]) -> ComponenteDespesa:
    """Reconstrói a hierarquia Composite a partir de linhas planas com id e parent_id."""
    if not itens:
        return GrupoItens(nome="Itens", filhos=[])

    nos_por_id: dict[int, object] = {}
    filhos_por_pai: dict[int | None, list[int]] = {None: []}

    for registro in itens:
        item_id = _ler_campo(registro, "id")
        if not isinstance(item_id, int):
            raise ValorInvalido("Todo item precisa de um 'id' inteiro para montar a árvore.")
        if item_id in nos_por_id:
            raise ValorInvalido(f"ID de item duplicado na árvore: {item_id}.")
        nos_por_id[item_id] = registro
        filhos_por_pai[item_id] = []

    for registro in itens:
        item_id = int(_ler_campo(registro, "id"))  # type: ignore[arg-type]
        parent_id = _ler_campo(registro, "parent_id")
        if parent_id is None:
            filhos_por_pai[None].append(item_id)
        else:
            if not isinstance(parent_id, int) or parent_id not in nos_por_id:
                raise ValorInvalido(f"Item {item_id} referencia parent_id inexistente: {parent_id}.")
            filhos_por_pai[parent_id].append(item_id)

    visitando: set[int] = set()
    visitados: set[int] = set()

    def construir(item_id: int) -> ComponenteDespesa:
        if item_id in visitando:
            raise ValorInvalido(f"Ciclo detectado na árvore de itens envolvendo o ID {item_id}.")
        visitando.add(item_id)

        registro = nos_por_id[item_id]
        nome = str(_ler_campo(registro, "nome", ""))
        valor = _ler_campo(registro, "valor")
        ids_filhos = filhos_por_pai[item_id]

        if ids_filhos or valor is None:
            filhos_construidos = [construir(filho_id) for filho_id in ids_filhos]
            componente: ComponenteDespesa = GrupoItens(nome=nome, filhos=filhos_construidos)
        else:
            if not isinstance(valor, int):
                raise ValorInvalido(f"Valor inválido para o item {item_id}: {valor!r}.")
            componente = Item(nome=nome, valor=valor)

        visitando.remove(item_id)
        visitados.add(item_id)
        return componente

    raizes = [construir(raiz_id) for raiz_id in filhos_por_pai[None]]
    if len(visitados) != len(nos_por_id):
        raise ValorInvalido("Existem itens desconexos ou em ciclo na árvore.")

    if len(raizes) == 1 and isinstance(raizes[0], GrupoItens):
        return raizes[0]
    return GrupoItens(nome="Itens", filhos=raizes)


# --- Padrão Decorator ---


def _calcular_pontos_base(base: int, pontos_base: int) -> int:
    """Calcula percentual em pontos-base (1000 = 10%) arredondando meio para cima."""
    resultado = (Decimal(base) * Decimal(pontos_base)) / Decimal(10000)
    return int(resultado.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class PassoAjuste:
    tipo: TipoAjuste
    ordem: int
    valor_ajuste: int
    diferenca: int
    total_parcial: int


@dataclass(frozen=True)
class DetalhamentoValor:
    subtotal: int
    ajustes: list[PassoAjuste]
    total: int


class DecoradorAjuste(ComponenteDespesa, ABC):
    """Decorator base para ajustes aplicados sequencialmente sobre um ComponenteDespesa."""

    tipo: TipoAjuste

    def __init__(self, componente: ComponenteDespesa, valor_ajuste: int, ordem: int = 0) -> None:
        if valor_ajuste < 0:
            raise ValorInvalido("O valor do ajuste não pode ser negativo.")
        self.componente = componente
        self.valor_ajuste = valor_ajuste
        self.ordem = ordem

    def detalhamento(self) -> DetalhamentoValor:
        return detalhamento(self)


class TaxaServico(DecoradorAjuste):
    tipo = TipoAjuste.TAXA_SERVICO

    def __init__(self, componente: ComponenteDespesa, pontos_base: int, ordem: int = 0) -> None:
        super().__init__(componente=componente, valor_ajuste=pontos_base, ordem=ordem)
        self.pontos_base = pontos_base

    def total(self) -> int:
        base = self.componente.total()
        return base + _calcular_pontos_base(base, self.pontos_base)


class Gorjeta(DecoradorAjuste):
    tipo = TipoAjuste.GORJETA

    def __init__(self, componente: ComponenteDespesa, pontos_base: int, ordem: int = 0) -> None:
        super().__init__(componente=componente, valor_ajuste=pontos_base, ordem=ordem)
        self.pontos_base = pontos_base

    def total(self) -> int:
        base = self.componente.total()
        return base + _calcular_pontos_base(base, self.pontos_base)


class Couvert(DecoradorAjuste):
    tipo = TipoAjuste.COUVERT

    def __init__(self, componente: ComponenteDespesa, valor: int, ordem: int = 0) -> None:
        super().__init__(componente=componente, valor_ajuste=valor, ordem=ordem)
        self.valor = valor

    def total(self) -> int:
        return self.componente.total() + self.valor


class Desconto(DecoradorAjuste):
    tipo = TipoAjuste.DESCONTO

    def __init__(self, componente: ComponenteDespesa, valor: int, ordem: int = 0) -> None:
        super().__init__(componente=componente, valor_ajuste=valor, ordem=ordem)
        self.valor = valor

    def total(self) -> int:
        resultado = self.componente.total() - self.valor
        if resultado < 0:
            raise ValorInvalido("O total da despesa não pode ser negativo após o desconto.")
        return resultado


_DECORADORES_POR_TIPO: dict[TipoAjuste, type[DecoradorAjuste]] = {
    TipoAjuste.TAXA_SERVICO: TaxaServico,
    TipoAjuste.GORJETA: Gorjeta,
    TipoAjuste.COUVERT: Couvert,
    TipoAjuste.DESCONTO: Desconto,
}


def aplicar_ajustes(
    componente: ComponenteDespesa,
    ajustes: Iterable[object],
) -> ComponenteDespesa:
    """Encadeia os decoradores de ajuste ordenados pela coluna 'ordem'."""
    ordenados = sorted(ajustes, key=lambda item: int(_ler_campo(item, "ordem", 0)))  # type: ignore[arg-type]

    atual = componente
    for ajuste in ordenados:
        tipo_bruto = _ler_campo(ajuste, "tipo")
        tipo = tipo_bruto if isinstance(tipo_bruto, TipoAjuste) else TipoAjuste(str(tipo_bruto))
        valor = int(_ler_campo(ajuste, "valor", 0))  # type: ignore[arg-type]
        ordem = int(_ler_campo(ajuste, "ordem", 0))  # type: ignore[arg-type]

        classe_decorador = _DECORADORES_POR_TIPO[tipo]
        atual = classe_decorador(atual, valor, ordem=ordem)

    return atual


def detalhamento(componente: ComponenteDespesa) -> DetalhamentoValor:
    """Retorna o subtotal inicial e a evolução do valor após cada ajuste aplicado."""
    cadeia: list[DecoradorAjuste] = []
    atual: ComponenteDespesa = componente

    while isinstance(atual, DecoradorAjuste):
        cadeia.append(atual)
        atual = atual.componente

    cadeia.reverse()
    subtotal = atual.total()
    valor_anterior = subtotal
    passos: list[PassoAjuste] = []

    for decorador in cadeia:
        total_parcial = decorador.total()
        passos.append(
            PassoAjuste(
                tipo=decorador.tipo,
                ordem=decorador.ordem,
                valor_ajuste=decorador.valor_ajuste,
                diferenca=total_parcial - valor_anterior,
                total_parcial=total_parcial,
            )
        )
        valor_anterior = total_parcial

    return DetalhamentoValor(
        subtotal=subtotal,
        ajustes=passos,
        total=valor_anterior,
    )