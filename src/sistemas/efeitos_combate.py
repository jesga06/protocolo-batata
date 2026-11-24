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


def _aplicar_dano_entidade(alvo: Any, dano: int) -> None:
    dano_int = max(0, int(dano))
    if hasattr(alvo, "receber_dano"):
        alvo.receber_dano(dano_int)
    elif hasattr(alvo, "sofrer_dano"):
        alvo.sofrer_dano(dano_int)
    elif hasattr(alvo, "hp"):
        alvo.hp = max(0, int(alvo.hp) - dano_int)
        if alvo.hp <= 0:
            alvo.vivo = False


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
    sistema_combo: Any = None
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

    def ao_dash(
        self,
        ctx: ContextoCombate,
        origem: tuple[float, float],
        destino: tuple[float, float],
    ) -> None:
        self._dash_id += 1
        self._empurrados_no_dash.clear()

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

        abates_golpe = 0
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
                    _aplicar_dano_entidade(dst, dano_col)
                    if not getattr(dst, "vivo", True):
                        abates_golpe += 1
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

        if abates_golpe >= 3 and ctx.sistema_conquistas is not None:
            ctx.sistema_conquistas.registrar_evento(
                "abate_boliche", abates_golpe, {"abates_golpe": abates_golpe}
            )


class EfeitoPinhataHardware(EfeitoCombate):
    id_efeito = "pinhata_hardware"
    prioridade = 40

    def __init__(self, nivel: int = 1):
        self.nivel = max(1, int(nivel))

    def ao_impacto(self, ctx: ContextoCombate, alvo: Any, dano: int, fonte: Any = None) -> dict | None:
        hp = getattr(alvo, "hp", 0)
        hp_max = max(1, getattr(alvo, "hp_max", 1))
        perdido_ratio = 1.0 - (max(0, hp) / hp_max)
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

    def ao_tick(self, ctx: ContextoCombate, dt: float) -> None:
        dt = float(dt)
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
                if ctx.sistema_conquistas is not None and apagados > 0:
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
        if ctx.jogador is None or not ctx.projeteis:
            return 0
        jx = getattr(ctx.jogador, "x", 0.0) + getattr(ctx.jogador, "largura", 32) * 0.5
        jy = getattr(ctx.jogador, "y", 0.0) + getattr(ctx.jogador, "altura", 32) * 0.5
        apagados = 0
        for p in ctx.projeteis:
            if getattr(p, "dono", "jogador") == "inimigo" and getattr(p, "ativo", True):
                if math.hypot(getattr(p, "x", 0.0) - jx, getattr(p, "y", 0.0) - jy) <= 260.0:
                    p.ativo = False
                    apagados += 1
        return apagados


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
                    _aplicar_dano_entidade(alvo, eco["dano"])
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

    def ao_impacto(self, ctx: ContextoCombate, alvo: Any, dano: int, fonte: Any = None) -> dict | None:
        ang_no = getattr(alvo, "_wireframe_no_ang", None)
        if ang_no is None:
            ang_no = ((id(alvo) % 360) * math.pi) / 180.0
            alvo._wireframe_no_ang = ang_no

        if fonte is not None and hasattr(fonte, "dir_x") and hasattr(fonte, "dir_y"):
            ang_tiro = math.atan2(-fonte.dir_y, -fonte.dir_x)
            diff = abs((ang_tiro - ang_no + math.pi) % (2.0 * math.pi) - math.pi)
            if diff <= math.radians(60.0):
                return {"dano_verdadeiro": True, "vulneravel": True}
        return None


