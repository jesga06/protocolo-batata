"""
Sistema Universal de Combos & Medidor de Estilo — Protocolo: Batata
Centraliza contagem de combo (Parry, Just-Dodge, troca de slot, abates sem drones),
bônus agnósticos para todas as armas e escala de Rank D..S quando medidor_estilo está ativo.
"""


class SistemaCombo:
    """Gerencia janela de combo, travas anti-bullet-hell e Ranks de estilo."""

    DURACAO_JANELA_BASE = 4.5
    CD_TROCA_SLOT = 1.2

    _BONUS_RANK = {
        "D": (0.00, 0.00),
        "C": (0.05, 0.04),
        "B": (0.10, 0.08),
        "A": (0.18, 0.12),
        "S": (0.28, 0.18),
    }

    def __init__(self):
        self.contagem: int = 0
        self.timer_janela: float = 0.0
        self.duracao_ativa_s: float = 0.0
        self.maior_contagem: int = 0
        self.modo_estilo: bool = False
        self.overdrive_pulso_pendente: bool = False
        self._ultimo_dash_id_combo: int = -1
        self._ultima_janela_parry_id: int = -1
        self._ultimo_slot_usado: int | None = None
        self._cd_troca_slot: float = 0.0
        self.golpe_sincronizado_pronto: bool = False
        self._rank_anterior: str = ""

    def definir_modo_estilo(self, ativo: bool) -> None:
        """Ativa ou desativa a escala de Rank D..S do Chip de Firmware medidor_estilo."""
        novo = bool(ativo)
        if novo == self.modo_estilo:
            return
        self.modo_estilo = novo
        rank_atual = self.rank
        if self.modo_estilo and rank_atual == "S" and self._rank_anterior != "S":
            self.overdrive_pulso_pendente = True
        self._rank_anterior = rank_atual

    @property
    def rank(self) -> str:
        """Retorna o Rank de estilo atual ('D'..'S') quando modo_estilo está ativo, ou ''."""
        if not self.modo_estilo:
            return ""
        c = self.contagem
        if c >= 35:
            return "S"
        if c >= 22:
            return "A"
        if c >= 12:
            return "B"
        if c >= 5:
            return "C"
        return "D"

    def _adicionar_pontos(self, pontos: int) -> None:
        self.contagem += int(pontos)
        if self.contagem > self.maior_contagem:
            self.maior_contagem = self.contagem
        self.timer_janela = self.DURACAO_JANELA_BASE
        rank_atual = self.rank
        if self.modo_estilo and rank_atual == "S" and self._rank_anterior != "S":
            self.overdrive_pulso_pendente = True
        self._rank_anterior = rank_atual

    def registrar_parry(self, janela_id: int) -> bool:
        """Registra no máximo 1 gatilho de combo por janela de Parry."""
        jid = int(janela_id)
        if jid == self._ultima_janela_parry_id:
            return False
        self._ultima_janela_parry_id = jid
        self._adicionar_pontos(3)
        self.golpe_sincronizado_pronto = True
        return True

    def registrar_just_dodge(self, dash_id: int) -> bool:
        """Registra no máximo 1 gatilho de combo por execução de Dash."""
        did = int(dash_id)
        if did == self._ultimo_dash_id_combo:
            return False
        self._ultimo_dash_id_combo = did
        self._adicionar_pontos(3)
        self.golpe_sincronizado_pronto = True
        return True

    def registrar_troca_slot(self, novo_slot: int) -> bool:
        """Concede +1 combo ao alternar de arma durante combo ativo (com cooldown anti-spam)."""
        slot = int(novo_slot)
        if self.contagem > 0 and self._ultimo_slot_usado is not None and slot != self._ultimo_slot_usado and self._cd_troca_slot <= 0.0:
            self._ultimo_slot_usado = slot
            self._cd_troca_slot = self.CD_TROCA_SLOT
            self._adicionar_pontos(1)
            return True
        self._ultimo_slot_usado = slot
        return False

    def registrar_abate(self, origem: str = "arma") -> bool:
        """Registra abate no combo (drones orbitais são explicitamente excluídos)."""
        if str(origem).lower() == "drone":
            return False
        self._adicionar_pontos(1)
        return True

    def consumir_golpe_sincronizado(self) -> bool:
        """Consome o bônus de próximo golpe sincronizado (+25% dano agnóstico)."""
        if self.golpe_sincronizado_pronto:
            self.golpe_sincronizado_pronto = False
            return True
        return False

    def consumir_pulso_overdrive(self) -> bool:
        """Consome o sinal de borda ao atingir Rank S."""
        if self.overdrive_pulso_pendente:
            self.overdrive_pulso_pendente = False
            return True
        return False

    def obter_multiplicadores(self) -> dict:
        """Retorna multiplicadores agnósticos de dano/cadência e estado de golpe sincronizado."""
        dano_mult = 1.0 + min(0.25, self.contagem * 0.01)
        cadencia_mult = 1.0 + min(0.15, self.contagem * 0.006)
        if self.modo_estilo:
            bonus_dano, bonus_cad = self._BONUS_RANK.get(self.rank, (0.0, 0.0))
            dano_mult += bonus_dano
            cadencia_mult += bonus_cad
        return {
            "dano_mult": dano_mult,
            "cadencia_mult": cadencia_mult,
            "proximo_golpe_sincronizado": self.golpe_sincronizado_pronto,
        }

    def update(self, dt: float) -> dict:
        """Atualiza decaimento da janela de combo, duração ativa e cooldown de troca de slot."""
        dt_val = max(0.0, float(dt))
        if self._cd_troca_slot > 0.0:
            self._cd_troca_slot = max(0.0, self._cd_troca_slot - dt_val)
        if self.contagem > 0:
            self.duracao_ativa_s += dt_val
            self.timer_janela = max(0.0, self.timer_janela - dt_val)
            if self.timer_janela <= 0.0:
                self.contagem = 0
                self.duracao_ativa_s = 0.0
                self.golpe_sincronizado_pronto = False
                self._rank_anterior = "D" if self.modo_estilo else ""
        return {
            "contagem": self.contagem,
            "duracao_s": self.duracao_ativa_s,
            "rank": self.rank,
        }
