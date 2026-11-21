"""
Sistema de Progressão de XP — Protocolo: Batata
Controla o ganho de experiência, cálculo dinâmico de nível pela fórmula progressiva quadrática,
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

    @property
    def xp_necessario(self) -> int:
        """Retorna a quantidade total de XP necessária para o próximo nível."""
        return self.xp_para_proximo_nivel(self.nivel)

    @staticmethod
    def calcular_xp_para_nivel(nivel: int) -> int:
        """
        Calcula a quantidade de XP necessária para avançar a partir do nível informado.
        Fórmula progressiva quadrática: base = 20 + 10 * level + 5 * (level ^ 2)
        Para níveis > 10, reduz em 25%: int(round(base * 0.75)) para suavizar a subida até o nível 20.
        Para níveis 1..10, retém a curva padrão exata: int(round(base)).
        """
        lvl = int(nivel)
        base = 20 + 10 * lvl + 5 * (lvl ** 2)
        if lvl > 10:
            return max(1, int(round(base * 0.75)))
        return int(round(base))

    def xp_para_proximo_nivel(self, nivel: int = None) -> int:
        """
        Retorna a quantidade de XP necessária para avançar a partir do nível informado.
        Se nivel não for especificado, utiliza self.nivel.
        """
        lvl = self.nivel if nivel is None else int(nivel)
        return self.calcular_xp_para_nivel(lvl)

    def calcular_xp_necessario(self, nivel: int = None) -> int:
        """
        Alias para xp_para_proximo_nivel / conformidade com contratos de interface.
        """
        lvl = self.nivel if nivel is None else int(nivel)
        return self.calcular_xp_para_nivel(lvl)

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
                cb(self.nivel)

        # Trava de teto no nível máximo
        if self.nivel >= self.nivel_max:
            self.xp_atual = min(self.xp_atual, self.xp_para_proximo_nivel(self.nivel_max))

        return niveis_ganhos

    def ganhar_xp(self, quantidade: int, mult_xp: float = 1.0) -> list[int]:
        """Alias para adicionar_xp."""
        return self.adicionar_xp(quantidade, mult_xp)

    def progresso_normalizado(self) -> float:
        """Retorna uma fração entre 0.0 e 1.0 correspondente ao preenchimento da barra de XP."""
        if self.nivel >= self.nivel_max:
            return 1.0
        necessario = float(self.xp_para_proximo_nivel(self.nivel))
        if necessario <= 0:
            return 1.0
        return clamp(self.xp_atual / necessario, 0.0, 1.0)
