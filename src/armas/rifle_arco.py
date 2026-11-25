"""
Rifle de Arco Elétrico — Protocolo: Batata
Arma de Slot 3 contínua (beam) travada no inimigo mais próximo da linha de mira.
"""

import math
from src.armas.arma_base import ArmaBase
from src.utils import constantes as _const
from src.utils.math_utils import distancia
from src.utils.traducao import t


class RifleArco(ArmaBase):
    """Feixe elétrico contínuo com lock-on angular suave e micro-slow."""

    def __init__(
        self,
        dano: int | None = None,
        intervalo_tick: float | None = None,
        alcance: float | None = None,
        municao_max: int | None = None,
        dreno_por_seg: float | None = None,
    ):
        dano_val = int(getattr(_const, "RIFLE_ARCO_DANO_TICK", 14)) if dano is None else int(dano)
        tick_val = (
            float(getattr(_const, "RIFLE_ARCO_INTERVALO_TICK", 0.10))
            if intervalo_tick is None
            else float(intervalo_tick)
        )
        mun_val = int(getattr(_const, "RIFLE_ARCO_MUNICIAO_MAX", 120)) if municao_max is None else int(municao_max)
        super().__init__(
            nome=t("combate_entidades", "arma_rifle_arco"),
            dano=dano_val,
            cooldown=tick_val,
            municao_infinita=False,
            municao_max=mun_val,
            slot=3,
            icone_asset="arma_rifle_arco",
        )
        self.id_arma: str = "rifle_arco"
        self.eh_continua = True
        self.intervalo_tick = tick_val
        self.alcance = float(getattr(_const, "RIFLE_ARCO_ALCANCE", 380.0)) if alcance is None else float(alcance)
        self.dreno_por_seg = (
            float(getattr(_const, "RIFLE_ARCO_DRENO_POR_SEG", 12.0))
            if dreno_por_seg is None
            else float(dreno_por_seg)
        )

        self.feixe_ativo: bool = False
        self.feixe_origem: tuple[float, float] = (0.0, 0.0)
        self.feixe_destino: tuple[float, float] = (0.0, 0.0)
        self.alvo_travado = None
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
            self.feixe_ativo = False
            self.alvo_travado = None
            self._tick_timer = 0.0
            return []

        self._municao_frac += self.dreno_por_seg * dt_val
        gasto = int(self._municao_frac)
        if gasto > 0:
            self._municao_frac -= gasto
            self.municao_atual = max(0, self.municao_atual - gasto)

        if self.municao_atual <= 0:
            self.feixe_ativo = False
            self.alvo_travado = None
            return []

        ang_mira = math.atan2(destino_y - origem_y, destino_x - origem_x)
        max_desvio = math.radians(38.0)

        melhor_alvo = None
        melhor_delta = max_desvio + 1e-5
        melhor_dist = self.alcance + 1.0
        melhor_cx = origem_x
        melhor_cy = origem_y

        for inimigo in inimigos or []:
            if not getattr(inimigo, "vivo", True) or getattr(inimigo, "em_fase", False):
                continue
            cx = inimigo.x + float(getattr(inimigo, "largura", 28)) / 2.0
            cy = inimigo.y + float(getattr(inimigo, "altura", 28)) / 2.0
            dist = distancia(origem_x, origem_y, cx, cy)
            if dist > self.alcance:
                continue
            ang_i = math.atan2(cy - origem_y, cx - origem_x)
            delta = abs(math.atan2(math.sin(ang_i - ang_mira), math.cos(ang_i - ang_mira)))
            if delta <= max_desvio:
                if delta < melhor_delta - 1e-4 or (abs(delta - melhor_delta) <= 1e-4 and dist < melhor_dist):
                    melhor_alvo = inimigo
                    melhor_delta = delta
                    melhor_dist = dist
                    melhor_cx = cx
                    melhor_cy = cy

        self.feixe_ativo = True
        self.feixe_origem = (float(origem_x), float(origem_y))
        if melhor_alvo is not None:
            self.alvo_travado = melhor_alvo
            self.feixe_destino = (float(melhor_cx), float(melhor_cy))
        else:
            self.alvo_travado = None
            self.feixe_destino = (
                float(origem_x + math.cos(ang_mira) * self.alcance),
                float(origem_y + math.sin(ang_mira) * self.alcance),
            )

        self._tick_timer += dt_val
        ticks_disparados = 0
        while self._tick_timer >= self.intervalo_tick and ticks_disparados < 4:
            self._tick_timer -= self.intervalo_tick
            ticks_disparados += 1
        if ticks_disparados > 0:
            if self.alvo_travado is not None:
                return [
                    {
                        "alvo": self.alvo_travado,
                        "dano": int(self.dano * ticks_disparados),
                        "tipo_fluxo": "arco",
                        "x": self.feixe_destino[0],
                        "y": self.feixe_destino[1],
                        "aplicar_slow": 0.25,
                        "aplicar_queimadura": 0.0,
                        "bonus_crit_overvolt": 0.20,
                    }
                ]
        return []
