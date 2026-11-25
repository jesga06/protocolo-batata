"""
Lança-Chamas Industrial — Protocolo: Batata
Arma de Slot 3 contínua em cone curto com dano periódico e queimadura.
"""

import math
from src.armas.arma_base import ArmaBase
from src.utils import constantes as _const
from src.utils.math_utils import distancia
from src.utils.traducao import t


class LancaChamas(ArmaBase):
    """Fluxo contínuo de fogo em cone curto sem gerar objetos Projetil por frame."""

    def __init__(
        self,
        dano: int | None = None,
        intervalo_tick: float | None = None,
        alcance: float | None = None,
        arco_graus: float | None = None,
        municao_max: int | None = None,
        dreno_por_seg: float | None = None,
    ):
        dano_val = int(getattr(_const, "LANCA_CHAMAS_DANO_TICK", 10)) if dano is None else int(dano)
        tick_val = float(getattr(_const, "LANCA_CHAMAS_INTERVALO_TICK", 0.14)) if intervalo_tick is None else float(intervalo_tick)
        mun_val = int(getattr(_const, "LANCA_CHAMAS_MUNICIAO_MAX", 140)) if municao_max is None else int(municao_max)
        super().__init__(
            nome=t("combate_entidades", "arma_lanca_chamas"),
            dano=dano_val,
            cooldown=tick_val,
            municao_infinita=False,
            municao_max=mun_val,
            slot=3,
            icone_asset="arma_lanca_chamas",
        )
        self.id_arma: str = "lanca_chamas"
        self.eh_continua = True
        self.intervalo_tick = tick_val
        self.alcance = float(getattr(_const, "LANCA_CHAMAS_ALCANCE", 195.0)) if alcance is None else float(alcance)
        self.arco_graus = (
            float(getattr(_const, "LANCA_CHAMAS_ARCO_GRAUS", 55.0)) if arco_graus is None else float(arco_graus)
        )
        self.dreno_por_seg = (
            float(getattr(_const, "LANCA_CHAMAS_DRENO_POR_SEG", 14.0))
            if dreno_por_seg is None
            else float(dreno_por_seg)
        )

        self.fluxo_ativo: bool = False
        self.fluxo_origem: tuple[float, float] = (0.0, 0.0)
        self.fluxo_angulo: float = 0.0
        self.fluxo_alcance: float = self.alcance
        self._municao_frac: float = 0.0
        self._tick_timer: float = 0.0

    def disparar(self, origem_x: float, origem_y: float, destino_x: float, destino_y: float) -> list:
        """Arma contínua: o pipeline utiliza atualizar_fluxo()."""
        return []

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
        dt_val = max(0.0, float(dt))
        if not segurando_gatilho or self.municao_atual <= 0:
            self.fluxo_ativo = False
            self._tick_timer = 0.0
            return []

        self._municao_frac += self.dreno_por_seg * dt_val
        gasto = int(self._municao_frac)
        if gasto > 0:
            self._municao_frac -= gasto
            self.municao_atual = max(0, self.municao_atual - gasto)

        if self.municao_atual <= 0:
            self.fluxo_ativo = False
            return []

        ang_mira = math.atan2(destino_y - origem_y, destino_x - origem_x)
        self.fluxo_ativo = True
        self.fluxo_origem = (float(origem_x), float(origem_y))
        self.fluxo_angulo = ang_mira
        self.fluxo_alcance = self.alcance

        self._tick_timer += dt_val
        ticks_disparados = 0
        while self._tick_timer >= self.intervalo_tick and ticks_disparados < 4:
            self._tick_timer -= self.intervalo_tick
            ticks_disparados += 1
        if ticks_disparados <= 0:
            return []

        meio_arco_rad = math.radians(self.arco_graus / 2.0)
        eventos = []
        for inimigo in inimigos or []:
            if not getattr(inimigo, "vivo", True) or getattr(inimigo, "em_fase", False):
                continue
            cx = inimigo.x + float(getattr(inimigo, "largura", 28)) / 2.0
            cy = inimigo.y + float(getattr(inimigo, "altura", 28)) / 2.0
            dist = distancia(origem_x, origem_y, cx, cy)
            if dist > self.alcance:
                continue
            if dist > 1e-4:
                ang_i = math.atan2(cy - origem_y, cx - origem_x)
                delta = abs(math.atan2(math.sin(ang_i - ang_mira), math.cos(ang_i - ang_mira)))
                if delta > meio_arco_rad + 1e-5:
                    continue
            eventos.append(
                {
                    "alvo": inimigo,
                    "dano": int(self.dano * ticks_disparados),
                    "tipo_fluxo": "chama",
                    "x": cx,
                    "y": cy,
                    "aplicar_slow": 0.0,
                    "aplicar_queimadura": 2.5,
                    "bonus_crit_overvolt": 0.0,
                }
            )
        return eventos
