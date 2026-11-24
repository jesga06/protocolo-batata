"""
SMG Compacta — Protocolo: Batata
Arma de Slot 2 alternativa (desbloqueada com Dash em mestre_chave_inglesa M1).
Mecânica Burst & Vent com barra de calor (0..100), zona ideal (65..95) e trava (1.0s).
"""

from src.armas.arma_base import ArmaBase
from src.entidades.projetil import Projetil
from src.utils import constantes as _const
from src.utils.math_utils import vetor_direcao


class SMGCompacta(ArmaBase):
    """Submetralhadora compacta de munição infinita com gerenciamento térmico."""

    def __init__(
        self,
        dano: int | None = None,
        cooldown: float | None = None,
        velocidade_projetil: float | None = None,
        desaceleracao: float | None = None,
    ):
        dano_val = int(getattr(_const, "SMG_DANO", 9)) if dano is None else int(dano)
        cd_val = float(getattr(_const, "SMG_COOLDOWN", 0.11)) if cooldown is None else float(cooldown)
        super().__init__(
            nome="SMG Compacta",
            dano=dano_val,
            cooldown=cd_val,
            municao_infinita=True,
            slot=2,
            icone_asset="arma_smg_compacta",
        )
        self.id_arma: str = "smg_compacta"
        self.usa_calor = True
        self.velocidade_projetil = (
            float(getattr(_const, "SMG_VELOCIDADE_PROJETIL", 520.0))
            if velocidade_projetil is None
            else float(velocidade_projetil)
        )
        self.desaceleracao = (
            float(getattr(_const, "SMG_DESACELERACAO", 360.0))
            if desaceleracao is None
            else float(desaceleracao)
        )
        self.calor_por_tiro = float(getattr(_const, "SMG_CALOR_POR_TIRO", 7.5))
        self.resfriamento_por_seg = float(getattr(_const, "SMG_RESFRIAMENTO_POR_SEG", 28.0))
        self.zona_ideal_min = float(getattr(_const, "SMG_ZONA_IDEAL_MIN", 65.0))
        self.zona_ideal_max = float(getattr(_const, "SMG_ZONA_IDEAL_MAX", 95.0))
        self.trava_superaquecimento = float(getattr(_const, "SMG_TRAVA_SUPERAQUECIMENTO", 1.0))

        self.calor_atual: float = 0.0
        self.superaquecida: bool = False
        self.tempo_trava_calor: float = 0.0
        self._tempo_desde_ultimo_tiro: float = 0.0

    @property
    def em_zona_ideal(self) -> bool:
        return (not self.superaquecida) and (self.zona_ideal_min <= self.calor_atual <= self.zona_ideal_max)

    def pode_atirar(self) -> bool:
        if self.superaquecida:
            return False
        return super().pode_atirar()

    def update(self, dt: float):
        super().update(dt)
        dt_val = max(0.0, float(dt))
        self._tempo_desde_ultimo_tiro += dt_val
        if self.superaquecida:
            self.tempo_trava_calor = max(0.0, self.tempo_trava_calor - dt_val)
            if self.tempo_trava_calor <= 0.0:
                self.superaquecida = False
                self.calor_atual = 0.0
        elif self._tempo_desde_ultimo_tiro > 0.18 and self.calor_atual > 0.0:
            self.calor_atual = max(0.0, self.calor_atual - self.resfriamento_por_seg * dt_val)

    def disparar(self, origem_x: float, origem_y: float, destino_x: float, destino_y: float) -> list[Projetil]:
        if not self.pode_atirar():
            return []

        self.tempo_recarga_restante = self.cooldown
        self._tempo_desde_ultimo_tiro = 0.0

        dir_x, dir_y = vetor_direcao(origem_x, origem_y, destino_x, destino_y)
        if dir_x == 0.0 and dir_y == 0.0:
            dir_x = 1.0

        na_zona_ideal = self.em_zona_ideal
        if na_zona_ideal:
            dano_proj = max(1, int(round(self.dano * 1.45)))
            vel_proj = self.velocidade_projetil * 1.20
            cor = (255, 165, 40)
            superaquecido = True
        else:
            dano_proj = self.dano
            vel_proj = self.velocidade_projetil
            cor = None
            superaquecido = False

        projetil = Projetil(
            x=origem_x - 4.0,
            y=origem_y - 4.0,
            dir_x=dir_x,
            dir_y=dir_y,
            velocidade=vel_proj,
            dano=dano_proj,
            tempo_vida=1.1,
            dono="jogador",
            largura=8,
            altura=8,
            desaceleracao=self.desaceleracao,
            cor=cor,
            superaquecido=superaquecido,
        )

        self.calor_atual = min(100.0, self.calor_atual + self.calor_por_tiro)
        if self.calor_atual >= 100.0:
            self.superaquecida = True
            self.tempo_trava_calor = self.trava_superaquecimento

        try:
            from PPlay.sound import Sound
            sfx_path = _const.obter_caminho_asset("sfx_tiro_pistola")
            Sound(sfx_path).play()
        except Exception:
            pass

        return [projetil]
