"""
Pipeline B+ de Hooks Seletivos de Combate — Protocolo: Batata
Instancia APENAS os handlers das configurações não-neutras ativas e dos
1..3 Chips de Firmware equipados, despachando eventos em ordem determinística.
"""

from collections import deque
from dataclasses import dataclass
import math
from typing import Any, Optional

from src.entidades.holograma import EntidadeHolograma
from src.entidades.projetil import Projetil
from src.sistemas.config_efeitos import ModificadoresGameplay
from src.utils import constantes as _const
from src.utils.math_utils import normalizar_vetor


def _eh_boss(obj: Any) -> bool:
    return bool(getattr(obj, "is_boss", False) or getattr(obj, "eh_boss", False))


def obter_bandas_vsync_y(base_y: float, altura_total: float = 720.0) -> tuple[float, float]:
    """Retorna as 2 posições Y simétricas das bandas ativas de VSync tear."""
    h = max(1.0, float(altura_total))
    y1 = float(base_y) % h
    y2 = (y1 + h * 0.5) % h
    return (y1, y2)


def _eh_elite_ou_miniboss(obj: Any) -> bool:
    return bool(
        getattr(obj, "is_elite", False)
        or getattr(obj, "eh_elite", False)
        or getattr(obj, "eh_miniboss", False)
    )


def _aplicar_dano_entidade(
    alvo: Any,
    dano: int,
    ctx: Optional["ContextoCombate"] = None,
    origem: str = "efeito",
    ignorar_blindagem: bool = False,
) -> int:
    dano_int = max(0, int(dano))
    estava_vivo = bool(getattr(alvo, "vivo", True))
    dano_ef = dano_int
    if hasattr(alvo, "receber_dano"):
        try:
            ret = alvo.receber_dano(dano_int, ignorar_blindagem=ignorar_blindagem, fonte=origem)
        except TypeError:
            ret = alvo.receber_dano(dano_int)
        if isinstance(ret, (int, float)):
            dano_ef = int(ret)
    elif hasattr(alvo, "sofrer_dano"):
        alvo.sofrer_dano(dano_int)
    elif hasattr(alvo, "hp"):
        alvo.hp = max(0, int(alvo.hp) - dano_int)
        if alvo.hp <= 0:
            alvo.vivo = False

    if ctx is not None and ctx.cena is not None:
        if dano_ef > 0 and hasattr(ctx.cena, "dano_total_causado"):
            ctx.cena.dano_total_causado = int(getattr(ctx.cena, "dano_total_causado", 0)) + dano_ef
        if estava_vivo and not getattr(alvo, "vivo", True) and hasattr(ctx.cena, "_registrar_abate_inimigo"):
            ctx.cena._registrar_abate_inimigo(alvo, ctx.mods, origem=origem)
    return dano_ef


def _reduzir_cd_parry(ctx: Optional["ContextoCombate"], delta: float = 0.0, fator: float = 1.0) -> None:
    if ctx is None or ctx.jogador is None:
        return
    arma_melee = getattr(ctx.jogador, "arma_melee", None)
    if arma_melee is None:
        armas = getattr(ctx.jogador, "armas", None)
        if armas:
            arma_melee = armas[0]
    if arma_melee is not None and hasattr(arma_melee, "tempo_recarga_restante"):
        cd = float(arma_melee.tempo_recarga_restante)
        if fator != 1.0:
            cd *= float(fator)
        if delta > 0.0:
            cd -= float(delta)
        arma_melee.tempo_recarga_restante = max(0.0, cd)


def _aplicar_stun_entidade(alvo: Any, duracao: float) -> None:
    dur = float(duracao)
    if not _eh_boss(alvo):
        if hasattr(alvo, "slow_timer"):
            alvo.slow_timer = max(float(getattr(alvo, "slow_timer", 0.0)), dur)
        if hasattr(alvo, "slow_fator"):
            alvo.slow_fator = 0.0
    if hasattr(alvo, "atordoado_timer"):
        alvo.atordoado_timer = max(float(getattr(alvo, "atordoado_timer", 0.0)), dur)


def _recarregar_municao_arma(arma: Any, fracao: float) -> None:
    if arma is None:
        return
    mmax = int(getattr(arma, "municao_max", 0) or 0)
    if mmax <= 0:
        return
    inc = max(1, int(round(mmax * float(fracao))))
    if hasattr(arma, "municao_atual"):
        arma.municao_atual = min(mmax, int(arma.municao_atual) + inc)
    elif hasattr(arma, "municao"):
        arma.municao = min(mmax, int(arma.municao) + inc)


def _distancia_ponto_segmento(
    px: float, py: float, ax: float, ay: float, bx: float, by: float
) -> float:
    vx = bx - ax
    vy = by - ay
    comp2 = vx * vx + vy * vy
    if comp2 <= 1e-6:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / comp2))
    proj_x = ax + t * vx
    proj_y = ay + t * vy
    return math.hypot(px - proj_x, py - proj_y)


@dataclass
class ContextoCombate:
    """Contexto compartilhado entre GameplayScene/Mixins e o Pipeline B+."""
    cena: Any
    jogador: Any
    inimigos: list
    projeteis: list
    drops: list
    particulas: Any = None
    mods: Any = None
    sistema_conquistas: Any = None
    hologramas: list | None = None
    tempo_sobrevivencia: float = 0.0
    profundidade_recursao: int = 0


class EfeitoCombate:
    """Interface base leve para handlers do Pipeline B+."""
    prioridade: int = 50
    id_efeito: str = ""

    def ao_tick(self, ctx: ContextoCombate, dt: float) -> None:
        pass

    def ao_dash(
        self,
        ctx: ContextoCombate,
        origem: tuple[float, float],
        destino: tuple[float, float],
    ) -> None:
        pass

    def ao_dash_evasao(self, ctx: ContextoCombate, evento: Any = None) -> None:
        pass

    def ao_parry(self, ctx: ContextoCombate, projeteis_rebatidos: list) -> None:
        pass

    def ao_disparo(self, ctx: ContextoCombate, arma: Any, projeteis: list) -> list:
        return []

    def ao_impacto(
        self, ctx: ContextoCombate, alvo: Any, dano: int, fonte: Any = None
    ) -> dict | None:
        return None

    def ao_abate(self, ctx: ContextoCombate, inimigo: Any, fonte: Any = None) -> None:
        pass

    def ao_dano_recebido(
        self, ctx: ContextoCombate, quantidade: int, fonte: Any = None
    ) -> None:
        pass

    def ao_pos_render_mundo(
        self, ctx: ContextoCombate, superficie: Any, camera: Any = None
    ) -> None:
        pass


# =============================================================================
# HANDLERS DE CONFIGURAÇÕES (REWORK + NOVAS)
# =============================================================================


class EfeitoZoomBalistica(EfeitoCombate):
    id_efeito = "zoom_balistica"
    prioridade = 20

    def __init__(self, mods: ModificadoresGameplay):
        self.balistica_longa = bool(mods.zoom_balistica_longa)
        self.queima_roupa_mult = float(mods.zoom_queima_roupa_mult)
        self.execucao_cd_red = float(mods.zoom_execucao_cd_red)
        self.execucao_limiar_hp = float(mods.zoom_execucao_limiar_hp)

    def ao_impacto(self, ctx: ContextoCombate, alvo: Any, dano: int, fonte: Any = None) -> dict | None:
        res: dict[str, Any] = {}
        if self.balistica_longa and fonte is not None:
            ox = getattr(fonte, "x_origem", getattr(ctx.jogador, "x", 0.0))
            oy = getattr(fonte, "y_origem", getattr(ctx.jogador, "y", 0.0))
            ax = getattr(alvo, "x", 0.0)
            ay = getattr(alvo, "y", 0.0)
            dist = math.hypot(ax - ox, ay - oy)
            if dist <= 120.0:
                res["dano_mult"] = self.queima_roupa_mult
            else:
                bonus = min(0.45, ((dist - 120.0) / 480.0) * 0.45)
                res["dano_mult"] = 1.0 + bonus
                if (
                    dist >= 320.0
                    and hasattr(fonte, "perfuracoes_restantes")
                    and not getattr(fonte, "_zoom_perf_aplicada", False)
                ):
                    fonte.perfuracoes_restantes += 1
                    fonte._zoom_perf_aplicada = True

        if self.execucao_limiar_hp > 0.0:
            if not _eh_boss(alvo) and not _eh_elite_ou_miniboss(alvo):
                hp = getattr(alvo, "hp", 0)
                hp_max = max(1, getattr(alvo, "hp_max", 1))
                if 0 < hp and (hp / hp_max) < self.execucao_limiar_hp:
                    res["executar"] = True
                    res["dano_extra"] = int(hp)

        return res or None

    def ao_abate(self, ctx: ContextoCombate, inimigo: Any, fonte: Any = None) -> None:
        if self.execucao_cd_red > 0.0 and ctx.jogador is not None:
            if hasattr(ctx.jogador, "dash_cooldown_restante"):
                ctx.jogador.dash_cooldown_restante = max(
                    0.0, ctx.jogador.dash_cooldown_restante - self.execucao_cd_red
                )
            _reduzir_cd_parry(ctx, delta=self.execucao_cd_red)


class EfeitoFlickShot(EfeitoCombate):
    id_efeito = "flick_shot"
    prioridade = 25

    def __init__(self):
        self.flick_pronto: bool = False
        self._ang_anterior: Optional[float] = None
        self._estava_movendo: bool = False

    def registrar_movimento_mira(self, ang_atual: float, movendo: bool) -> None:
        if self._ang_anterior is not None:
            delta = abs((ang_atual - self._ang_anterior + math.pi) % (2.0 * math.pi) - math.pi)
            if delta > math.radians(45.0):
                self.flick_pronto = True
        if self._estava_movendo and not movendo:
            self.flick_pronto = True
        self._ang_anterior = ang_atual
        self._estava_movendo = movendo

    def ao_disparo(self, ctx: ContextoCombate, arma: Any, projeteis: list) -> list:
        if not self.flick_pronto or not projeteis:
            return []
        self.flick_pronto = False
        for p in projeteis:
            if getattr(p, "eh_replica", False):
                continue
            if hasattr(p, "velocidade"):
                p.velocidade *= 2.0
            if hasattr(p, "perfuracoes_restantes"):
                p.perfuracoes_restantes += 1
            if hasattr(p, "dano"):
                p.dano = max(1, int(round(p.dano * 1.35)))
        return []


class EfeitoBulletHellFuel(EfeitoCombate):
    id_efeito = "inimigos_ranged_bullet_hell"
    prioridade = 30

    def __init__(self):
        self.proximo_tiro_sobrecarregado: bool = False

    def _carregar(self, ctx: ContextoCombate) -> None:
        self.proximo_tiro_sobrecarregado = True
        if ctx.jogador is not None and hasattr(ctx.jogador, "dash_cooldown_restante"):
            ctx.jogador.dash_cooldown_restante = max(0.0, ctx.jogador.dash_cooldown_restante - 0.8)
        _reduzir_cd_parry(ctx, delta=0.8)

    def ao_parry(self, ctx: ContextoCombate, projeteis_rebatidos: list) -> None:
        self._carregar(ctx)

    def ao_dash_evasao(self, ctx: ContextoCombate, evento: Any = None) -> None:
        self._carregar(ctx)

    def ao_disparo(self, ctx: ContextoCombate, arma: Any, projeteis: list) -> list:
        if not self.proximo_tiro_sobrecarregado or not projeteis:
            return []
        self.proximo_tiro_sobrecarregado = False
        for p in projeteis:
            if getattr(p, "eh_replica", False):
                continue
            p.sobrecarregado = True
            p.dano = max(1, int(round(getattr(p, "dano", 10) * 1.35)))
        return []


