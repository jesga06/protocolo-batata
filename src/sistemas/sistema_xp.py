"""
Sistema de Progressão de XP — Protocolo: Batata
Controla o ganho de experiência, cálculo dinâmico de nível pela fórmula XP_prox = 10 + 5 * level,
tratamento de overflow multi-nível e limite máximo (Nível 20).
"""

from src.utils.math_utils import clamp


class SistemaXP:
    """
    Gerenciador de experiência e evolução de níveis da Batata.
    """

    def __init__(self, nivel_inicial: int = 1, nivel_maximo: int = 20):
        self.nivel: int = int(nivel_inicial)
        self.nivel_max: int = int(nivel_maximo)
        self.xp_atual: int = 0
        self.xp_total: int = 0
        self._callbacks_level_up: list = []

    def registrar_callback_level_up(self, callback):
        """Registra uma função ou método a ser executado ao subir de nível."""
        if callable(callback) and callback not in self._callbacks_level_up:
            self._callbacks_level_up.append(callback)

    def xp_para_proximo_nivel(self, nivel: int = None) -> int:
        """
        Retorna a quantidade de XP necessária para avançar a partir do nível informado.
        Fórmula estrita SSOT: XP_prox = 10 + 5 * level
        """
        lvl = self.nivel if nivel is None else int(nivel)
        return 10 + 5 * lvl

    def adicionar_xp(self, quantidade: int, mult_xp: float = 1.0) -> list[int]:
        """
        Acrescenta XP com multiplicador, processa subida de nível com suporte a transbordo
        (multi-level carryover) e dispara eventos de level-up.
        Retorna lista dos novos níveis atingidos neste incremento.
        """
        if quantidade <= 0:
            return []

        xp_ganho = int(round(quantidade * mult_xp))
        self.xp_total += xp_ganho
        self.xp_atual += xp_ganho

        niveis_ganhos = []

        while self.nivel < self.nivel_max and self.xp_atual >= self.xp_para_proximo_nivel(self.nivel):
            custo_nivel = self.xp_para_proximo_nivel(self.nivel)
            self.xp_atual -= custo_nivel
            self.nivel += 1
            niveis_ganhos.append(self.nivel)

            for cb in self._callbacks_level_up:
                try:
                    cb(self.nivel)
                except Exception:
                    pass

        # Trava de teto no nível máximo
        if self.nivel >= self.nivel_max:
            self.xp_atual = min(self.xp_atual, self.xp_para_proximo_nivel(self.nivel_max))

        return niveis_ganhos

    def progresso_normalizado(self) -> float:
        """Retorna uma fração entre 0.0 e 1.0 correspondente ao preenchimento da barra de XP."""
        if self.nivel >= self.nivel_max:
            return 1.0
        necessario = float(self.xp_para_proximo_nivel(self.nivel))
        if necessario <= 0:
            return 1.0
        return clamp(self.xp_atual / necessario, 0.0, 1.0)
