"""
Ataque Melee (Chave de Manutenção) — Protocolo: Batata
Arma de Slot 1 permanente do jogador com dano em arco curto e repulsão (knockback).
"""

import math
from src.armas.arma_base import ArmaBase
from src.utils.math_utils import distancia, vetor_direcao
from src.utils.constantes import (
    MELEE_DANO, MELEE_COOLDOWN, MELEE_ALCANCE,
    MELEE_KNOCKBACK, MELEE_ALVOS_MAX, MELEE_ARCO_GRAUS, obter_caminho_asset
)


class Melee(ArmaBase):
    """
    Ataque corpo-a-corpo de curto alcance em cone direcional com dano em área
    e repulsão nos alvos mais próximos.
    """

    def __init__(
        self,
        dano: int = MELEE_DANO,
        cooldown: float = MELEE_COOLDOWN,
        alcance: float = MELEE_ALCANCE,
        knockback_forca: float = MELEE_KNOCKBACK,
        max_alvos_knockback: int = MELEE_ALVOS_MAX,
        arco_graus: float = MELEE_ARCO_GRAUS
    ):
        super().__init__(
            nome="Chave de Manutenção",
            dano=dano,
            cooldown=cooldown,
            municao_infinita=True,
            slot=1,
            icone_asset="arma_melee"
        )
        self.alcance = float(alcance)
        self.knockback_forca = float(knockback_forca)
        self.max_alvos_knockback = int(max_alvos_knockback)
        self.arco_graus = float(arco_graus)

    def disparar(self, origem_x: float, origem_y: float, destino_x: float, destino_y: float) -> list:
        """Melee não dispara projéteis balísticos convencionais."""
        return []

    def executar_ataque(
        self,
        origem_x: float,
        origem_y: float,
        lista_inimigos: list,
        mira_x: float = None,
        mira_y: float = None,
        angulo_mira: float = None,
        arco_graus: float = None
    ) -> list:
        """
        Executa o golpe corpo-a-corpo: causa dano a todos os inimigos no cone direcional de alcance
        e aplica knockback aos alvos mais próximos.
        Se mira_x/mira_y ou angulo_mira for fornecido, filtra estritamente pelo cone de arco_graus (45°).
        Caso contrário, mantém compatibilidade radial.
        Retorna a lista de inimigos atingidos.
        """
        if not self.pode_atirar():
            return []

        self.tempo_recarga_restante = self.cooldown

        # Efeito sonoro do golpe (sempre que desfere o ataque)
        try:
            from PPlay.sound import Sound
            sfx_path = obter_caminho_asset("sfx_ataque_melee")
            sfx = Sound(sfx_path)
            sfx.play()
        except Exception:
            pass

        # Determina o ângulo central de mira se fornecido
        ang_mira = None
        if angulo_mira is not None:
            ang_mira = float(angulo_mira)
        elif mira_x is not None and mira_y is not None:
            ang_mira = math.atan2(mira_y - origem_y, mira_x - origem_x)

        arco_efetivo = self.arco_graus if arco_graus is None else float(arco_graus)
        meio_arco_rad = math.radians(arco_efetivo / 2.0)

        atingidos = []
        for inimigo in lista_inimigos:
            if not getattr(inimigo, "vivo", True):
                continue

            centro_e_x = inimigo.x + getattr(inimigo, "largura", 28) / 2.0
            centro_e_y = inimigo.y + getattr(inimigo, "altura", 28) / 2.0
            dist = distancia(origem_x, origem_y, centro_e_x, centro_e_y)

            if dist <= self.alcance:
                if ang_mira is not None:
                    ang_e = math.atan2(centro_e_y - origem_y, centro_e_x - origem_x)
                    delta_ang = abs(math.atan2(math.sin(ang_e - ang_mira), math.cos(ang_e - ang_mira)))
                    if delta_ang <= meio_arco_rad + 1e-5:
                        atingidos.append((inimigo, dist, centro_e_x, centro_e_y))
                else:
                    atingidos.append((inimigo, dist, centro_e_x, centro_e_y))

        if not atingidos:
            return []

        # Ordena do mais próximo para o mais distante
        atingidos.sort(key=lambda item: item[1])

        # Aplica dano a todos os atingidos no cone
        inimigos_afetados = []
        for idx, (inimigo, dist, cx, cy) in enumerate(atingidos):
            inimigo.receber_dano(self.dano)
            inimigos_afetados.append(inimigo)

            # Aplica knockback aos N alvos mais próximos
            if idx < self.max_alvos_knockback:
                dir_x, dir_y = vetor_direcao(origem_x, origem_y, cx, cy)
                if dir_x == 0.0 and dir_y == 0.0:
                    if ang_mira is not None:
                        dir_x = math.cos(ang_mira)
                        dir_y = math.sin(ang_mira)
                    else:
                        dir_x = 1.0
                        dir_y = 0.0
                if hasattr(inimigo, "aplicar_knockback"):
                    inimigo.aplicar_knockback(dir_x, dir_y, self.knockback_forca)

        return inimigos_afetados
