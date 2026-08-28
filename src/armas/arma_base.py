"""
Arma Base — Protocolo: Batata
Classe abstrata/base para todas as armas do jogo.
"""

from abc import ABC, abstractmethod


class ArmaBase(ABC):
    """
    Classe base que define o comportamento e atributos de armas.
    """

    def __init__(
        self,
        nome: str,
        dano: int,
        cooldown: float,
        municao_infinita: bool = True,
        municao_max: int = 0,
        slot: int = 1,
        icone_asset: str = ""
    ):
        self.nome = nome
        self.dano = int(dano)
        self.cooldown = float(cooldown)
        self.tempo_recarga_restante = 0.0
        self.municao_infinita = municao_infinita
        self.municao_max = int(municao_max)
        self.municao_atual = int(municao_max) if not municao_infinita else -1
        self.slot = int(slot)
        self.icone_asset = icone_asset

    def update(self, dt: float):
        """Decrementa o tempo de recarga com base no Delta Time."""
        if self.tempo_recarga_restante > 0.0:
            self.tempo_recarga_restante = max(0.0, self.tempo_recarga_restante - dt)

    def pode_atirar(self) -> bool:
        """Verifica se a arma está pronta para disparar (sem cooldown e com munição)."""
        if self.tempo_recarga_restante > 0.0:
            return False
        if not self.municao_infinita and self.municao_atual <= 0:
            return False
        return True

    @abstractmethod
    def disparar(self, origem_x: float, origem_y: float, destino_x: float, destino_y: float) -> list:
        """
        Executa o disparo e retorna uma lista de projéteis criados (ou lista vazia).
        """
        pass