class EfeitoInerciaCinetica(EfeitoCombate):
    id_efeito = "inercia_cinetica"
    prioridade = 35

    def __init__(self, nivel: int = 1):
        self.nivel = max(1, int(nivel))
        self.raio_colisao = 36.0 if self.nivel == 1 else 48.0
        self._dash_id: int = 0
        self._empurrados_no_dash: set[int] = set()
        self._abates_boliche_dash: int = 0

    def ao_dash(
        self,
        ctx: ContextoCombate,
        origem: tuple[float, float],
        destino: tuple[float, float],
    ) -> None:
        self._dash_id += 1
        self._empurrados_no_dash.clear()
        self._abates_boliche_dash = 0

    def ao_tick(self, ctx: ContextoCombate, dt: float) -> None:
        inimigos = ctx.inimigos
        if not inimigos:
            return

        # Boliche de Dash: jogador em dash empurra inimigos tocados lateralmente, atordoa e ativa derrapagem cinética
        jog = ctx.jogador
        if jog is not None and float(getattr(jog, "dash_ativo_timer", 0.0)) > 0.0:
            jx = float(getattr(jog, "x", 0.0)) + float(getattr(jog, "largura", 42)) * 0.5
            jy = float(getattr(jog, "y", 0.0)) + float(getattr(jog, "altura", 42)) * 0.5
            ddx, ddy = getattr(jog, "dash_dir", (1.0, 0.0))
            ddx, ddy = normalizar_vetor(float(ddx), float(ddy))
            if ddx == 0.0 and ddy == 0.0:
                ddx = 1.0
            px_lat, py_lat = -ddy, ddx
            raio_jog = max(float(getattr(jog, "largura", 42)), float(getattr(jog, "altura", 42))) * 0.6 + 24.0
            forca_boliche = 460.0 if self.nivel == 1 else 620.0

            for inim in inimigos:
                if not getattr(inim, "vivo", True) or _eh_boss(inim):
                    continue
                if id(inim) in self._empurrados_no_dash:
                    continue
                ix = float(getattr(inim, "x", 0.0)) + float(getattr(inim, "largura", 32)) * 0.5
                iy = float(getattr(inim, "y", 0.0)) + float(getattr(inim, "altura", 32)) * 0.5
                raio_inim = max(float(getattr(inim, "largura", 32)), float(getattr(inim, "altura", 32))) * 0.45
                if math.hypot(ix - jx, iy - jy) <= raio_jog + raio_inim:
                    self._empurrados_no_dash.add(id(inim))
                    lado = px_lat * (ix - jx) + py_lat * (iy - jy)
                    sinal = 1.0 if lado >= 0.0 else -1.0
                    nx_lat, ny_lat = px_lat * sinal, py_lat * sinal
                    if hasattr(inim, "aplicar_knockback"):
                        inim.aplicar_knockback(nx_lat, ny_lat, forca_boliche)
                    else:
                        inim.vx_knockback = nx_lat * forca_boliche
                        inim.vy_knockback = ny_lat * forca_boliche
                    _aplicar_stun_entidade(inim, 0.75)
                    inim.em_derrapagem_cinetica = True

        # Guarda O(K * N): itera SOMENTE sobre inimigos em derrapagem cinética
        derrapando = [
            e
            for e in inimigos
            if getattr(e, "vivo", True)
            and (
                getattr(e, "em_derrapagem_cinetica", False)
                or math.hypot(
                    getattr(e, "vx_knockback", 0.0),
                    getattr(e, "vy_knockback", 0.0),
                )
                >= 140.0
            )
        ]
        if not derrapando:
            return

        for src in derrapando:
            sx = getattr(src, "x", 0.0) + getattr(src, "largura", 32) * 0.5
            sy = getattr(src, "y", 0.0) + getattr(src, "altura", 32) * 0.5
            vel_kb = math.hypot(
                getattr(src, "vx_knockback", 0.0),
                getattr(src, "vy_knockback", 0.0),
            )
            hp_ref = max(int(getattr(src, "hp", 0) or 0), int(getattr(src, "hp_max", 20) or 20))
            mult_hp = 0.50 if self.nivel == 1 else 0.80
            dano_col_base = max(8, int(round(hp_ref * mult_hp)) + int(vel_kb * (0.08 if self.nivel == 1 else 0.12)))

            for dst in inimigos:
                if dst is src or not getattr(dst, "vivo", True):
                    continue
                if getattr(dst, "_boliche_cd", 0.0) > 0.0:
                    continue
                dx = (getattr(dst, "x", 0.0) + getattr(dst, "largura", 32) * 0.5) - sx
                dy = (getattr(dst, "y", 0.0) + getattr(dst, "altura", 32) * 0.5) - sy
                dist = math.hypot(dx, dy)
                if dist <= self.raio_colisao:
                    dst._boliche_cd = 0.25
                    dano_col = min(dano_col_base, 250) if _eh_boss(dst) else dano_col_base
                    estava_vivo_dst = bool(getattr(dst, "vivo", True))
                    _aplicar_dano_entidade(dst, dano_col, ctx=ctx, origem="boliche")
                    if estava_vivo_dst and not getattr(dst, "vivo", True):
                        self._abates_boliche_dash += 1
                    nx, ny = normalizar_vetor(dx, dy)
                    if hasattr(dst, "aplicar_knockback"):
                        dst.aplicar_knockback(nx, ny, vel_kb * 0.65)
                    if self.nivel >= 2:
                        dst.em_derrapagem_cinetica = True
            if getattr(src, "em_derrapagem_cinetica", False) and vel_kb < 40.0 and getattr(src, "slow_timer", 0.0) <= 0.0:
                src.em_derrapagem_cinetica = False

        for e in inimigos:
            if getattr(e, "_boliche_cd", 0.0) > 0.0:
                e._boliche_cd = max(0.0, e._boliche_cd - float(dt))

        if self._abates_boliche_dash >= 3:
            if ctx.cena is not None and hasattr(ctx.cena, "_emitir_evento_conquista"):
                ctx.cena._emitir_evento_conquista(
                    "abate_boliche", self._abates_boliche_dash, {"abates_golpe": self._abates_boliche_dash}
                )
            elif ctx.sistema_conquistas is not None:
                ctx.sistema_conquistas.registrar_evento(
                    "abate_boliche", self._abates_boliche_dash, {"abates_golpe": self._abates_boliche_dash}
                )


class EfeitoPinhataHardware(EfeitoCombate):
    id_efeito = "pinhata_hardware"
    prioridade = 40

    def __init__(self, nivel: int = 1):
        self.nivel = max(1, int(nivel))

    def ao_impacto(self, ctx: ContextoCombate, alvo: Any, dano: int, fonte: Any = None) -> dict | None:
        hp = getattr(alvo, "hp", 0)
        hp_pos = max(0, int(hp) - max(0, int(dano)))
        hp_max = max(1, getattr(alvo, "hp_max", 1))
        perdido_ratio = 1.0 - (hp_pos / hp_max)
        marcos = getattr(alvo, "_pinhata_marcos", None)
        if marcos is None:
            marcos = set()
            alvo._pinhata_marcos = marcos

        liberou = 0
        if perdido_ratio >= 0.33 and 1 not in marcos:
            marcos.add(1)
            liberou += self.nivel
        if perdido_ratio >= 0.66 and 2 not in marcos:
            marcos.add(2)
            liberou += self.nivel

        if liberou > 0:
            return {"micro_sucata": liberou}
        return None


class EfeitoClaraoFotossensivel(EfeitoCombate):
    id_efeito = "clarao_fotossensivel"
    prioridade = 42

    def __init__(self):
        self.clarao_timer: float = 0.0

    def ao_tick(self, ctx: ContextoCombate, dt: float) -> None:
        if self.clarao_timer > 0.0:
            self.clarao_timer = max(0.0, self.clarao_timer - float(dt))

    def ao_disparo(self, ctx: ContextoCombate, arma: Any, projeteis: list) -> list:
        self.clarao_timer = 0.6
        return []

    def ao_parry(self, ctx: ContextoCombate, projeteis_rebatidos: list) -> None:
        self.clarao_timer = 0.8

    def ao_impacto(self, ctx: ContextoCombate, alvo: Any, dano: int, fonte: Any = None) -> dict | None:
        if self.clarao_timer > 0.0 and not getattr(alvo, "_revelado_clarao", False):
            alvo._revelado_clarao = True
            _aplicar_stun_entidade(alvo, 0.35)
            return {"critico_forcado": True, "stun": 0.35}
        return None


class EfeitoPolaridadeInvertida(EfeitoCombate):
    id_efeito = "polaridade_invertida"
    prioridade = 44

    def __init__(self):
        self.surto_timer: float = 0.0

    def ativar_surto(self) -> None:
        self.surto_timer = 2.0

    def ao_tick(self, ctx: ContextoCombate, dt: float) -> None:
        if self.surto_timer > 0.0:
            self.surto_timer = max(0.0, self.surto_timer - float(dt))

    def ao_impacto(self, ctx: ContextoCombate, alvo: Any, dano: int, fonte: Any = None) -> dict | None:
        eh_blindado = "blindado" in getattr(alvo, "sprite_key", "") or getattr(alvo, "blindado", False)
        extra = int(round(dano * 0.40)) if eh_blindado else 0
        if self.surto_timer > 0.0:
            extra += int(round(dano * 0.25))
        if extra > 0:
            return {"dano_extra": extra}
        return None


class EfeitoGarbageCollector(EfeitoCombate):
    id_efeito = "garbage_collector"
    prioridade = 15

    def __init__(self):
        self.ram_progresso: float = 0.0
        self.disparos_travados: bool = False
        self.pausa_restante: float = 0.0
        self.buff_cadencia_timer: float = 0.0
        self.ondas_gc: list[dict] = []

    def ao_tick(self, ctx: ContextoCombate, dt: float) -> None:
        dt = float(dt)
        if self.ondas_gc:
            self.ondas_gc = [
                {**o, "tempo": o["tempo"] - dt}
                for o in self.ondas_gc
                if o["tempo"] - dt > 0.0
            ]
        if self.buff_cadencia_timer > 0.0:
            self.buff_cadencia_timer = max(0.0, self.buff_cadencia_timer - dt)

        if self.disparos_travados:
            self.pausa_restante -= dt
            if self.pausa_restante <= 0.0:
                self.disparos_travados = False
                self.pausa_restante = 0.0
                self.ram_progresso = 0.0
                self.buff_cadencia_timer = 4.0
                apagados = self._limpar_projeteis_proximos(ctx)
                _recarregar_municao_arma(getattr(ctx.jogador, "arma_especial", None), 0.15)
                if apagados > 0:
                    if ctx.cena is not None and hasattr(ctx.cena, "_emitir_evento_conquista"):
                        ctx.cena._emitir_evento_conquista(
                            "coleta_gc_projeteis",
                            apagados,
                            {"projeteis_apagados": apagados},
                        )
                    elif ctx.sistema_conquistas is not None:
                        ctx.sistema_conquistas.registrar_evento(
                            "coleta_gc_projeteis",
                            apagados,
                            {"projeteis_apagados": apagados},
                        )
            return

        self.ram_progresso = min(1.0, self.ram_progresso + dt / 12.0)
        if self.ram_progresso >= 1.0:
            self.disparos_travados = True
            self.pausa_restante = 0.8

    def _limpar_projeteis_proximos(self, ctx: ContextoCombate) -> int:
        if ctx.jogador is None:
            return 0
        jx = getattr(ctx.jogador, "x", 0.0) + getattr(ctx.jogador, "largura", 32) * 0.5
        jy = getattr(ctx.jogador, "y", 0.0) + getattr(ctx.jogador, "altura", 32) * 0.5
        raio_gc = 460.0
        self.ondas_gc.append({"x": jx, "y": jy, "raio": raio_gc, "tempo": 0.45, "duracao": 0.45})
        if ctx.particulas is not None and hasattr(ctx.particulas, "emitir_onda_choque"):
            ctx.particulas.emitir_onda_choque(jx, jy, raio_max=raio_gc, cor=(52, 211, 153))
        if not ctx.projeteis:
            return 0
        apagados = 0
        for p in ctx.projeteis:
            if getattr(p, "dono", "jogador") == "inimigo" and getattr(p, "ativo", True):
                px = getattr(p, "x", 0.0) + getattr(p, "largura", 8) * 0.5
                py = getattr(p, "y", 0.0) + getattr(p, "altura", 8) * 0.5
                if math.hypot(px - jx, py - jy) <= raio_gc:
                    p.ativo = False
                    apagados += 1
                    if ctx.particulas is not None and hasattr(ctx.particulas, "emitir_faiscas"):
                        ctx.particulas.emitir_faiscas(px, py, cor=(52, 211, 153), qtd=2)
        return apagados

    def ao_pos_render_mundo(self, ctx: ContextoCombate, superficie: Any, camera: Any = None) -> None:
        if not self.ondas_gc or superficie is None:
            return
        import pygame
        for o in self.ondas_gc:
            dur = max(0.01, float(o.get("duracao", 0.45)))
            prog = 1.0 - max(0.0, min(1.0, float(o.get("tempo", 0.0)) / dur))
            rx = int(camera.transform_x(o["x"])) if camera else int(o["x"])
            ry = int(camera.transform_y(o["y"])) if camera else int(o["y"])
            r_atual = max(8, int(round(o["raio"] * prog)))
            pygame.draw.circle(superficie, (52, 211, 153), (rx, ry), r_atual, width=2)