class EfeitoDashProtocolo(EfeitoCombate):
    id_efeito = "dash_protocolo"
    prioridade = 18

    def __init__(self, modo: str):
        self.modo = modo
        self.snapshots: deque[tuple[float, float, int]] = deque(maxlen=30)
        self._amostra_timer: float = 0.0
        self.sombra_ativa: Optional[EntidadeHolograma] = None
        self.linhas_eletricas: list[dict] = []

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

    def ao_dash(
        self,
        ctx: ContextoCombate,
        origem: tuple[float, float],
        destino: tuple[float, float],
    ) -> None:
        if self.modo == "teleporte_buffer" and ctx.jogador is not None:
            ctx.jogador.x = float(destino[0])
            ctx.jogador.y = float(destino[1])
            if hasattr(ctx.jogador, "dash_cooldown_restante"):
                ctx.jogador.dash_cooldown_restante = float(ctx.jogador.dash_cooldown_restante) + 0.6
            self.linhas_eletricas.append({"origem": origem, "destino": destino, "tempo": 0.35})
            for inim in ctx.inimigos:
                if not getattr(inim, "vivo", True):
                    continue
                ix = getattr(inim, "x", 0.0) + getattr(inim, "largura", 32) * 0.5
                iy = getattr(inim, "y", 0.0) + getattr(inim, "altura", 32) * 0.5
                if _distancia_ponto_segmento(ix, iy, origem[0], origem[1], destino[0], destino[1]) <= 36.0:
                    _aplicar_dano_entidade(inim, 28)

        elif self.modo == "sombra_espelho" and ctx.jogador is not None:
            if self.sombra_ativa is not None and self.sombra_ativa.vivo:
                sx, sy = self.sombra_ativa.x, self.sombra_ativa.y
                self.sombra_ativa.x, self.sombra_ativa.y = ctx.jogador.x, ctx.jogador.y
                ctx.jogador.x, ctx.jogador.y = sx, sy
            else:
                sombra = EntidadeHolograma(
                    x=destino[0],
                    y=destino[1],
                    modo="sombra",
                    duracao=3.5,
                    dano_mult=0.55,
                )
                self.sombra_ativa = sombra
                if ctx.hologramas is not None:
                    ctx.hologramas.append(sombra)

        elif self.modo == "rollback_estado" and ctx.jogador is not None and self.snapshots:
            rx, ry, rhp = self.snapshots[0]
            ctx.jogador.x = rx
            ctx.jogador.y = ry
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
                    _aplicar_dano_entidade(inim, 30)
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
        alvo_x = getattr(ctx.jogador, "mira_x", self.sombra_ativa.x + 100.0)
        alvo_y = getattr(ctx.jogador, "mira_y", self.sombra_ativa.y)
        return self.sombra_ativa.replicar_disparo(projeteis, alvo_x, alvo_y, max_replicas=12)


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
                                _aplicar_dano_entidade(inim, 8)
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
                    v_ativos.append(v)
            self.vortices[:] = v_ativos

        if self.feixes_subprocesso:
            self.feixes_subprocesso[:] = [
                {**f, "tempo": f["tempo"] - dt}
                for f in self.feixes_subprocesso
                if f["tempo"] - dt > 0.0
            ]

        # Subprocesso atrasado (dispara após 0.75s)
        if self.subprocessos_pendentes:
            restantes: list[dict] = []
            for sp in self.subprocessos_pendentes:
                sp["tempo"] -= dt
                if sp["tempo"] <= 0.0:
                    ox, oy = sp["origem"]
                    dx, dy = sp["destino"]
                    for inim in ctx.inimigos:
                        if not getattr(inim, "vivo", True):
                            continue
                        ix = getattr(inim, "x", 0.0) + getattr(inim, "largura", 32) * 0.5
                        iy = getattr(inim, "y", 0.0) + getattr(inim, "altura", 32) * 0.5
                        if _distancia_ponto_segmento(ix, iy, ox, oy, dx, dy) <= 40.0:
                            _aplicar_dano_entidade(inim, 30)
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
            self.vortices.append({"x": float(destino[0]), "y": float(destino[1]), "raio": 95.0, "tempo": 2.5})
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

    def _executar_corte_ventoinha(self, ctx: ContextoCombate) -> None:
        if ctx.jogador is None:
            return
        jx = getattr(ctx.jogador, "x", 0.0) + getattr(ctx.jogador, "largura", 32) * 0.5
        jy = getattr(ctx.jogador, "y", 0.0) + getattr(ctx.jogador, "altura", 32) * 0.5
        for inim in ctx.inimigos:
            if not getattr(inim, "vivo", True):
                continue
            ix = getattr(inim, "x", 0.0) + getattr(inim, "largura", 32) * 0.5
            iy = getattr(inim, "y", 0.0) + getattr(inim, "altura", 32) * 0.5
            if math.hypot(ix - jx, iy - jy) <= 95.0:
                _aplicar_dano_entidade(inim, 24)

    def ao_tick(self, ctx: ContextoCombate, dt: float) -> None:
        dt = float(dt)
        if self.barreiras_firewall:
            restantes: list[dict] = []
            for b in self.barreiras_firewall:
                b["tempo"] -= dt
                if b["tempo"] > 0.0:
                    for p in ctx.projeteis:
                        if getattr(p, "dono", "jogador") == "inimigo" and getattr(p, "ativo", True):
                            if math.hypot(p.x - b["x"], p.y - b["y"]) <= b["raio"]:
                                p.ativo = False
                    restantes.append(b)
            self.barreiras_firewall = restantes

        if self.ventoinha_timer > 0.0:
            self.ventoinha_timer = max(0.0, self.ventoinha_timer - dt)
            if ctx.jogador is not None:
                jx = getattr(ctx.jogador, "x", 0.0)
                jy = getattr(ctx.jogador, "y", 0.0)
                for p in ctx.projeteis:
                    if getattr(p, "dono", "jogador") == "inimigo" and getattr(p, "ativo", True):
                        if math.hypot(p.x - jx, p.y - jy) <= 110.0:
                            p.ativo = False
            if self.cortes_pendentes > 0:
                self._corte_intervalo -= dt
                if self._corte_intervalo <= 0.0:
                    self._executar_corte_ventoinha(ctx)
                    self.cortes_pendentes -= 1
                    self._corte_intervalo = 0.30

    def ao_parry(self, ctx: ContextoCombate, projeteis_rebatidos: list) -> None:
        if self.precisao == "postura_riposte" and ctx.jogador is not None:
            ctx.jogador.enraizado_timer = 0.45
            ctx.jogador.riposte_invuln_timer = 0.45
            jx = getattr(ctx.jogador, "x", 0.0)
            jy = getattr(ctx.jogador, "y", 0.0)
            for inim in ctx.inimigos:
                if getattr(inim, "vivo", True):
                    if math.hypot(getattr(inim, "x", 0.0) - jx, getattr(inim, "y", 0.0) - jy) <= 180.0:
                        _aplicar_stun_entidade(inim, 1.5)

        if self.efeito == "firewall_estatico" and ctx.jogador is not None:
            self.barreiras_firewall.append(
                {
                    "x": getattr(ctx.jogador, "x", 0.0) + 40.0,
                    "y": getattr(ctx.jogador, "y", 0.0),
                    "raio": 65.0,
                    "tempo": 2.5,
                }
            )
        elif self.efeito == "ventoinha_360" and ctx.jogador is not None:
            self.ventoinha_timer = 0.6
            self.cortes_pendentes = 1
            self._corte_intervalo = 0.30
            self._executar_corte_ventoinha(ctx)
            jx = getattr(ctx.jogador, "x", 0.0)
            jy = getattr(ctx.jogador, "y", 0.0)
            for p in ctx.projeteis:
                if getattr(p, "dono", "jogador") == "inimigo" and getattr(p, "ativo", True):
                    if math.hypot(p.x - jx, p.y - jy) <= 110.0:
                        p.ativo = False


