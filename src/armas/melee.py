"""
Ataque Melee (Chave de Manutenção) — Protocolo: Batata
Arma de Slot 1 permanente do jogador com dano em arco curto e repulsão (knockback).
"""

import math
from src.armas.arma_base import ArmaBase
from src.utils.math_utils import distancia, vetor_direcao, clamp
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
        arco_graus: float = None,
        aplicar_dano: bool = True
    ) -> list:
        """
        Executa o golpe corpo-a-corpo: causa dano a todos os inimigos no cone direcional de alcance (109px)
        e aplica knockback aos alvos mais próximos.
        Se mira_x/mira_y ou angulo_mira for fornecido, filtra estritamente pelo cone de arco_graus (60°).
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
            if not getattr(inimigo, "vivo", True) or getattr(inimigo, "em_fase", False):
                continue

            larg_e = float(getattr(inimigo, "largura", 28))
            alt_e = float(getattr(inimigo, "altura", 28))
            centro_e_x = inimigo.x + larg_e / 2.0
            centro_e_y = inimigo.y + alt_e / 2.0
            usar_aabb = getattr(inimigo, "is_elite", False) or getattr(inimigo, "is_boss", False) or larg_e > 32.0 or alt_e > 32.0
            if usar_aabb:
                px = clamp(origem_x, inimigo.x, inimigo.x + larg_e)
                py = clamp(origem_y, inimigo.y, inimigo.y + alt_e)
                dist = distancia(origem_x, origem_y, px, py)
            else:
                px, py = centro_e_x, centro_e_y
                dist = distancia(origem_x, origem_y, centro_e_x, centro_e_y)

            if dist <= self.alcance:
                if ang_mira is not None:
                    ang_c = math.atan2(centro_e_y - origem_y, centro_e_x - origem_x)
                    delta_c = abs(math.atan2(math.sin(ang_c - ang_mira), math.cos(ang_c - ang_mira)))
                    no_cone = (delta_c <= meio_arco_rad + 1e-5)
                    if not no_cone and usar_aabb and dist > 1e-5:
                        ang_p = math.atan2(py - origem_y, px - origem_x)
                        delta_p = abs(math.atan2(math.sin(ang_p - ang_mira), math.cos(ang_p - ang_mira)))
                        no_cone = (delta_p <= meio_arco_rad + 1e-5)
                    elif not no_cone and usar_aabb and dist <= 1e-5:
                        no_cone = True
                    if no_cone:
                        atingidos.append((inimigo, dist, centro_e_x, centro_e_y))
                else:
                    atingidos.append((inimigo, dist, centro_e_x, centro_e_y))

        if not atingidos:
            return []

        # Ordena do mais próximo para o mais distante
        atingidos.sort(key=lambda item: item[1])

        # Aplica dano a todos os atingidos no cone se aplicar_dano for True
        inimigos_afetados = []
        for idx, (inimigo, dist, cx, cy) in enumerate(atingidos):
            if aplicar_dano:
                ang_base = ang_mira if ang_mira is not None else math.atan2(cy - origem_y, cx - origem_x)
                dir_ataque = (math.cos(ang_base), math.sin(ang_base))
                try:
                    inimigo.receber_dano(
                        self.dano,
                        origem_x=origem_x,
                        origem_y=origem_y,
                        dir_ataque=dir_ataque
                    )
                except TypeError:
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

    def rebater_projeteis(
        self,
        origem_x: float,
        origem_y: float,
        lista_projeteis: list,
        mira_x: float = None,
        mira_y: float = None,
        angulo_mira: float = None
    ) -> list:
        """Rebate (Parry) projéteis inimigos dentro do cone de alcance da Chave de Manutenção."""
        if not lista_projeteis:
            return []
        ang_base = None
        if angulo_mira is not None:
            ang_base = float(angulo_mira)
        elif mira_x is not None and mira_y is not None:
            ang_base = math.atan2(mira_y - origem_y, mira_x - origem_x)

        meio_arco_rad = math.radians((self.arco_graus + 20.0) / 2.0)
        rebatidos = []
        for p in lista_projeteis:
            if not getattr(p, "ativo", False) or getattr(p, "dono", "") != "inimigo":
                continue
            pcx = p.x + getattr(p, "largura", 8) / 2.0
            pcy = p.y + getattr(p, "altura", 8) / 2.0
            dist = distancia(origem_x, origem_y, pcx, pcy)
            if dist <= self.alcance + 18.0:
                no_cone = True
                if ang_base is not None and dist > 1e-4:
                    ang_p = math.atan2(pcy - origem_y, pcx - origem_x)
                    delta = abs(math.atan2(math.sin(ang_p - ang_base), math.cos(ang_p - ang_base)))
                    no_cone = (delta <= meio_arco_rad)
                if no_cone:
                    dir_reb_x = math.cos(ang_base) if ang_base is not None else -getattr(p, "dir_x", 1.0)
                    dir_reb_y = math.sin(ang_base) if ang_base is not None else -getattr(p, "dir_y", 0.0)
                    p.dono = "jogador"
                    p.parried = True
                    p.dano = max(25, int(round(p.dano * 2.5)))
                    p.velocidade = max(500.0, float(getattr(p, "velocidade", 300.0)) * 1.6)
                    p.dir_x = dir_reb_x
                    p.dir_y = dir_reb_y
                    p.cor = (255, 215, 0)
                    p.tempo_vida_restante = max(float(getattr(p, "tempo_vida_restante", 1.0)), 1.6)
                    if hasattr(p, "alvos_atingidos"):
                        p.alvos_atingidos.clear()
                    rebatidos.append(p)
        return rebatidos
