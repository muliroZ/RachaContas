from abc import ABC, abstractmethod


class ComponenteDespesa(ABC):
    @abstractmethod
    def total(self) -> int:
        """Retorna o total em centavos."""