class EfeitoLatenciaPing(EfeitoCombate):
    id_efeito = "latencia_ping"
    prioridade = 10

    def __init__(self):
        self.atraso_s: float = float(
            getattr(_const, "LATENCIA_PING_ATRASO_SEGUNDOS", 0.080)
        )
        self._fila_acoes: deque[dict] = deque()
        self._historico_pos: deque[tuple[float, float]] = deque(maxlen=12)
        self._ecos_pendentes: list[dict] = []

    def agendar_acao(
        self,
        tipo: str,
        payload: Any = None,
        pos_fantasma: tuple[float, float] = (0.0, 0.0),
        ang_mira: float = 0.0,
    ) -> None:
        self._fila_acoes.append(
            {
                "tipo": str(tipo),
                "payload": payload,
                "pos_fantasma": pos_fantasma,
                "ang_mira": float(ang_mira),
                "tempo_restante": self.atraso_s,
            }
        )

    def consumir_acoes_prontas(self, dt: float) -> list[dict]:
        for acao in self._fila_acoes:
            acao["tempo_restante"] -= float(dt)
        prontas: list[dict] = []
        while self._fila_acoes and self._fila_acoes[0]["tempo_restante"] <= 0.0:
            prontas.append(self._fila_acoes.popleft())
        return prontas

    def obter_pos_hitbox_atrasada(
        self, fallback: Optional[tuple[float, float]] = None
    ) -> Optional[tuple[float, float]]:
        if not self._historico_pos:
            return fallback
        return self._historico_pos[0]

    def ao_tick(self, ctx: ContextoCombate, dt: float) -> None:
        dt = float(dt)
        if ctx.jogador is not None:
            cx = getattr(ctx.jogador, "x", 0.0) + getattr(ctx.jogador, "largura", 32) * 0.5
            cy = getattr(ctx.jogador, "y", 0.0) + getattr(ctx.jogador, "altura", 32) * 0.5
            self._historico_pos.append((cx, cy))

        restantes: list[dict] = []
        for eco in self._ecos_pendentes:
            eco["tempo"] -= dt
            if eco["tempo"] <= 0.0:
                alvo = eco["alvo"]
                if getattr(alvo, "vivo", True):
                    _aplicar_dano_entidade(alvo, eco["dano"], ctx=ctx, origem="eco_ping", ignorar_blindagem=True)
            else:
                restantes.append(eco)
        self._ecos_pendentes = restantes

    def ao_impacto(self, ctx: ContextoCombate, alvo: Any, dano: int, fonte: Any = None) -> dict | None:
        if fonte == "eco_ping" or getattr(fonte, "eh_eco_ping", False):
            return None
        dano_eco = max(1, int(round(dano * 0.30)))
        self._ecos_pendentes.append({"alvo": alvo, "dano": dano_eco, "tempo": 0.30})
        return None


class EfeitoModoWireframe(EfeitoCombate):
    id_efeito = "modo_wireframe"
    prioridade = 45
    MULT_HITBOX_INIMIGO: float = 1.30
    MULT_HITBOX_PROJETIL: float = 1.35

    @staticmethod
    def sincronizar_entidade(ent: Any, fator: float) -> None:
        """Escala (ou restaura para 1.0x) a hitbox de uma entidade preservando seu centro."""
        if ent is None or not hasattr(ent, "largura") or not hasattr(ent, "altura"):
            return
        if not hasattr(ent, "_wf_base_dim"):
            ent._wf_base_dim = (float(ent.largura), float(ent.altura))
        escala_atual = float(getattr(ent, "_wf_escala_aplicada", 1.0))
        if abs(escala_atual - float(fator)) < 1e-4:
            return
        bw, bh = ent._wf_base_dim
        nw = max(1, int(round(bw * float(fator))))
        nh = max(1, int(round(bh * float(fator))))
        if hasattr(ent, "x") and hasattr(ent, "y"):
            ent.x -= (nw - float(ent.largura)) * 0.5
            ent.y -= (nh - float(ent.altura)) * 0.5
        ent.largura = nw
        ent.altura = nh
        if hasattr(ent, "width"):
            ent.width = nw
        if hasattr(ent, "height"):
            ent.height = nh
        ent._wf_escala_aplicada = float(fator)


