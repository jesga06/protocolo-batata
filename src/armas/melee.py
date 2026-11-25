"""
Ataque Melee (Chave de Manutenção) — Protocolo: Batata
Arma de Slot 1 permanente do jogador com dano em arco curto e repulsão (knockback).
"""

import math
from src.armas.arma_base import ArmaBase
from src.utils.math_utils import distancia, vetor_direcao, clamp
from src.utils.constantes import (
    MELEE_DANO, MELEE_COOLDOWN, MELEE_ALCANCE,
    MELEE_KNOCKBACK, MELEE_ALVOS_MAX, MELEE_ARCO_GRAUS
)
from src.utils.traducao import t


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
            nome=t("combate_entidades", "arma_melee"),
            dano=dano,
            cooldown=cooldown,
            municao_infinita=True,
            slot=1,
            icone_asset="arma_melee"
        )
        self.alcance = float(alcance)
        self._alcance_base: float = float(alcance)
        self.knockback_forca = float(knockback_forca)
        self.max_alvos_knockback = int(max_alvos_knockback)
        self.arco_graus = float(arco_graus)
        self._arco_graus_base: float = float(arco_graus)
        self._cooldown_base: float = float(cooldown)
        self.ultimo_parry_cd_total: float = float(cooldown)
        self.id_arma: str = "chave_manutencao"
        self.parry_duracao: float = 0.12
        self.parry_alcance_base: float = 64.0
        self.parry_alcance_mult: float = 1.0
        self.parry_janela_restante: float = 0.0
        self.parry_janela_id: int = 0
        self.parry_angulo: float = 0.0
        self.parry_acertou: bool = False
        self.parry_pode_punir_whiff: bool = False
        self.parry_whiff_penalidade_cd: float = 0.8
        self.parry_dano_mult: float = 1.0
        self.parry_splash_raio: float = 90.0
        self.parry_modo_postura_riposte: bool = False
        self.parry_modo_firewall: bool = False
        self.parry_modo_ventoinha: bool = False
        self.ultimo_parry_bloqueado_nao_parriavel: bool = False
        self.whiff_callback = None

    @property
    def parry_alcance(self) -> float:
        """Alcance efetivo da janela ativa de parry (desacoplado do alcance de LMB)."""
        return self.parry_alcance_base * self.parry_alcance_mult

    def finalizar_acerto_duelo(self) -> None:
        """Fecha a janela ativa de parry e reduz cooldown para 0.08s apenas em estágios de Duelo."""
        self.parry_janela_restante = 0.0
        self.parry_pode_punir_whiff = False
        self.tempo_recarga_restante = 0.08

    @property
    def parry_ativo(self) -> bool:
        """Retorna True enquanto a janela ativa de parry estiver aberta."""
        return self.parry_janela_restante > 0.0

    def atualizar(self, dt: float):
        """Decrementa a janela ativa de parry e aplica punição de whiff se expirar sem acerto."""
        if self.parry_janela_restante > 0.0:
            self.parry_janela_restante = max(0.0, self.parry_janela_restante - max(0.0, float(dt)))
            if self.parry_janela_restante <= 0.0:
                if self.parry_pode_punir_whiff and not self.parry_acertou:
                    self.tempo_recarga_restante += float(self.parry_whiff_penalidade_cd)
                    self.ultimo_parry_cd_total = max(
                        float(getattr(self, "ultimo_parry_cd_total", self.cooldown)),
                        float(self.tempo_recarga_restante),
                    )
                    if callable(self.whiff_callback):
                        self.whiff_callback()
                self.parry_pode_punir_whiff = False

    def iniciar_golpe_parry(self, angulo: float = 0.0, punir_whiff: bool = True):
        """Abre a janela ativa de parry na direção informada."""
        self.parry_janela_id = getattr(self, "parry_janela_id", 0) + 1
        self.parry_janela_restante = float(self.parry_duracao)
        self.parry_angulo = float(angulo) if angulo is not None else 0.0
        self.parry_acertou = False
        self.parry_pode_punir_whiff = bool(punir_whiff)

    def executar_parry(
        self,
        angulo: float = 0.0,
        punir_whiff: bool = True,
        cooldown_override: float | None = None,
    ) -> bool:
        """Executa o Quick-Parry (RMB/E) respeitando cooldown obrigatório."""
        if not self.pode_atirar():
            return False
        cd_aplicado = float(cooldown_override) if cooldown_override is not None else float(self.cooldown)
        self.tempo_recarga_restante = cd_aplicado
        self.ultimo_parry_cd_total = max(0.01, cd_aplicado)
        self.iniciar_golpe_parry(angulo=angulo, punir_whiff=punir_whiff)
        return True

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
        aplicar_dano: bool = True,
        abrir_janela_parry: bool = False,
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

        # Determina o ângulo central de mira se fornecido
        ang_mira = None
        if angulo_mira is not None:
            ang_mira = float(angulo_mira)
        elif mira_x is not None and mira_y is not None:
            ang_mira = math.atan2(mira_y - origem_y, mira_x - origem_x)

        # Abre janela ativa de parry apenas quando explicitamente solicitado
        if abrir_janela_parry:
            self.iniciar_golpe_parry(ang_mira if ang_mira is not None else 0.0, punir_whiff=True)

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

        if aplicar_dano and len(inimigos_afetados) > 0:
            self.parry_pode_punir_whiff = False

        return inimigos_afetados

    def tentar_parry_projeteis(
        self,
        origem_x: float,
        origem_y: float,
        lista_projeteis: list,
        angulo_mira: float = None,
        jogador_largura: float = 32.0,
        jogador_altura: float = 32.0,
    ) -> list:
        """
        Reflete (Parry) projéteis hostis ativos dentro do alcance de parry e arco de 120°
        enquanto a janela ativa de parry estiver aberta.
        Em postura_riposte, dá parry em qualquer projétil que encoste na hitbox da batata (360°).
        Retorna a lista de projéteis refletidos.
        """
        if self.parry_janela_restante <= 0.0 or not lista_projeteis:
            return []
        if getattr(self, "parry_modo_firewall", False) or getattr(self, "parry_modo_ventoinha", False):
            return []

        self.ultimo_parry_bloqueado_nao_parriavel = False
        ang_base = float(angulo_mira) if angulo_mira is not None else self.parry_angulo
        alcance_efetivo = self.parry_alcance
        meio_arco_rad = math.radians(self.arco_graus / 2.0)
        modo_riposte = bool(getattr(self, "parry_modo_postura_riposte", False))
        half_jw = float(jogador_largura) * 0.5
        half_jh = float(jogador_altura) * 0.5
        pad_hitbox_riposte = 6.0

        refletidos = []
        for p in lista_projeteis:
            if not getattr(p, "ativo", False) or getattr(p, "dono", "jogador") == "jogador":
                continue

            pw = float(getattr(p, "largura", 8))
            ph = float(getattr(p, "altura", 8))
            pcx = p.x + pw / 2.0
            pcy = p.y + ph / 2.0

            if modo_riposte:
                toca_hitbox = (
                    abs(pcx - origem_x) <= half_jw + pw * 0.5 + pad_hitbox_riposte
                    and abs(pcy - origem_y) <= half_jh + ph * 0.5 + pad_hitbox_riposte
                )
                if not toca_hitbox:
                    continue
            else:
                dist = distancia(origem_x, origem_y, pcx, pcy)
                if dist > alcance_efetivo:
                    continue

                no_cone = True
                if ang_base is not None and dist > 1e-4:
                    ang_p = math.atan2(pcy - origem_y, pcx - origem_x)
                    delta = abs(math.atan2(math.sin(ang_p - ang_base), math.cos(ang_p - ang_base)))
                    no_cone = (delta <= meio_arco_rad + 1e-5)

                if not no_cone:
                    continue

            if getattr(p, "nao_parriavel", False):
                self.ultimo_parry_bloqueado_nao_parriavel = True
                continue

            if angulo_mira is not None:
                dir_reb_x = math.cos(ang_base)
                dir_reb_y = math.sin(ang_base)
            elif ang_base is not None:
                dir_reb_x = math.cos(ang_base)
                dir_reb_y = math.sin(ang_base)
            else:
                dir_reb_x = -float(getattr(p, "dir_x", 1.0))
                dir_reb_y = -float(getattr(p, "dir_y", 0.0))

            p.dono = "jogador"
            p.velocidade = float(getattr(p, "velocidade", 300.0)) * 1.5
            p.dano = max(1, int(round(getattr(p, "dano", 1) * 3.0 * float(getattr(self, "parry_dano_mult", 1.0)))))
            p.dir_x = dir_reb_x
            p.dir_y = dir_reb_y
            p.refletido_parry = True
            p.parried = True
            p.raio_explosao = float(getattr(self, "parry_splash_raio", 90.0))
            p.splash_mult = 0.75
            p.cor = (255, 225, 90)
            p.tempo_vida = max(float(getattr(p, "tempo_vida", 0.0)), 2.0)
            p.tempo_vida_restante = max(float(getattr(p, "tempo_vida_restante", 0.0)), 2.0)
            if hasattr(p, "alvos_atingidos"):
                p.alvos_atingidos.clear()
            refletidos.append(p)

        if refletidos:
            self.parry_acertou = True

        return refletidos
