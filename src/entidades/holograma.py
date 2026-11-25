"""
Entidade Holograma — Protocolo: Batata
Clones holográficos para as opções de Dash:
- modo="sombra" (sombra_espelho): replica disparos/parries (~55% dano) com guarda anti-recursão.
- modo="clone_agro" (thread_fantasma): atrai agro de inimigos próximos e explode ao expirar/morrer.
"""

import math
import pygame
from src.entidades.projetil import Projetil
from src.utils.math_utils import normalizar_vetor


class EntidadeHolograma:
    """Entidade holográfica auxiliar para Sombra Espelho e Thread Fantasma."""

    def __init__(
        self,
        x: float,
        y: float,
        modo: str = "sombra",
        duracao: float = 3.5,
        hp: int = 80,
        raio_agro: float = 280.0,
        dano_mult: float = 0.55,
    ):
        self.x = float(x)
        self.y = float(y)
        self.modo = modo if modo in ("sombra", "clone_agro") else "sombra"
        self.largura = 32
        self.altura = 32
        self.vivo = True
        self.tempo_restante = float(duracao)
        self.hp = int(hp)
        self.hp_max = int(hp)
        self.raio_agro = float(raio_agro)
        self.dano_mult = float(dano_mult)
        self.explodiu = False
        self._afetados_agro: list = []
        self._surface_cache: pygame.Surface | None = None

    def sofrer_dano(self, quantidade: int) -> None:
        """Aplica dano ao holograma (relevante para clone_agro)."""
        if not self.vivo:
            return
        self.hp = max(0, self.hp - max(0, int(quantidade)))
        if self.hp <= 0:
            self.vivo = False

    def _limpar_agro(self) -> None:
        """Limpa pos_alvo_override de todos os inimigos atraídos pelo clone."""
        for inim in self._afetados_agro:
            if hasattr(inim, "pos_alvo_override"):
                inim.pos_alvo_override = None
        self._afetados_agro.clear()

    def update(self, dt: float, inimigos: list | None = None) -> dict:
        """
        Atualiza temporizador, atração de agro (clone_agro) e detonação ao morrer/expirar.
        Retorna {"explodir": True, ...} quando clone_agro explode.
        """
        if not self.vivo:
            self._limpar_agro()
            if self.modo == "clone_agro" and not self.explodiu:
                self.explodiu = True
                return {
                    "explodir": True,
                    "x": self.x + self.largura * 0.5,
                    "y": self.y + self.altura * 0.5,
                    "raio": 115.0,
                    "dano": 45,
                }
            return {}

        self.tempo_restante -= float(dt)
        if self.tempo_restante <= 0.0 or self.hp <= 0:
            self.vivo = False
            self._limpar_agro()
            if self.modo == "clone_agro" and not self.explodiu:
                self.explodiu = True
                return {
                    "explodir": True,
                    "x": self.x + self.largura * 0.5,
                    "y": self.y + self.altura * 0.5,
                    "raio": 115.0,
                    "dano": 45,
                }
            return {}

        if self.modo == "clone_agro" and inimigos is not None:
            cx = self.x + self.largura * 0.5
            cy = self.y + self.altura * 0.5
            novos_afetados: list = []
            for inim in inimigos:
                if not getattr(inim, "vivo", True):
                    continue
                if getattr(inim, "is_boss", False) or getattr(inim, "eh_boss", False):
                    continue
                ix = getattr(inim, "x", 0.0) + getattr(inim, "largura", 32) * 0.5
                iy = getattr(inim, "y", 0.0) + getattr(inim, "altura", 32) * 0.5
                if math.hypot(ix - cx, iy - cy) <= self.raio_agro:
                    inim.pos_alvo_override = (cx, cy)
                    novos_afetados.append(inim)

            for antigo in self._afetados_agro:
                if antigo not in novos_afetados and hasattr(antigo, "pos_alvo_override"):
                    antigo.pos_alvo_override = None
            self._afetados_agro = novos_afetados

        return {}

    def replicar_disparo(
        self,
        projeteis_origem: list,
        alvo_x: float,
        alvo_y: float,
        max_replicas: int = 12,
    ) -> list[Projetil]:
        """
        Replica projéteis originais a partir da posição da sombra em direção a (alvo_x, alvo_y).
        Guarda anti-recursão: ignora qualquer projétil com origem_holograma=True ou eh_replica=True
        e marca todas as réplicas com ambas as flags.
        """
        if self.modo != "sombra" or not self.vivo:
            return []

        cx = self.x + self.largura * 0.5
        cy = self.y + self.altura * 0.5
        base_dx, base_dy = normalizar_vetor(alvo_x - cx, alvo_y - cy)
        if base_dx == 0.0 and base_dy == 0.0:
            base_dx, base_dy = 1.0, 0.0
        ang_alvo = math.atan2(base_dy, base_dx)

        # Preserva leque relativo em disparos multiplos (ex.: escopeta) mantendo centro na mira
        angulos_orig = [
            math.atan2(float(getattr(p, "dir_y", 0.0)), float(getattr(p, "dir_x", 1.0)))
            for p in projeteis_origem
            if not (getattr(p, "origem_holograma", False) or getattr(p, "eh_replica", False))
        ]
        ang_ref = 0.0
        if angulos_orig:
            sx_ang = sum(math.cos(a) for a in angulos_orig)
            sy_ang = sum(math.sin(a) for a in angulos_orig)
            if abs(sx_ang) > 1e-6 or abs(sy_ang) > 1e-6:
                ang_ref = math.atan2(sy_ang, sx_ang)

        replicas: list[Projetil] = []
        for p in projeteis_origem:
            if getattr(p, "origem_holograma", False) or getattr(p, "eh_replica", False):
                continue
            if len(replicas) >= max_replicas:
                break
            ang_p = math.atan2(float(getattr(p, "dir_y", 0.0)), float(getattr(p, "dir_x", 1.0)))
            offset_ang = math.atan2(math.sin(ang_p - ang_ref), math.cos(ang_p - ang_ref)) if len(angulos_orig) > 1 else 0.0
            ang_final = ang_alvo + offset_ang
            dx = math.cos(ang_final)
            dy = math.sin(ang_final)
            dano_rep = max(1, int(round(getattr(p, "dano", 10) * self.dano_mult)))
            vel_rep = float(getattr(p, "velocidade", 420.0))
            rep = Projetil(
                x=cx,
                y=cy,
                dir_x=dx,
                dir_y=dy,
                velocidade=vel_rep,
                dano=dano_rep,
                tempo_vida=float(getattr(p, "tempo_vida", 2.0)),
                dono="jogador",
                largura=int(getattr(p, "largura", 8)),
                altura=int(getattr(p, "altura", 8)),
                sprite_key=getattr(p, "sprite_key", "projetil_pistola"),
                cor=(80, 230, 255),
                perfurante=bool(getattr(p, "perfurante", False)),
            )
            rep.homing_ativo = bool(getattr(p, "homing_ativo", False))
            rep.homing_alvo_cursor = bool(getattr(p, "homing_alvo_cursor", False))
            rep.homing_taxa_rad = float(getattr(p, "homing_taxa_rad", 1.65))
            rep.homing_radar_dot = float(getattr(p, "homing_radar_dot", 0.25))
            rep.origem_holograma = True
            rep.eh_replica = True
            replicas.append(rep)

        return replicas

    def desenhar(self, janela, camera=None) -> None:
        """Renderiza o holograma com surface cacheada (zero alocação de fonte)."""
        if not self.vivo:
            return
        if self._surface_cache is None:
            surf = pygame.Surface((self.largura, self.altura), pygame.SRCALPHA)
            cor = (70, 230, 255, 165) if self.modo == "sombra" else (240, 80, 220, 175)
            borda = (180, 255, 255, 220) if self.modo == "sombra" else (255, 170, 240, 220)
            pygame.draw.rect(surf, cor, (0, 0, self.largura, self.altura), border_radius=6)
            pygame.draw.rect(surf, borda, (0, 0, self.largura, self.altura), width=2, border_radius=6)
            self._surface_cache = surf

        screen = getattr(janela, "screen", janela)
        if camera is not None and hasattr(camera, "transform_x") and hasattr(camera, "transform_y"):
            px = int(camera.transform_x(self.x))
            py = int(camera.transform_y(self.y))
        else:
            ox = camera.offset_x if camera is not None and hasattr(camera, "offset_x") else 0.0
            oy = camera.offset_y if camera is not None and hasattr(camera, "offset_y") else 0.0
            px = int(self.x - ox)
            py = int(self.y - oy)
        screen.blit(self._surface_cache, (px, py))