class EfeitoDashProtocolo(EfeitoCombate):
    id_efeito = "dash_protocolo"
    prioridade = 18

    def __init__(self, modo: str):
        self.modo = modo
        self.snapshots: deque[tuple[float, float, int]] = deque(maxlen=30)
        self._amostra_timer: float = 0.0
        self.sombra_ativa: Optional[EntidadeHolograma] = None
        self.linhas_eletricas: list[dict] = []
        self._ultima_janela_parry_sombra: int = -1
        self._sombra_parry_timer: float = 0.0
        self._sombra_parry_ang: float = 0.0
        self._sombra_parry_ja_atingidos_melee: set[int] = set()

    def tem_sombra_pronta_troca(self) -> bool:
        return (
            self.modo == "sombra_espelho"
            and self.sombra_ativa is not None
            and bool(getattr(self.sombra_ativa, "vivo", False))
        )

    def _resolver_alvo_mira(
        self,
        ctx: ContextoCombate,
        ox: float,
        oy: float,
        projeteis: list | None = None,
        ang_fallback: Optional[float] = None,
    ) -> tuple[float, float]:
        alvo_cena = getattr(ctx.cena, "_ultimo_mouse_mundo", None) if ctx.cena is not None else None
        if isinstance(alvo_cena, (tuple, list)) and len(alvo_cena) >= 2:
            return (float(alvo_cena[0]), float(alvo_cena[1]))
        if ctx.jogador is not None and hasattr(ctx.jogador, "mira_x") and hasattr(ctx.jogador, "mira_y"):
            return (float(ctx.jogador.mira_x), float(ctx.jogador.mira_y))
        if ang_fallback is not None:
            return (ox + math.cos(float(ang_fallback)) * 220.0, oy + math.sin(float(ang_fallback)) * 220.0)
        if ctx.jogador is not None and hasattr(ctx.jogador, "aim_angle"):
            ang = float(getattr(ctx.jogador, "aim_angle", 0.0))
            return (ox + math.cos(ang) * 220.0, oy + math.sin(ang) * 220.0)
        if projeteis:
            for p in projeteis:
                if not getattr(p, "origem_holograma", False) and not getattr(p, "eh_replica", False):
                    dx = float(getattr(p, "dir_x", 1.0))
                    dy = float(getattr(p, "dir_y", 0.0))
                    return (ox + dx * 220.0, oy + dy * 220.0)
        return (ox + 100.0, oy)

    def _tentar_parry_sombra(
        self,
        ctx: ContextoCombate,
        alcance: float = 105.0,
        ang_mira: Optional[float] = None,
    ) -> list:
        if self.sombra_ativa is None or not self.sombra_ativa.vivo:
            return []
        sx_c = self.sombra_ativa.x + self.sombra_ativa.largura * 0.5
        sy_c = self.sombra_ativa.y + self.sombra_ativa.altura * 0.5
        alvo_x, alvo_y = self._resolver_alvo_mira(ctx, sx_c, sy_c, ang_fallback=ang_mira)
        dx, dy = normalizar_vetor(alvo_x - sx_c, alvo_y - sy_c)
        if dx == 0.0 and dy == 0.0:
            dx, dy = 1.0, 0.0

        rebatidos_sombra: list = []
        for p in ctx.projeteis:
            if not getattr(p, "ativo", False) or getattr(p, "dono", "jogador") == "jogador":
                continue
            if getattr(p, "nao_parriavel", False):
                continue
            if getattr(p, "origem_holograma", False) or getattr(p, "eh_replica", False):
                continue
            pcx = float(getattr(p, "x", 0.0)) + float(getattr(p, "largura", 8)) * 0.5
            pcy = float(getattr(p, "y", 0.0)) + float(getattr(p, "altura", 8)) * 0.5
            if math.hypot(pcx - sx_c, pcy - sy_c) <= alcance:
                p.dono = "jogador"
                p.dir_x = dx
                p.dir_y = dy
                p.velocidade = float(getattr(p, "velocidade", 300.0)) * 1.5
                p.dano = max(1, int(round(getattr(p, "dano", 1) * 3.0 * float(self.sombra_ativa.dano_mult))))
                p.refletido_parry = True
                p.parried = True
                p.origem_holograma = True
                p.eh_replica = True
                p.cor = (80, 230, 255)
                p.tempo_vida = max(float(getattr(p, "tempo_vida", 0.0)), 2.0)
                p.tempo_vida_restante = max(float(getattr(p, "tempo_vida_restante", 0.0)), 2.0)
                if hasattr(p, "alvos_atingidos"):
                    p.alvos_atingidos.clear()
                rebatidos_sombra.append(p)
        return rebatidos_sombra

    def ao_tick(self, ctx: ContextoCombate, dt: float) -> None:
        dt = float(dt)
        if self.linhas_eletricas:
            self.linhas_eletricas = [
                ln for ln in self.linhas_eletricas if (ln.__setitem__("tempo", ln["tempo"] - dt) or True) and ln["tempo"] > 0.0
            ]

        if self.modo == "propulsor_instavel" and ctx.jogador is not None:
            ctx.jogador.dash_cargas_max = 2
            ctx.jogador.dash_recarga_mult = 1.35
            ctx.jogador.dash_sem_iframes = True
        elif self.modo == "rollback_estado" and ctx.jogador is not None:
            self._amostra_timer += dt
            if self._amostra_timer >= 0.10 or not self.snapshots:
                self._amostra_timer = 0.0
                self.snapshots.append(
                    (
                        float(getattr(ctx.jogador, "x", 0.0)),
                        float(getattr(ctx.jogador, "y", 0.0)),
                        int(getattr(ctx.jogador, "hp", 100)),
                    )
                )
        if self.sombra_ativa is not None and not self.sombra_ativa.vivo:
            self.sombra_ativa = None
            self._sombra_parry_timer = 0.0
        elif self._sombra_parry_timer > 0.0:
            self._sombra_parry_timer = max(0.0, self._sombra_parry_timer - dt)
            if self.modo == "sombra_espelho" and self.sombra_ativa is not None and ctx.profundidade_recursao < 1:
                self._tentar_parry_sombra(ctx, ang_mira=self._sombra_parry_ang)

    def ao_dash(
        self,
        ctx: ContextoCombate,
        origem: tuple[float, float],
        destino: tuple[float, float],
    ) -> None:
        if self.modo == "teleporte_buffer" and ctx.jogador is not None:
            if ctx.cena is not None:
                larg = float(getattr(ctx.jogador, "largura", 32))
                alt = float(getattr(ctx.jogador, "altura", 32))
                arena_w = float(getattr(ctx.cena, "largura_arena", 2240.0))
                arena_h = float(getattr(ctx.cena, "altura_arena", 1560.0))
                dest_cx = max(larg * 0.5, min(arena_w - larg * 0.5, float(destino[0])))
                dest_cy = max(alt * 0.5, min(arena_h - alt * 0.5, float(destino[1])))
                ctx.jogador.x = dest_cx - larg * 0.5
                ctx.jogador.y = dest_cy - alt * 0.5
                if hasattr(ctx.jogador, "dash_ativo_timer"):
                    ctx.jogador.dash_ativo_timer = 0.0
                destino_efetivo = (dest_cx, dest_cy)
            else:
                ctx.jogador.x = float(destino[0])
                ctx.jogador.y = float(destino[1])
                destino_efetivo = destino

            if hasattr(ctx.jogador, "dash_cooldown_restante"):
                ctx.jogador.dash_cooldown_restante = float(ctx.jogador.dash_cooldown_restante) + 0.6
            self.linhas_eletricas.append(
                {"origem": origem, "destino": destino_efetivo, "tempo": 0.35, "duracao": 0.35}
            )
            for inim in ctx.inimigos:
                if not getattr(inim, "vivo", True):
                    continue
                ix = getattr(inim, "x", 0.0) + getattr(inim, "largura", 32) * 0.5
                iy = getattr(inim, "y", 0.0) + getattr(inim, "altura", 32) * 0.5
                if _distancia_ponto_segmento(ix, iy, origem[0], origem[1], destino_efetivo[0], destino_efetivo[1]) <= 40.0:
                    _aplicar_dano_entidade(inim, 28, ctx=ctx, origem="blink")

        elif self.modo == "sombra_espelho" and ctx.jogador is not None:
            if self.sombra_ativa is not None and self.sombra_ativa.vivo:
                sx, sy = self.sombra_ativa.x, self.sombra_ativa.y
                self.sombra_ativa.x, self.sombra_ativa.y = ctx.jogador.x, ctx.jogador.y
                ctx.jogador.x, ctx.jogador.y = sx, sy
                if hasattr(ctx.jogador, "dash_ativo_timer"):
                    ctx.jogador.dash_ativo_timer = 0.0
            else:
                sx_spawn = float(destino[0]) - 16.0
                sy_spawn = float(destino[1]) - 16.0
                if ctx.cena is not None:
                    arena_w = float(getattr(ctx.cena, "largura_arena", 2240.0))
                    arena_h = float(getattr(ctx.cena, "altura_arena", 1560.0))
                    sx_spawn = max(0.0, min(arena_w - 32.0, sx_spawn))
                    sy_spawn = max(0.0, min(arena_h - 32.0, sy_spawn))
                sombra = EntidadeHolograma(
                    x=sx_spawn,
                    y=sy_spawn,
                    modo="sombra",
                    duracao=3.5,
                    dano_mult=0.55,
                )
                self.sombra_ativa = sombra
                if ctx.hologramas is not None:
                    ctx.hologramas.append(sombra)
                # 1o toque de Sombra Espelho nao move Cleiton nem consome cooldown antes da troca
                if hasattr(ctx.jogador, "dash_ativo_timer"):
                    ctx.jogador.dash_ativo_timer = 0.0
                if hasattr(ctx.jogador, "dash_cooldown_restante"):
                    ctx.jogador.dash_cooldown_restante = 0.0
                if hasattr(ctx.jogador, "dash_cargas_atuais") and hasattr(ctx.jogador, "dash_cargas_max"):
                    ctx.jogador.dash_cargas_atuais = ctx.jogador.dash_cargas_max

        elif self.modo == "rollback_estado" and ctx.jogador is not None and self.snapshots:
            rx, ry, rhp = self.snapshots[0]
            ctx.jogador.x = rx
            ctx.jogador.y = ry
            if hasattr(ctx.jogador, "dash_ativo_timer"):
                ctx.jogador.dash_ativo_timer = 0.0
            if hasattr(ctx.jogador, "dash_cooldown_restante"):
                ctx.jogador.dash_cooldown_restante = max(float(ctx.jogador.dash_cooldown_restante), 3.2)
            hp_atual = int(getattr(ctx.jogador, "hp", rhp))
            if rhp > hp_atual:
                hp_max = int(getattr(ctx.jogador, "hp_max", rhp))
                cura = int(round((rhp - hp_atual) * 0.5))
                ctx.jogador.hp = min(hp_max, hp_atual + cura)
            # Onda de choque na chegada
            cx = rx + getattr(ctx.jogador, "largura", 32) * 0.5
            cy = ry + getattr(ctx.jogador, "altura", 32) * 0.5
            for inim in ctx.inimigos:
                if not getattr(inim, "vivo", True):
                    continue
                ix = getattr(inim, "x", 0.0) + getattr(inim, "largura", 32) * 0.5
                iy = getattr(inim, "y", 0.0) + getattr(inim, "altura", 32) * 0.5
                dx, dy = ix - cx, iy - cy
                if math.hypot(dx, dy) <= 140.0:
                    _aplicar_dano_entidade(inim, 30, ctx=ctx, origem="rollback")
                    if hasattr(inim, "aplicar_knockback"):
                        nx, ny = normalizar_vetor(dx, dy)
                        inim.aplicar_knockback(nx, ny, 320.0)

    def ao_disparo(self, ctx: ContextoCombate, arma: Any, projeteis: list) -> list:
        if (
            self.modo != "sombra_espelho"
            or self.sombra_ativa is None
            or not self.sombra_ativa.vivo
            or ctx.profundidade_recursao >= 1
        ):
            return []
        sx_c = self.sombra_ativa.x + self.sombra_ativa.largura * 0.5
        sy_c = self.sombra_ativa.y + self.sombra_ativa.altura * 0.5
        alvo_x, alvo_y = self._resolver_alvo_mira(ctx, sx_c, sy_c, projeteis=projeteis)
        return self.sombra_ativa.replicar_disparo(projeteis, alvo_x, alvo_y, max_replicas=12)

    def ao_parry(
        self,
        ctx: ContextoCombate,
        projeteis_rebatidos: list,
        ang_mira: Optional[float] = None,
        apenas_ativacao: bool = False,
    ) -> None:
        if (
            self.modo != "sombra_espelho"
            or self.sombra_ativa is None
            or not self.sombra_ativa.vivo
            or ctx.profundidade_recursao >= 1
        ):
            return
        sx_c = self.sombra_ativa.x + self.sombra_ativa.largura * 0.5
        sy_c = self.sombra_ativa.y + self.sombra_ativa.altura * 0.5
        arma_melee = getattr(ctx.jogador, "arma_melee", None) if ctx.jogador is not None else None
        alcance = float(getattr(arma_melee, "parry_alcance", 105.0)) if arma_melee is not None else 105.0
        janela_id = int(getattr(arma_melee, "parry_janela_id", -1)) if arma_melee is not None else -1

        alvo_x, alvo_y = self._resolver_alvo_mira(ctx, sx_c, sy_c, ang_fallback=ang_mira)
        ang_sombra = math.atan2(alvo_y - sy_c, alvo_x - sx_c)
        self._sombra_parry_ang = ang_sombra

        nova_janela = (janela_id == -1) or (janela_id != self._ultima_janela_parry_sombra)
        if nova_janela:
            self._ultima_janela_parry_sombra = janela_id
            self._sombra_parry_ja_atingidos_melee.clear()
            dur = float(getattr(arma_melee, "parry_duracao", 0.25)) if arma_melee is not None else 0.25
            self._sombra_parry_timer = max(self._sombra_parry_timer, dur)
            if ctx.particulas is not None:
                if hasattr(ctx.particulas, "adicionar_arco_parry"):
                    ctx.particulas.adicionar_arco_parry(
                        sx_c,
                        sy_c,
                        ang_sombra,
                        raio=alcance,
                        arco_graus=160.0,
                        mostrar_texto=False,
                        cor=(80, 230, 255),
                    )
                if hasattr(ctx.particulas, "emitir_onda_choque"):
                    ctx.particulas.emitir_onda_choque(sx_c, sy_c, raio_max=alcance, cor=(80, 230, 255))
            dano_onda_sombra = max(1, int(round(20 * float(self.sombra_ativa.dano_mult))))
            for inim in list(ctx.inimigos):
                if not getattr(inim, "vivo", True) or getattr(inim, "em_fase", False) or _eh_boss(inim):
                    continue
                if id(inim) in self._sombra_parry_ja_atingidos_melee:
                    continue
                ix = float(getattr(inim, "x", 0.0)) + float(getattr(inim, "largura", 28)) * 0.5
                iy = float(getattr(inim, "y", 0.0)) + float(getattr(inim, "altura", 28)) * 0.5
                dist_i = math.hypot(ix - sx_c, iy - sy_c)
                if dist_i <= alcance:
                    self._sombra_parry_ja_atingidos_melee.add(id(inim))
                    if dist_i > 1e-4 and hasattr(inim, "aplicar_knockback"):
                        inim.aplicar_knockback((ix - sx_c) / dist_i, (iy - sy_c) / dist_i, 240.0)
                    _aplicar_dano_entidade(inim, dano_onda_sombra, ctx=ctx, origem="sombra_parry")
                    _aplicar_stun_entidade(inim, 0.35)

        rebatidos_sombra = self._tentar_parry_sombra(ctx, alcance=alcance, ang_mira=ang_mira)
        if rebatidos_sombra:
            if ctx.particulas is not None and hasattr(ctx.particulas, "emitir_faiscas"):
                ctx.particulas.emitir_faiscas(sx_c, sy_c, cor=(80, 230, 255), qtd=6)
            if ctx.cena is not None:
                audio = getattr(ctx.cena, "sistema_audio", None)
                if audio is not None and hasattr(audio, "tocar_parry_clang"):
                    audio.tocar_parry_clang(pitch_mult=1.18)

    def ao_pos_render_mundo(self, ctx: ContextoCombate, superficie: Any, camera: Any = None) -> None:
        if superficie is None:
            return
        import pygame
        for ln in self.linhas_eletricas:
            ox, oy = ln["origem"]
            dx, dy = ln["destino"]
            tx1 = int(camera.transform_x(ox)) if camera else int(ox)
            ty1 = int(camera.transform_y(oy)) if camera else int(oy)
            tx2 = int(camera.transform_x(dx)) if camera else int(dx)
            ty2 = int(camera.transform_y(dy)) if camera else int(dy)
            dur = max(0.01, float(ln.get("duracao", 0.35)))
            ratio = max(0.0, min(1.0, float(ln.get("tempo", 0.0)) / dur))
            w_ext = max(3, int(round(9 * ratio)))
            pygame.draw.line(superficie, (56, 189, 248), (tx1, ty1), (tx2, ty2), width=w_ext)
            pygame.draw.line(superficie, (240, 252, 255), (tx1, ty1), (tx2, ty2), width=max(1, w_ext // 2))
            r_pt = max(3, int(round(10 * ratio)))
            pygame.draw.circle(superficie, (56, 189, 248), (tx1, ty1), r_pt, width=2)
            pygame.draw.circle(superficie, (240, 252, 255), (tx2, ty2), r_pt, width=2)
        if self._sombra_parry_timer > 0.0 and self.sombra_ativa is not None and self.sombra_ativa.vivo:
            sx_c = self.sombra_ativa.x + self.sombra_ativa.largura * 0.5
            sy_c = self.sombra_ativa.y + self.sombra_ativa.altura * 0.5
            tx = int(camera.transform_x(sx_c)) if camera else int(sx_c)
            ty = int(camera.transform_y(sy_c)) if camera else int(sy_c)
            pygame.draw.circle(superficie, (80, 230, 255), (tx, ty), 32, width=2)


class EfeitoDashRastro(EfeitoCombate):
    id_efeito = "dash_rastro"
    prioridade = 22

    def __init__(self, modo: str):
        self.modo = modo
        self.sobreaquecimento_timer: float = 0.0
        self.zonas_fogo: list[dict] = []
        self.vortices: list[dict] = []
        self.vortices_vacuo: list[dict] = self.vortices
        self.subprocessos_pendentes: list[dict] = []
        self.feixes_subprocesso: list[dict] = []

    def ao_tick(self, ctx: ContextoCombate, dt: float) -> None:
        dt = float(dt)
        if self.sobreaquecimento_timer > 0.0:
            self.sobreaquecimento_timer = max(0.0, self.sobreaquecimento_timer - dt)

        if self.modo == "vacuo_io" and ctx.jogador is not None:
            ctx.jogador.dash_alcance_mult = 0.75
        elif self.modo == "subprocesso_atrasado" and ctx.jogador is not None:
            ctx.jogador.dash_alcance_mult = 0.85

        # Zonas incandescentes de exaustao_termica
        if self.zonas_fogo:
            ativas: list[dict] = []
            for z in self.zonas_fogo:
                z["tempo"] -= dt
                z["tick"] -= dt
                if z["tempo"] > 0.0:
                    if z["tick"] <= 0.0:
                        z["tick"] = 0.35
                        for inim in ctx.inimigos:
                            if not getattr(inim, "vivo", True):
                                continue
                            ix = getattr(inim, "x", 0.0) + getattr(inim, "largura", 32) * 0.5
                            iy = getattr(inim, "y", 0.0) + getattr(inim, "altura", 32) * 0.5
                            if math.hypot(ix - z["x"], iy - z["y"]) <= z["raio"]:
                                _aplicar_dano_entidade(inim, 8, ctx=ctx, origem="exaustao_termica")
                                if hasattr(inim, "vulneravel_timer"):
                                    inim.vulneravel_timer = max(float(getattr(inim, "vulneravel_timer", 0.0)), 1.5)
                                    inim.vulneravel_mult = max(float(getattr(inim, "vulneravel_mult", 1.0)), 1.25)
                    ativas.append(z)
            self.zonas_fogo = ativas

        # Vórtices de vacuo_io
        if self.vortices:
            v_ativos: list[dict] = []
            for v in self.vortices:
                v["tempo"] -= dt
                if v["tempo"] > 0.0:
                    for inim in ctx.inimigos:
                        if not getattr(inim, "vivo", True) or _eh_boss(inim):
                            continue
                        ix = getattr(inim, "x", 0.0) + getattr(inim, "largura", 32) * 0.5
                        iy = getattr(inim, "y", 0.0) + getattr(inim, "altura", 32) * 0.5
                        dx, dy = v["x"] - ix, v["y"] - iy
                        dist = math.hypot(dx, dy)
                        if 8.0 < dist <= v["raio"]:
                            nx, ny = normalizar_vetor(dx, dy)
                            inim.x = float(inim.x) + nx * 160.0 * dt
                            inim.y = float(inim.y) + ny * 160.0 * dt
                            if ctx.cena is not None and hasattr(ctx.cena, "_clamp_entidade_arena"):
                                ctx.cena._clamp_entidade_arena(inim)
                    for d in ctx.drops or []:
                        if getattr(d, "coletado", False) or not getattr(d, "ativo", True):
                            continue
                        if getattr(d, "tipo", "") in ("overclock", "powerup"):
                            continue
                        dx_d = v["x"] - (float(getattr(d, "x", 0.0)) + float(getattr(d, "largura", 16)) * 0.5)
                        dy_d = v["y"] - (float(getattr(d, "y", 0.0)) + float(getattr(d, "altura", 16)) * 0.5)
                        dist_d = math.hypot(dx_d, dy_d)
                        if 8.0 < dist_d <= v["raio"]:
                            nxd, nyd = normalizar_vetor(dx_d, dy_d)
                            d.x = float(d.x) + nxd * 220.0 * dt
                            d.y = float(d.y) + nyd * 220.0 * dt
                    v_ativos.append(v)
            self.vortices[:] = v_ativos

        if self.feixes_subprocesso:
            self.feixes_subprocesso[:] = [
                {**f, "tempo": f["tempo"] - dt}
                for f in self.feixes_subprocesso
                if f["tempo"] - dt > 0.0
            ]

        # Subprocesso atrasado (dispara após 0.75s indo até a posição atual do jogador)
        if self.subprocessos_pendentes:
            restantes: list[dict] = []
            for sp in self.subprocessos_pendentes:
                sp["tempo"] -= dt
                if sp["tempo"] <= 0.0:
                    ox, oy = sp["origem"]
                    if (
                        ctx.jogador is not None
                        and hasattr(ctx.jogador, "x")
                        and hasattr(ctx.jogador, "y")
                    ):
                        dx = float(ctx.jogador.x) + float(getattr(ctx.jogador, "largura", 32)) * 0.5
                        dy = float(ctx.jogador.y) + float(getattr(ctx.jogador, "altura", 32)) * 0.5
                    else:
                        dx, dy = sp["destino"]
                    for inim in ctx.inimigos:
                        if not getattr(inim, "vivo", True):
                            continue
                        ix = getattr(inim, "x", 0.0) + getattr(inim, "largura", 32) * 0.5
                        iy = getattr(inim, "y", 0.0) + getattr(inim, "altura", 32) * 0.5
                        if _distancia_ponto_segmento(ix, iy, ox, oy, dx, dy) <= 40.0:
                            _aplicar_dano_entidade(inim, 30, ctx=ctx, origem="subprocesso_atrasado")
                            _aplicar_stun_entidade(inim, 1.1)
                    self.feixes_subprocesso.append({
                        "origem": (ox, oy),
                        "destino": (dx, dy),
                        "tempo": 0.35,
                        "duracao": 0.35,
                    })
                else:
                    restantes.append(sp)
            self.subprocessos_pendentes = restantes

    def ao_dash(
        self,
        ctx: ContextoCombate,
        origem: tuple[float, float],
        destino: tuple[float, float],
    ) -> None:
        if self.modo == "exaustao_termica":
            self.sobreaquecimento_timer = 1.2
            mx = (origem[0] + destino[0]) * 0.5
            my = (origem[1] + destino[1]) * 0.5
            for px, py in (origem, (mx, my), destino):
                self.zonas_fogo.append({"x": px, "y": py, "raio": 48.0, "tempo": 3.5, "tick": 0.0})
        elif self.modo == "vacuo_io":
            self.vortices.append({"x": float(origem[0]), "y": float(origem[1]), "raio": 95.0, "tempo": 3.5})
        elif self.modo == "subprocesso_atrasado":
            if ctx.jogador is not None and hasattr(ctx.jogador, "dash_cooldown_restante"):
                ctx.jogador.dash_cooldown_restante = float(ctx.jogador.dash_cooldown_restante) + 0.4
            self.subprocessos_pendentes.append({"origem": origem, "destino": destino, "tempo": 0.75})
        elif self.modo == "thread_fantasma":
            clone = EntidadeHolograma(
                x=origem[0],
                y=origem[1],
                modo="clone_agro",
                duracao=2.5,
                hp=80,
                raio_agro=280.0,
            )
            if ctx.hologramas is not None:
                ctx.hologramas.append(clone)


class EfeitoParryAvancado(EfeitoCombate):
    id_efeito = "parry_avancado"
    prioridade = 24

    def __init__(self, precisao: str, efeito: str):
        self.precisao = precisao
        self.efeito = efeito
        self.barreiras_firewall: list[dict] = []
        self.ventoinha_timer: float = 0.0
        self.cortes_pendentes: int = 0
        self._corte_intervalo: float = 0.0
        self.estocadas_riposte: list[dict] = []
        self.postura_ring_timer: float = 0.0
        self._riposte_inimigos_janela: set[int] = set()

    def _disparar_estocada_riposte(
        self,
        ctx: ContextoCombate,
        jx_c: float,
        jy_c: float,
        ang_mira: Optional[float] = None,
    ) -> None:
        if ang_mira is not None:
            ang = float(ang_mira)
        else:
            alvo_cena = getattr(ctx.cena, "_ultimo_mouse_mundo", None) if ctx.cena is not None else None
            if isinstance(alvo_cena, (tuple, list)) and len(alvo_cena) >= 2:
                ang = math.atan2(float(alvo_cena[1]) - jy_c, float(alvo_cena[0]) - jx_c)
            else:
                ang = float(getattr(ctx.jogador, "aim_angle", 0.0)) if ctx.jogador is not None else 0.0
        alcance = 240.0
        dx_end = jx_c + math.cos(ang) * alcance
        dy_end = jy_c + math.sin(ang) * alcance
        mult_dano = float(getattr(ctx.mods, "dano_armas_mult", 1.0)) if ctx.mods else 1.0
        dano_estocada = max(1, int(round(45 * mult_dano)))
        for inim in ctx.inimigos:
            if not getattr(inim, "vivo", True) or getattr(inim, "em_fase", False):
                continue
            ix = getattr(inim, "x", 0.0) + getattr(inim, "largura", 28) * 0.5
            iy = getattr(inim, "y", 0.0) + getattr(inim, "altura", 28) * 0.5
            if _distancia_ponto_segmento(ix, iy, jx_c, jy_c, dx_end, dy_end) <= 23.0 + max(getattr(inim, "largura", 28), getattr(inim, "altura", 28)) * 0.3:
                _aplicar_dano_entidade(inim, dano_estocada, ctx=ctx, origem="parry")
                _aplicar_stun_entidade(inim, 1.5)
        self.estocadas_riposte.append(
            {
                "ox": jx_c,
                "oy": jy_c,
                "dx": dx_end,
                "dy": dy_end,
                "tempo": 0.28,
                "duracao": 0.28,
            }
        )

    def _executar_corte_ventoinha(self, ctx: ContextoCombate) -> None:
        if ctx.jogador is None:
            return
        jx = getattr(ctx.jogador, "x", 0.0) + getattr(ctx.jogador, "largura", 32) * 0.5
        jy = getattr(ctx.jogador, "y", 0.0) + getattr(ctx.jogador, "altura", 32) * 0.5
        mult_dano = float(getattr(ctx.mods, "dano_armas_mult", 1.0)) if ctx.mods else 1.0
        dano_corte = max(1, int(round(32 * mult_dano)))
        if ctx.particulas is not None and hasattr(ctx.particulas, "emitir_onda_choque"):
            ctx.particulas.emitir_onda_choque(jx, jy, raio_max=95.0, cor=(125, 240, 255))
        for inim in list(ctx.inimigos):
            if not getattr(inim, "vivo", True) or getattr(inim, "em_fase", False):
                continue
            ix = getattr(inim, "x", 0.0) + getattr(inim, "largura", 32) * 0.5
            iy = getattr(inim, "y", 0.0) + getattr(inim, "altura", 32) * 0.5
            dist = math.hypot(ix - jx, iy - jy)
            raio_hit = 95.0 + max(getattr(inim, "largura", 28), getattr(inim, "altura", 28)) * 0.35
            if dist <= raio_hit:
                dano_ef = _aplicar_dano_entidade(inim, dano_corte)
                if dist > 1e-4 and hasattr(inim, "aplicar_knockback"):
                    inim.aplicar_knockback((ix - jx) / dist, (iy - jy) / dist, 220.0)
                if ctx.particulas is not None and hasattr(ctx.particulas, "emitir_faiscas"):
                    ctx.particulas.emitir_faiscas(ix, iy, cor=(186, 230, 253), qtd=4)
                if ctx.cena is not None:
                    ctx.cena.dano_total_causado = getattr(ctx.cena, "dano_total_causado", 0) + (
                        int(dano_ef) if isinstance(dano_ef, (int, float)) else dano_corte
                    )
                    if not getattr(inim, "vivo", True) and hasattr(ctx.cena, "_registrar_abate_inimigo"):
                        ctx.cena._registrar_abate_inimigo(inim, ctx.mods, origem="parry")

    def _pulverizar_projeteis_ventoinha(self, ctx: ContextoCombate) -> int:
        if ctx.jogador is None:
            return 0
        jx = getattr(ctx.jogador, "x", 0.0) + getattr(ctx.jogador, "largura", 32) * 0.5
        jy = getattr(ctx.jogador, "y", 0.0) + getattr(ctx.jogador, "altura", 32) * 0.5
        pulverizados = 0
        for p in ctx.projeteis:
            if getattr(p, "dono", "jogador") == "inimigo" and getattr(p, "ativo", True):
                if getattr(p, "nao_parriavel", False):
                    continue
                px_c = getattr(p, "x", 0.0) + getattr(p, "largura", 8) * 0.5
                py_c = getattr(p, "y", 0.0) + getattr(p, "altura", 8) * 0.5
                r_p = max(float(getattr(p, "largura", 8)), float(getattr(p, "altura", 8))) * 0.45
                if math.hypot(px_c - jx, py_c - jy) <= 105.0 + r_p:
                    p.ativo = False
                    pulverizados += 1
                    if ctx.particulas is not None and hasattr(ctx.particulas, "emitir_faiscas"):
                        ctx.particulas.emitir_faiscas(px_c, py_c, cor=(224, 242, 254), qtd=4)
        return pulverizados

    def ao_tick(self, ctx: ContextoCombate, dt: float) -> None:
        dt = float(dt)
        if self.postura_ring_timer > 0.0:
            self.postura_ring_timer = max(0.0, self.postura_ring_timer - dt)
            if self.precisao == "postura_riposte" and ctx.jogador is not None:
                jw = float(getattr(ctx.jogador, "largura", 32))
                jh = float(getattr(ctx.jogador, "altura", 32))
                jx_c = float(getattr(ctx.jogador, "x", 0.0)) + jw * 0.5
                jy_c = float(getattr(ctx.jogador, "y", 0.0)) + jh * 0.5
                tocado = False
                for inim in list(ctx.inimigos):
                    if not getattr(inim, "vivo", True) or getattr(inim, "em_fase", False):
                        continue
                    if id(inim) in self._riposte_inimigos_janela:
                        continue
                    iw = float(getattr(inim, "largura", 28))
                    ih = float(getattr(inim, "altura", 28))
                    ix = float(getattr(inim, "x", 0.0)) + iw * 0.5
                    iy = float(getattr(inim, "y", 0.0)) + ih * 0.5
                    if (
                        abs(ix - jx_c) <= jw * 0.5 + iw * 0.5 + 6.0
                        and abs(iy - jy_c) <= jh * 0.5 + ih * 0.5 + 6.0
                    ):
                        self._riposte_inimigos_janela.add(id(inim))
                        tocado = True
                        _aplicar_stun_entidade(inim, 1.5)
                        if hasattr(inim, "aplicar_knockback"):
                            nx, ny = normalizar_vetor(ix - jx_c, iy - jy_c)
                            if nx == 0.0 and ny == 0.0:
                                nx = 1.0
                            inim.aplicar_knockback(nx, ny, 320.0)
                if tocado:
                    arma_melee = getattr(ctx.jogador, "arma_melee", None)
                    if arma_melee is not None:
                        arma_melee.parry_acertou = True
                    self._disparar_estocada_riposte(ctx, jx_c, jy_c)
            if self.postura_ring_timer <= 0.0:
                self._riposte_inimigos_janela.clear()
        if self.estocadas_riposte:
            for est in self.estocadas_riposte:
                est["tempo"] -= dt
            self.estocadas_riposte = [est for est in self.estocadas_riposte if est["tempo"] > 0.0]
        if self.barreiras_firewall:
            restantes: list[dict] = []
            for b in self.barreiras_firewall:
                b["tempo"] -= dt
                if b["tempo"] > 0.0:
                    r_b = max(12.0, float(b.get("raio", 65.0)))
                    ang = float(b.get("ang", 0.0))
                    perp_x, perp_y = -math.sin(ang), math.cos(ang)
                    p1x = float(b["x"]) - perp_x * r_b
                    p1y = float(b["y"]) - perp_y * r_b
                    p2x = float(b["x"]) + perp_x * r_b
                    p2y = float(b["y"]) + perp_y * r_b
                    for p in ctx.projeteis:
                        if getattr(p, "dono", "jogador") == "inimigo" and getattr(p, "ativo", True):
                            px_c = getattr(p, "x", 0.0) + getattr(p, "largura", 8) * 0.5
                            py_c = getattr(p, "y", 0.0) + getattr(p, "altura", 8) * 0.5
                            r_p = max(float(getattr(p, "largura", 8)), float(getattr(p, "altura", 8))) * 0.45
                            if _distancia_ponto_segmento(px_c, py_c, p1x, p1y, p2x, p2y) <= 9.0 + r_p:
                                p.ativo = False
                    restantes.append(b)
            self.barreiras_firewall = restantes

        if self.ventoinha_timer > 0.0:
            self.ventoinha_timer = max(0.0, self.ventoinha_timer - dt)
            self._pulverizar_projeteis_ventoinha(ctx)
            if self.cortes_pendentes > 0:
                self._corte_intervalo -= dt
                if self._corte_intervalo <= 0.0:
                    self._executar_corte_ventoinha(ctx)
                    self.cortes_pendentes -= 1
                    self._corte_intervalo = 0.30

    def ao_parry(
        self,
        ctx: ContextoCombate,
        projeteis_rebatidos: list,
        ang_mira: Optional[float] = None,
        apenas_ativacao: bool = False,
    ) -> None:
        if self.precisao == "postura_riposte" and ctx.jogador is not None:
            ctx.jogador.enraizado_timer = 0.45
            ctx.jogador.riposte_invuln_timer = 0.45
            self.postura_ring_timer = max(self.postura_ring_timer, 0.45)
            if apenas_ativacao:
                self._riposte_inimigos_janela.clear()
            else:
                jx = getattr(ctx.jogador, "x", 0.0)
                jy = getattr(ctx.jogador, "y", 0.0)
                jx_c = jx + getattr(ctx.jogador, "largura", 32) * 0.5
                jy_c = jy + getattr(ctx.jogador, "altura", 32) * 0.5
                for inim in ctx.inimigos:
                    if getattr(inim, "vivo", True):
                        if math.hypot(getattr(inim, "x", 0.0) - jx, getattr(inim, "y", 0.0) - jy) <= 180.0:
                            _aplicar_stun_entidade(inim, 1.5)
                if projeteis_rebatidos:
                    self._disparar_estocada_riposte(ctx, jx_c, jy_c, ang_mira=ang_mira)

        if self.efeito == "firewall_estatico" and ctx.jogador is not None:
            if ctx.cena is not None:
                jx = getattr(ctx.jogador, "x", 0.0) + getattr(ctx.jogador, "largura", 32) * 0.5
                jy = getattr(ctx.jogador, "y", 0.0) + getattr(ctx.jogador, "altura", 32) * 0.5
                ang = float(ang_mira) if ang_mira is not None else float(getattr(ctx.jogador, "aim_angle", 0.0))
                bx = jx + math.cos(ang) * 56.0
                by = jy + math.sin(ang) * 56.0
            else:
                ang = float(ang_mira) if ang_mira is not None else 0.0
                bx = getattr(ctx.jogador, "x", 0.0) + 40.0
                by = getattr(ctx.jogador, "y", 0.0)
            self.barreiras_firewall.append(
                {
                    "x": bx,
                    "y": by,
                    "ang": ang,
                    "raio": 65.0,
                    "tempo": 2.5,
                    "duracao": 2.5,
                }
            )
        elif self.efeito == "ventoinha_360" and ctx.jogador is not None:
            self.ventoinha_timer = 0.6
            self.cortes_pendentes = 1
            self._corte_intervalo = 0.30
            self._executar_corte_ventoinha(ctx)
            pulv = self._pulverizar_projeteis_ventoinha(ctx)
            if pulv > 0 and ctx.cena is not None:
                audio = getattr(ctx.cena, "sistema_audio", None)
                if audio is not None and hasattr(audio, "tocar_parry_clang"):
                    audio.tocar_parry_clang(pitch_mult=1.1)

    def ao_pos_render_mundo(self, ctx: ContextoCombate, superficie: Any, camera: Any = None) -> None:
        if superficie is None:
            return
        import pygame

        for b in self.barreiras_firewall:
            bx = int(camera.transform_x(b["x"])) if camera else int(b["x"])
            by = int(camera.transform_y(b["y"])) if camera else int(b["y"])
            r_b = max(12, int(round(b.get("raio", 65.0))))
            ang = float(b.get("ang", 0.0))
            perp_x, perp_y = -math.sin(ang), math.cos(ang)
            p1 = (int(bx - perp_x * r_b), int(by - perp_y * r_b))
            p2 = (int(bx + perp_x * r_b), int(by + perp_y * r_b))
            pygame.draw.line(superficie, (14, 165, 233), p1, p2, width=10)
            pygame.draw.line(superficie, (186, 230, 253), p1, p2, width=4)
            pygame.draw.circle(superficie, (56, 189, 248), p1, 6, width=2)
            pygame.draw.circle(superficie, (56, 189, 248), p2, 6, width=2)

        if self.ventoinha_timer > 0.0 and ctx.jogador is not None:
            jx = getattr(ctx.jogador, "x", 0.0) + getattr(ctx.jogador, "largura", 32) * 0.5
            jy = getattr(ctx.jogador, "y", 0.0) + getattr(ctx.jogador, "altura", 32) * 0.5
            tx = int(camera.transform_x(jx)) if camera else int(jx)
            ty = int(camera.transform_y(jy)) if camera else int(jy)
            fase = (0.6 - self.ventoinha_timer) * 24.0
            pygame.draw.circle(superficie, (125, 240, 255), (tx, ty), 95, width=2)
            for k in range(4):
                a_p = fase + k * (math.pi * 0.5)
                pygame.draw.line(
                    superficie,
                    (224, 242, 254),
                    (tx, ty),
                    (int(tx + math.cos(a_p) * 92), int(ty + math.sin(a_p) * 92)),
                    width=3,
                )

        if self.postura_ring_timer > 0.0 and ctx.jogador is not None:
            jx = getattr(ctx.jogador, "x", 0.0) + getattr(ctx.jogador, "largura", 32) * 0.5
            jy = getattr(ctx.jogador, "y", 0.0) + getattr(ctx.jogador, "altura", 32) * 0.5
            tx = int(camera.transform_x(jx)) if camera else int(jx)
            ty = int(camera.transform_y(jy)) if camera else int(jy)
            pygame.draw.circle(superficie, (251, 191, 36), (tx, ty), 30, width=2)
            pygame.draw.circle(superficie, (254, 240, 138), (tx, ty), 24, width=1)

        for est in self.estocadas_riposte:
            ox = int(camera.transform_x(est["ox"])) if camera else int(est["ox"])
            oy = int(camera.transform_y(est["oy"])) if camera else int(est["oy"])
            dx = int(camera.transform_x(est["dx"])) if camera else int(est["dx"])
            dy = int(camera.transform_y(est["dy"])) if camera else int(est["dy"])
            razao = max(0.1, min(1.0, float(est["tempo"]) / max(0.01, float(est["duracao"]))))
            larg_ext = max(4, int(round(14 * razao)))
            larg_int = max(2, int(round(6 * razao)))
            pygame.draw.line(superficie, (245, 158, 11), (ox, oy), (dx, dy), width=larg_ext)
            pygame.draw.line(superficie, (254, 249, 195), (ox, oy), (dx, dy), width=larg_int)


# =============================================================================
# 8 HANDLERS DE CHIPS DE FIRMWARE
# =============================================================================


class FirmwareGatilhoDuplo(EfeitoCombate):
    id_efeito = "gatilho_duplo"
    prioridade = 60

    def __init__(self):
        self.pronto: bool = False

    def ao_dash(self, ctx: ContextoCombate, origem: tuple[float, float], destino: tuple[float, float]) -> None:
        self.pronto = True
        if ctx.jogador is not None and hasattr(ctx.jogador, "dash_cooldown_restante"):
            ctx.jogador.dash_cooldown_restante = max(0.0, ctx.jogador.dash_cooldown_restante - 0.4)

    def ao_parry(self, ctx: ContextoCombate, projeteis_rebatidos: list) -> None:
        self.pronto = True

    def ao_disparo(self, ctx: ContextoCombate, arma: Any, projeteis: list) -> list:
        if not self.pronto or not projeteis or ctx.profundidade_recursao >= 1:
            return []
        self.pronto = False
        p = projeteis[0]
        if getattr(p, "eh_replica", False):
            return []
        rep = Projetil(
            x=p.x,
            y=p.y,
            dir_x=p.dir_x,
            dir_y=p.dir_y,
            velocidade=p.velocidade,
            dano=max(1, int(round(p.dano * 0.60))),
            tempo_vida=p.tempo_vida,
            dono="jogador",
            cor=(255, 180, 70),
        )
        rep.eh_replica = True
        return [rep]


class FirmwareRecargaTatica(EfeitoCombate):
    id_efeito = "recarga_tatica"
    prioridade = 61

    def __init__(self):
        self.contador_dash: int = 0
        self.pilhas_blindagem: int = 0
        self.timer_blindagem: float = 0.0

    def ao_tick(self, ctx: ContextoCombate, dt: float) -> None:
        if self.timer_blindagem > 0.0:
            self.timer_blindagem = max(0.0, self.timer_blindagem - float(dt))
            if self.timer_blindagem == 0.0:
                self.pilhas_blindagem = 0

    def ao_dash(self, ctx: ContextoCombate, origem: tuple[float, float], destino: tuple[float, float]) -> None:
        self.contador_dash += 1
        if self.contador_dash >= 3:
            self.contador_dash = 0
            self.pilhas_blindagem = min(3, self.pilhas_blindagem + 1)
            self.timer_blindagem = 4.0
            arma_esp = getattr(ctx.jogador, "arma_especial", None)
            _recarregar_municao_arma(arma_esp, 0.25)


class FirmwareAdrenalinaOverclock(EfeitoCombate):
    id_efeito = "adrenalina_overclock"
    prioridade = 62

    def __init__(self):
        self.timer: float = 0.0
        self.abates_recentes: int = 0
        self.janela_abates: float = 0.0

    def ao_tick(self, ctx: ContextoCombate, dt: float) -> None:
        dt = float(dt)
        if self.timer > 0.0:
            self.timer = max(0.0, self.timer - dt)
        if self.janela_abates > 0.0:
            self.janela_abates = max(0.0, self.janela_abates - dt)
            if self.janela_abates == 0.0:
                self.abates_recentes = 0

    def ao_abate(self, ctx: ContextoCombate, inimigo: Any, fonte: Any = None) -> None:
        if _eh_elite_ou_miniboss(inimigo) or getattr(inimigo, "is_caixa_som", False):
            self.timer = 3.5
            return
        self.abates_recentes += 1
        self.janela_abates = 3.0
        if self.abates_recentes >= 5:
            self.abates_recentes = 0
            self.timer = 3.5


class FirmwareCanhoesPerimetrais(EfeitoCombate):
    id_efeito = "canhoes_perimetrais"
    prioridade = 63

    def __init__(self):
        self.setores_cd: list[float] = [0.0] * 6

    def ao_tick(self, ctx: ContextoCombate, dt: float) -> None:
        for i in range(6):
            if self.setores_cd[i] > 0.0:
                self.setores_cd[i] = max(0.0, self.setores_cd[i] - float(dt))

    def ao_disparo(self, ctx: ContextoCombate, arma: Any, projeteis: list) -> list:
        if not projeteis or ctx.profundidade_recursao >= 1:
            return []
        p = projeteis[0]
        if getattr(p, "eh_replica", False):
            return []
        ang = math.atan2(p.dir_y, p.dir_x) % (2.0 * math.pi)
        setor = int((ang / (2.0 * math.pi)) * 6) % 6
        if self.setores_cd[setor] <= 0.0:
            self.setores_cd[setor] = 4.0
            n_pellets = max(1, int(getattr(_const, "SHOTGUN_PELLETS", 9)) // 2)
            spread = float(getattr(_const, "SHOTGUN_SPREAD_ANGULO", 0.45))
            dano_pellet = max(1, int(getattr(_const, "SHOTGUN_DANO", 10)))
            vel_pellet = float(getattr(_const, "SHOTGUN_VELOCIDADE_PROJETIL", 540.0))
            kb_pellet = 10.5 * 1.5
            meio_leque = spread / 2.0
            passo = spread / (n_pellets - 1) if n_pellets > 1 else 0.0
            reps: list[Projetil] = []
            for i in range(n_pellets):
                offset = (-meio_leque + i * passo) if n_pellets > 1 else 0.0
                cos_o = math.cos(offset)
                sin_o = math.sin(offset)
                dx = p.dir_x * cos_o - p.dir_y * sin_o
                dy = p.dir_x * sin_o + p.dir_y * cos_o
                rep = Projetil(
                    x=p.x,
                    y=p.y,
                    dir_x=dx,
                    dir_y=dy,
                    velocidade=vel_pellet,
                    dano=dano_pellet,
                    tempo_vida=1.2,
                    dono="jogador",
                    largura=6,
                    altura=6,
                    cor=(255, 110, 40),
                    knockback_forca=kb_pellet,
                )
                rep.eh_replica = True
                rep.aplicar_queimadura = 3.0
                reps.append(rep)
            return reps
        return []

    def ao_pos_render_mundo(self, ctx: ContextoCombate, superficie: Any, camera: Any = None) -> None:
        if ctx.jogador is None or superficie is None:
            return
        import pygame
        jx = float(getattr(ctx.jogador, "x", 0.0)) + float(getattr(ctx.jogador, "largura", 32)) * 0.5
        jy = float(getattr(ctx.jogador, "y", 0.0)) + float(getattr(ctx.jogador, "altura", 32)) * 0.5
        cx = int(round(camera.transform_x(jx))) if camera else int(round(jx))
        cy = int(round(camera.transform_y(jy))) if camera else int(round(jy))
        raio = 40
        rect = pygame.Rect(cx - raio, cy - raio, raio * 2, raio * 2)
        passo = (2.0 * math.pi) / 6.0
        folga = 0.08
        for i in range(6):
            a0 = i * passo + folga
            a1 = (i + 1) * passo - folga
            cd = self.setores_cd[i]
            if cd <= 0.0:
                pygame.draw.arc(superficie, (255, 130, 45), rect, -a1, -a0, 3)
                ang_mid = (a0 + a1) * 0.5
                p1 = (cx + int(round(math.cos(ang_mid) * (raio + 2))), cy + int(round(math.sin(ang_mid) * (raio + 2))))
                p2 = (cx + int(round(math.cos(ang_mid) * (raio + 8))), cy + int(round(math.sin(ang_mid) * (raio + 8))))
                pygame.draw.line(superficie, (255, 185, 90), p1, p2, 2)
            else:
                pygame.draw.arc(superficie, (70, 80, 95), rect, -a1, -a0, 2)
                prog = max(0.0, min(1.0, 1.0 - (cd / 4.0)))
                if prog > 0.02:
                    a_prog = a0 + (a1 - a0) * prog
                    pygame.draw.arc(superficie, (200, 95, 35), rect, -a_prog, -a0, 2)


class FirmwareSobrecargaEstrutural(EfeitoCombate):
    id_efeito = "sobrecarga_estrutural"
    prioridade = 64

    def __init__(self):
        self.ultimo_alvo_id: Optional[int] = None
        self.acertos_consecutivos: int = 0

    def ao_impacto(self, ctx: ContextoCombate, alvo: Any, dano: int, fonte: Any = None) -> dict | None:
        aid = id(alvo)
        if aid == self.ultimo_alvo_id:
            self.acertos_consecutivos += 1
        else:
            self.ultimo_alvo_id = aid
            self.acertos_consecutivos = 1

        eh_pesado = (
            "blindado" in getattr(alvo, "sprite_key", "")
            or "tank" in getattr(alvo, "sprite_key", "")
            or _eh_elite_ou_miniboss(alvo)
            or _eh_boss(alvo)
        )
        if self.acertos_consecutivos >= 3 or eh_pesado:
            self.acertos_consecutivos = 0
            hp_max = max(1, getattr(alvo, "hp_max", 50))
            return {
                "dano_extra": max(5, int(round(hp_max * 0.12))),
                "vulneravel": True,
                "vulneravel_mult": 1.20,
            }
        return None


class FirmwareOverclockTermico(EfeitoCombate):
    id_efeito = "overclock_termico"
    prioridade = 65

    def __init__(self):
        self.carga_residual: float = 0.0
        self.timer: float = 0.0

    def ao_tick(self, ctx: ContextoCombate, dt: float) -> None:
        if self.timer > 0.0:
            self.timer = max(0.0, self.timer - float(dt))
            if self.timer == 0.0:
                self.carga_residual = 0.0

    def ao_dano_recebido(self, ctx: ContextoCombate, quantidade: int, fonte: Any = None) -> None:
        self.carga_residual = min(1.0, self.carga_residual + 0.35)
        self.timer = 5.0

    def _descarregar_onda_frontal(self, ctx: ContextoCombate) -> None:
        if self.carga_residual <= 0.0 or ctx.jogador is None:
            return
        dano_onda = max(18, int(round(45 * self.carga_residual)))
        self.carga_residual = 0.0
        self.timer = 0.0
        jx = float(getattr(ctx.jogador, "x", 0.0)) + float(getattr(ctx.jogador, "largura", 32)) * 0.5
        jy = float(getattr(ctx.jogador, "y", 0.0)) + float(getattr(ctx.jogador, "altura", 32)) * 0.5
        ang_mira = float(getattr(ctx.jogador, "aim_angle", 0.0))
        if hasattr(ctx.jogador, "mira_x") and hasattr(ctx.jogador, "mira_y"):
            ang_mira = math.atan2(float(ctx.jogador.mira_y) - jy, float(ctx.jogador.mira_x) - jx)
        if ctx.particulas is not None and hasattr(ctx.particulas, "emitir_onda_choque"):
            ctx.particulas.emitir_onda_choque(jx, jy, raio_max=150.0, cor=(251, 146, 60))
        for inim in list(ctx.inimigos or []):
            if not getattr(inim, "vivo", True) or getattr(inim, "em_fase", False):
                continue
            ix = float(getattr(inim, "x", 0.0)) + float(getattr(inim, "largura", 28)) * 0.5
            iy = float(getattr(inim, "y", 0.0)) + float(getattr(inim, "altura", 28)) * 0.5
            if math.hypot(ix - jx, iy - jy) <= 155.0:
                ang_i = math.atan2(iy - jy, ix - jx)
                diff = abs((ang_i - ang_mira + math.pi) % (2.0 * math.pi) - math.pi)
                if diff <= math.radians(55.0):
                    _aplicar_dano_entidade(inim, dano_onda, ctx=ctx, origem="overclock_termico", ignorar_blindagem=True)

    def ao_parry(self, ctx: ContextoCombate, projeteis_rebatidos: list) -> None:
        self._descarregar_onda_frontal(ctx)

    def ao_disparo(self, ctx: ContextoCombate, arma: Any, projeteis: list) -> list:
        if self.carga_residual > 0.0 and any(
            getattr(p, "sobrecarregado", False) or getattr(p, "critico_nativo", False)
            for p in (projeteis or [])
        ):
            self._descarregar_onda_frontal(ctx)
        return []


class FirmwareSandboxIsolada(EfeitoCombate):
    id_efeito = "sandbox_isolada"
    prioridade = 66

    def __init__(self):
        self.cd_restante: float = 0.0
        self.cupulas: list[dict] = []

    def ao_tick(self, ctx: ContextoCombate, dt: float) -> None:
        dt = float(dt)
        if self.cd_restante > 0.0:
            self.cd_restante = max(0.0, self.cd_restante - dt)

        ativas: list[dict] = []
        for c in self.cupulas:
            c["tempo"] -= dt
            if c["tempo"] > 0.0:
                for p in ctx.projeteis:
                    if getattr(p, "dono", "jogador") == "inimigo" and getattr(p, "ativo", True):
                        if math.hypot(p.x - c["x"], p.y - c["y"]) <= c["raio"]:
                            p.ativo = False
                ativas.append(c)
        self.cupulas = ativas

    def ao_parry(self, ctx: ContextoCombate, projeteis_rebatidos: list) -> None:
        if self.cd_restante <= 0.0 and ctx.jogador is not None:
            self.cd_restante = 28.0
            self.cupulas.append(
                {
                    "x": float(getattr(ctx.jogador, "x", 0.0) + getattr(ctx.jogador, "largura", 32) * 0.5),
                    "y": float(getattr(ctx.jogador, "y", 0.0) + getattr(ctx.jogador, "altura", 32) * 0.5),
                    "raio": 95.0,
                    "tempo": 3.5,
                }
            )

    def ao_pos_render_mundo(self, ctx: ContextoCombate, superficie: Any, camera: Any = None) -> None:
        if not self.cupulas or superficie is None:
            return
        import pygame
        for c in self.cupulas:
            cx = int(camera.transform_x(c["x"])) if camera else int(c["x"])
            cy = int(camera.transform_y(c["y"])) if camera else int(c["y"])
            r_c = max(16, int(round(c.get("raio", 95.0))))
            pygame.draw.circle(superficie, (16, 185, 129), (cx, cy), r_c, width=2)
            pygame.draw.circle(superficie, (110, 231, 183), (cx, cy), max(8, r_c - 6), width=1)


class FirmwareResetVoraz(EfeitoCombate):
    id_efeito = "reset_voraz"
    prioridade = 67

    def __init__(self):
        self.janela_ativa: float = 0.0

    def ao_tick(self, ctx: ContextoCombate, dt: float) -> None:
        if self.janela_ativa > 0.0:
            self.janela_ativa = max(0.0, self.janela_ativa - float(dt))

    def ao_dash(self, ctx: ContextoCombate, origem: tuple[float, float], destino: tuple[float, float]) -> None:
        self.janela_ativa = 2.0

    def ao_parry(self, ctx: ContextoCombate, projeteis_rebatidos: list) -> None:
        self.janela_ativa = 2.0

    def ao_abate(self, ctx: ContextoCombate, inimigo: Any, fonte: Any = None) -> None:
        if self.janela_ativa > 0.0 and ctx.jogador is not None:
            if hasattr(ctx.jogador, "dash_cooldown_restante"):
                ctx.jogador.dash_cooldown_restante *= 0.5
            _reduzir_cd_parry(ctx, fator=0.5)


# =============================================================================
# GERENCIADOR DO PIPELINE B+
# =============================================================================


class GerenciadorEfeitosCombate:
    """Orquestra o despacho seletivo de hooks do Pipeline B+ em ordem determinística."""

    def __init__(self):
        self.efeitos: list[EfeitoCombate] = []
        self._mapa_efeitos: dict[str, EfeitoCombate] = {}

    def reconstruir(
        self,
        mods: ModificadoresGameplay,
        firmwares_equipados: list[str] | None = None,
    ) -> None:
        """
        Instancia APENAS os handlers das configs não-neutras ativas e firmwares equipados,
        preservando instâncias compatíveis já ativas (ex: progresso de RAM do Garbage Collector ao abrir Configs).
        """
        anteriores = dict(self._mapa_efeitos)
        ativos: list[EfeitoCombate] = []

        if mods.zoom_balistica_longa or mods.zoom_execucao_cd_red > 0.0:
            ant = anteriores.get("zoom_balistica")
            if isinstance(ant, EfeitoZoomBalistica):
                ant.balistica_longa = bool(mods.zoom_balistica_longa)
                ant.queima_roupa_mult = float(mods.zoom_queima_roupa_mult)
                ant.execucao_cd_red = float(mods.zoom_execucao_cd_red)
                ant.execucao_limiar_hp = float(mods.zoom_execucao_limiar_hp)
                ativos.append(ant)
            else:
                ativos.append(EfeitoZoomBalistica(mods))

        if mods.flick_shot_ativo:
            ant = anteriores.get("flick_shot")
            ativos.append(ant if isinstance(ant, EfeitoFlickShot) else EfeitoFlickShot())
        if mods.inimigos_ranged_bullet_hell:
            ant = anteriores.get("inimigos_ranged_bullet_hell")
            ativos.append(ant if isinstance(ant, EfeitoBulletHellFuel) else EfeitoBulletHellFuel())
        if mods.inercia_cinetica_nivel > 0:
            ant = anteriores.get("inercia_cinetica")
            if isinstance(ant, EfeitoInerciaCinetica):
                ant.nivel = max(1, int(mods.inercia_cinetica_nivel))
                ant.raio_colisao = 36.0 if ant.nivel == 1 else 48.0
                ativos.append(ant)
            else:
                ativos.append(EfeitoInerciaCinetica(mods.inercia_cinetica_nivel))
        if mods.pinhata_hardware_nivel > 0:
            ant = anteriores.get("pinhata_hardware")
            if isinstance(ant, EfeitoPinhataHardware):
                ant.nivel = max(1, int(mods.pinhata_hardware_nivel))
                ativos.append(ant)
            else:
                ativos.append(EfeitoPinhataHardware(mods.pinhata_hardware_nivel))
        if mods.clarao_fotossensivel:
            ant = anteriores.get("clarao_fotossensivel")
            ativos.append(ant if isinstance(ant, EfeitoClaraoFotossensivel) else EfeitoClaraoFotossensivel())
        if mods.polaridade_invertida:
            ant = anteriores.get("polaridade_invertida")
            ativos.append(ant if isinstance(ant, EfeitoPolaridadeInvertida) else EfeitoPolaridadeInvertida())
        if mods.garbage_collector:
            ant = anteriores.get("garbage_collector")
            ativos.append(ant if isinstance(ant, EfeitoGarbageCollector) else EfeitoGarbageCollector())
        if mods.latencia_ping:
            ant = anteriores.get("latencia_ping")
            ativos.append(ant if isinstance(ant, EfeitoLatenciaPing) else EfeitoLatenciaPing())
        if mods.modo_wireframe:
            ant = anteriores.get("modo_wireframe")
            ativos.append(ant if isinstance(ant, EfeitoModoWireframe) else EfeitoModoWireframe())
        if mods.dash_protocolo != "padrao":
            ant = anteriores.get("dash_protocolo")
            if isinstance(ant, EfeitoDashProtocolo) and ant.modo == mods.dash_protocolo:
                ativos.append(ant)
            else:
                ativos.append(EfeitoDashProtocolo(mods.dash_protocolo))
        if mods.dash_rastro != "padrao":
            ant = anteriores.get("dash_rastro")
            if isinstance(ant, EfeitoDashRastro) and ant.modo == mods.dash_rastro:
                ativos.append(ant)
            else:
                ativos.append(EfeitoDashRastro(mods.dash_rastro))
        if mods.parry_precisao == "postura_riposte" or mods.parry_efeito in (
            "firewall_estatico",
            "ventoinha_360",
        ):
            ant = anteriores.get("parry_avancado")
            if isinstance(ant, EfeitoParryAvancado):
                ant.precisao = mods.parry_precisao
                ant.efeito = mods.parry_efeito
                ativos.append(ant)
            else:
                ativos.append(EfeitoParryAvancado(mods.parry_precisao, mods.parry_efeito))

        fabrica_firmwares = {
            "gatilho_duplo": FirmwareGatilhoDuplo,
            "recarga_tatica": FirmwareRecargaTatica,
            "adrenalina_overclock": FirmwareAdrenalinaOverclock,
            "canhoes_perimetrais": FirmwareCanhoesPerimetrais,
            "sobrecarga_estrutural": FirmwareSobrecargaEstrutural,
            "overclock_termico": FirmwareOverclockTermico,
            "sandbox_isolada": FirmwareSandboxIsolada,
            "reset_voraz": FirmwareResetVoraz,
        }
        for chip_id in firmwares_equipados or []:
            cls = fabrica_firmwares.get(chip_id)
            if cls is not None:
                ant = anteriores.get(chip_id)
                ativos.append(ant if isinstance(ant, cls) else cls())

        ativos.sort(key=lambda e: e.prioridade)
        self.efeitos = ativos
        self._mapa_efeitos = {e.id_efeito: e for e in ativos}

    def obter_efeito(self, id_efeito: str) -> Optional[EfeitoCombate]:
        """Lookup O(1) do handler ativo pelo id_efeito canônico."""
        return self._mapa_efeitos.get(id_efeito)

    def obter_mult_cadencia(self) -> float:
        """Consolida multiplicadores dinâmicos de cadência de disparo dos efeitos B+ ativos."""
        mult = 1.0
        gc = self._mapa_efeitos.get("garbage_collector")
        if gc is not None and getattr(gc, "buff_cadencia_timer", 0.0) > 0.0:
            mult *= 1.40
        rastro = self._mapa_efeitos.get("dash_rastro")
        if rastro is not None and getattr(rastro, "sobreaquecimento_timer", 0.0) > 0.0:
            mult *= 0.75
        adr = self._mapa_efeitos.get("adrenalina_overclock")
        if adr is not None and getattr(adr, "timer", 0.0) > 0.0:
            mult *= 1.0 + 0.35 * (float(adr.timer) / 3.5)
        oc_term = self._mapa_efeitos.get("overclock_termico")
        if oc_term is not None and getattr(oc_term, "carga_residual", 0.0) > 0.0:
            mult *= 1.0 + 0.30 * float(oc_term.carga_residual)
        return mult

    def obter_mult_velocidade(self) -> float:
        """Consolida multiplicadores dinâmicos de velocidade do jogador dos efeitos B+ ativos."""
        mult = 1.0
        pol = self._mapa_efeitos.get("polaridade_invertida")
        if pol is not None and getattr(pol, "surto_timer", 0.0) > 0.0:
            mult *= 1.25
        adr = self._mapa_efeitos.get("adrenalina_overclock")
        if adr is not None and getattr(adr, "timer", 0.0) > 0.0:
            mult *= 1.0 + 0.45 * (float(adr.timer) / 3.5)
        return mult

    def obter_mult_dano_recebido(self) -> float:
        """Consolida redução de dano recebido de efeitos B+ (ex: Recarga Tática)."""
        mult = 1.0
        rec = self._mapa_efeitos.get("recarga_tatica")
        if rec is not None and getattr(rec, "pilhas_blindagem", 0) > 0:
            mult *= 0.92 ** int(rec.pilhas_blindagem)
        return mult

    def disparar_ao_tick(self, ctx: ContextoCombate, dt: float) -> None:
        for e in self.efeitos:
            e.ao_tick(ctx, dt)

    def disparar_ao_dash(
        self,
        ctx: ContextoCombate,
        origem: tuple[float, float],
        destino: tuple[float, float],
    ) -> None:
        for e in self.efeitos:
            e.ao_dash(ctx, origem, destino)

    def disparar_ao_dash_evasao(self, ctx: ContextoCombate, evento: Any = None) -> None:
        for e in self.efeitos:
            e.ao_dash_evasao(ctx, evento)

    def disparar_ao_parry(self, ctx: ContextoCombate, projeteis_rebatidos: list) -> None:
        for e in self.efeitos:
            e.ao_parry(ctx, projeteis_rebatidos)

    def disparar_ao_disparo(
        self, ctx: ContextoCombate, arma: Any, projeteis: list
    ) -> list:
        """
        Despacha ao_disparo com guarda anti-recursão estrita:
        bloqueia se profundidade_recursao >= 1 ou se todos os projéteis forem réplicas.
        """
        if ctx.profundidade_recursao >= 1:
            return []
        if projeteis and all(
            getattr(p, "eh_replica", False) or getattr(p, "origem_holograma", False)
            for p in projeteis
        ):
            return []

        extras: list = []
        for e in self.efeitos:
            novos = e.ao_disparo(ctx, arma, projeteis)
            if novos:
                extras.extend(novos)
        return extras

    def disparar_ao_impacto(
        self, ctx: ContextoCombate, alvo: Any, dano: int, fonte: Any = None
    ) -> dict:
        consolidado: dict[str, Any] = {}
        for e in self.efeitos:
            res = e.ao_impacto(ctx, alvo, dano, fonte)
            if res:
                consolidado.update(res)
        return consolidado

    def disparar_ao_abate(
        self, ctx: ContextoCombate, inimigo: Any, fonte: Any = None
    ) -> None:
        for e in self.efeitos:
            e.ao_abate(ctx, inimigo, fonte)

    def disparar_ao_dano_recebido(
        self, ctx: ContextoCombate, quantidade: int, fonte: Any = None
    ) -> None:
        for e in self.efeitos:
            e.ao_dano_recebido(ctx, quantidade, fonte)

    def disparar_ao_pos_render_mundo(
        self, ctx: ContextoCombate, superficie: Any, camera: Any = None
    ) -> None:
        for e in self.efeitos:
            e.ao_pos_render_mundo(ctx, superficie, camera)
