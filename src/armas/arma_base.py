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
        self._dano_original = self.dano
        self.cooldown = float(cooldown)
        self.tempo_recarga_restante = 0.0
        self._recarga_excedente = 0.0
        self.municao_infinita = municao_infinita
        self.municao_max = int(municao_max)
        self.municao_atual = int(municao_max) if not municao_infinita else -1
        self.slot = int(slot)
        self.icone_asset = icone_asset
        self.eh_continua: bool = False
        self.usa_calor: bool = False
        self.calor_atual: float = 0.0
        self.superaquecida: bool = False

    @property
    def em_zona_ideal(self) -> bool:
        return False

    @property
    def cooldown_atual(self) -> float:
        return self.tempo_recarga_restante

    @cooldown_atual.setter
    def cooldown_atual(self, valor: float):
        self.tempo_recarga_restante = float(valor)

    def update(self, dt: float):
        """Decrementa o tempo de recarga preservando excedente temporal para compensação de FPS baixo."""
        dt_val = max(0.0, float(dt))
        if self.tempo_recarga_restante > 0.0:
            restante = self.tempo_recarga_restante - dt_val
            if restante <= 0.0:
                self._recarga_excedente = max(0.0, -restante)
                self.tempo_recarga_restante = 0.0
            else:
                self._recarga_excedente = 0.0
                self.tempo_recarga_restante = restante
        else:
            self._recarga_excedente = min(float(self.cooldown) * 2.0, getattr(self, "_recarga_excedente", 0.0) + dt_val)

    def pode_atirar(self) -> bool:
        """Verifica se a arma está pronta para disparar (sem cooldown e com munição)."""
        if self.tempo_recarga_restante > 0.0:
            return False
        if not self.municao_infinita and self.municao_atual <= 0:
            return False
        return True

    def atualizar_fluxo(
        self,
        dt: float,
        segurando_gatilho: bool,
        origem_x: float,
        origem_y: float,
        destino_x: float,
        destino_y: float,
        inimigos: list,
    ) -> list[dict]:
        """Atualiza fluxo contínuo para armas de feixe/cone. Armas balísticas retornam []."""
        return []

    @abstractmethod
    def disparar(self, origem_x: float, origem_y: float, destino_x: float, destino_y: float) -> list:
        """
        Executa o disparo e retorna uma lista de projéteis criados (ou lista vazia).
        """
        pass