# =============================================================================
# 9 HANDLERS DE CHIPS DE FIRMWARE
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
        if _eh_elite_ou_miniboss(inimigo):
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
            rep = Projetil(
                x=p.x,
                y=p.y,
                dir_x=p.dir_x,
                dir_y=p.dir_y,
                velocidade=p.velocidade * 1.15,
                dano=max(1, int(round(p.dano * 0.85))),
                tempo_vida=1.4,
                dono="jogador",
                cor=(255, 110, 40),
            )
            rep.eh_replica = True
            return [rep]
        return []


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
            return {"dano_extra": max(5, int(round(hp_max * 0.12))), "vulneravel": True}
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

    def ao_parry(self, ctx: ContextoCombate, projeteis_rebatidos: list) -> None:
        if self.carga_residual > 0.0:
            self.carga_residual = 0.0
            self.timer = 0.0


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


class FirmwareMedidorEstilo(EfeitoCombate):
    id_efeito = "medidor_estilo"
    prioridade = 68

    def __init__(self):
        self._ativado: bool = False

    def ao_tick(self, ctx: ContextoCombate, dt: float) -> None:
        if not self._ativado and ctx.sistema_combo is not None:
            if hasattr(ctx.sistema_combo, "definir_modo_estilo"):
                ctx.sistema_combo.definir_modo_estilo(True)
                self._ativado = True


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
        """Instancia APENAS os handlers das configs não-neutras ativas e firmwares equipados."""
        ativos: list[EfeitoCombate] = []

        if mods.zoom_balistica_longa or mods.zoom_execucao_cd_red > 0.0:
            ativos.append(EfeitoZoomBalistica(mods))
        if mods.flick_shot_ativo:
            ativos.append(EfeitoFlickShot())
        if mods.inimigos_ranged_bullet_hell:
            ativos.append(EfeitoBulletHellFuel())
        if mods.inercia_cinetica_nivel > 0:
            ativos.append(EfeitoInerciaCinetica(mods.inercia_cinetica_nivel))
        if mods.pinhata_hardware_nivel > 0:
            ativos.append(EfeitoPinhataHardware(mods.pinhata_hardware_nivel))
        if mods.clarao_fotossensivel:
            ativos.append(EfeitoClaraoFotossensivel())
        if mods.polaridade_invertida:
            ativos.append(EfeitoPolaridadeInvertida())
        if mods.garbage_collector:
            ativos.append(EfeitoGarbageCollector())
        if mods.latencia_ping:
            ativos.append(EfeitoLatenciaPing())
        if mods.modo_wireframe:
            ativos.append(EfeitoModoWireframe())
        if mods.dash_protocolo != "padrao":
            ativos.append(EfeitoDashProtocolo(mods.dash_protocolo))
        if mods.dash_rastro != "padrao":
            ativos.append(EfeitoDashRastro(mods.dash_rastro))
        if mods.parry_precisao == "postura_riposte" or mods.parry_efeito in (
            "firewall_estatico",
            "ventoinha_360",
        ):
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
            "medidor_estilo": FirmwareMedidorEstilo,
        }
        for chip_id in firmwares_equipados or []:
            cls = fabrica_firmwares.get(chip_id)
            if cls is not None:
                ativos.append(cls())

        ativos.sort(key=lambda e: e.prioridade)
        self.efeitos = ativos
        self._mapa_efeitos = {e.id_efeito: e for e in ativos}

    def obter_efeito(self, id_efeito: str) -> Optional[EfeitoCombate]:
        """Lookup O(1) do handler ativo pelo id_efeito canônico."""
        return self._mapa_efeitos.get(id_efeito)

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
