"""
Bastão de Choque — Protocolo: Batata
Arma de Slot 1 alternativa (desbloqueada via conquista modo_batata_supremo).
Arco mais focado e cooldown mais rápido, preservando Quick-Parry (RMB).
"""

from src.armas.melee import Melee
from src.utils import constantes as _const


class BastaoChoque(Melee):
    """Arma corpo-a-corpo rápida e focada para Slot 1."""

    def __init__(
        self,
        dano: int | None = None,
        cooldown: float | None = None,
        alcance: float | None = None,
        knockback_forca: float | None = None,
        max_alvos_knockback: int = 4,
        arco_graus: float | None = None,
    ):
        dano_val = int(getattr(_const, "BASTAO_CHOQUE_DANO", 18)) if dano is None else int(dano)
        cd_val = float(getattr(_const, "BASTAO_CHOQUE_COOLDOWN", 0.42)) if cooldown is None else float(cooldown)
        alc_val = float(getattr(_const, "MELEE_ALCANCE", 84.0)) if alcance is None else float(alcance)
        kb_val = float(getattr(_const, "MELEE_KNOCKBACK", 360.0)) if knockback_forca is None else float(knockback_forca)
        arco_val = float(getattr(_const, "BASTAO_CHOQUE_ARCO_GRAUS", 95.0)) if arco_graus is None else float(arco_graus)

        super().__init__(
            dano=dano_val,
            cooldown=cd_val,
            alcance=alc_val,
            knockback_forca=kb_val,
            max_alvos_knockback=max_alvos_knockback,
            arco_graus=arco_val,
        )
        self.nome = "Bastão de Choque"
        self.id_arma = "bastao_choque"
        self.slot = 1
        self.icone_asset = "arma_melee"
        self.sprite_key = "arma_bastao_choque"
        self.parry_alcance_base = 58.0
