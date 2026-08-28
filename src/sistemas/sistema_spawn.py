"""
Sistema de Spawn de Inimigos — Protocolo: Batata
Gera ondas progressivas de inimigos fora do campo de visão da câmera
com escalonamento de densidade, taxa de spawn e teto populacional suave.
"""

import random
from src.entidades.inimigo_padrao import InimigoPadrao
from src.utils.constantes import (
    SPAWN_INTERVALO_INICIAL, SPAWN_INTERVALO_MINIMO,
    SPAWN_DISTANCIA_OFFSET, LARGURA_TELA, ALTURA_TELA,
    LARGURA_ARENA, ALTURA_ARENA
)
from src.utils.math_utils import clamp


class SistemaSpawn:
    """
    Controlador do surgimento de inimigos na arena ao redor do jogador.
    """

    def __init__(self, max_ativos: int = 60):
        self.tempo_decorrido = 0.0
        self.timer_spawn = 0.0
        self.max_ativos = int(max_ativos)

    def intervalo_spawn(self, tempo_s: float) -> float:
        """
        Calcula o intervalo de tempo entre spawns em segundos.
        Fórmula: T_spawn(t) = max(0.40s, 1.80s - 0.012s * t)
        """
        return max(SPAWN_INTERVALO_MINIMO, SPAWN_INTERVALO_INICIAL - 0.012 * tempo_s)

    def tamanho_lote(self, tempo_s: float) -> int:
        """
        Calcula a quantidade de inimigos gerados por pulso de spawn.
        Fórmula: N_batch(t) = min(8, 1 + floor(t / 25))
        """
        return min(8, 1 + int(tempo_s // 25.0))

    def gerar_posicao_spawn(
        self,
        camera_x: float,
        camera_y: float,
        view_w: float = float(LARGURA_TELA),
        view_h: float = float(ALTURA_TELA),
        margem: float = float(SPAWN_DISTANCIA_OFFSET),
        arena_w: float = float(LARGURA_ARENA),
        arena_h: float = float(ALTURA_ARENA)
    ) -> tuple[float, float]:
        """
        Gera uma coordenada (x, y) no anel perimetral imediatamente fora da visão da câmera.
        """
        borda = random.choice(["topo", "base", "esquerda", "direita"])

        if borda == "topo":
            x = random.uniform(camera_x - margem, camera_x + view_w + margem)
            y = camera_y - margem
        elif borda == "base":
            x = random.uniform(camera_x - margem, camera_x + view_w + margem)
            y = camera_y + view_h + margem
        elif borda == "esquerda":
            x = camera_x - margem
            y = random.uniform(camera_y - margem, camera_y + view_h + margem)
        else:  # direita
            x = camera_x + view_w + margem
            y = random.uniform(camera_y - margem, camera_y + view_h + margem)

        # Clampa suavemente na margem exterior da arena
        x = clamp(x, -margem, arena_w + margem)
        y = clamp(y, -margem, arena_h + margem)
        return x, y

    def update(
        self,
        dt: float,
        camera_x: float,
        camera_y: float,
        total_inimigos_vivos: int,
        view_w: float = float(LARGURA_TELA),
        view_h: float = float(ALTURA_TELA),
        arena_w: float = float(LARGURA_ARENA),
        arena_h: float = float(ALTURA_ARENA)
    ) -> list:
        """
        Atualiza os cronômetros e gera novos inimigos quando o intervalo é atingido.
        """
        self.tempo_decorrido += dt
        self.timer_spawn += dt

        intervalo = self.intervalo_spawn(self.tempo_decorrido)
        if self.timer_spawn < intervalo:
            return []

        self.timer_spawn = 0.0

        vagas_disponiveis = self.max_ativos - total_inimigos_vivos
        if vagas_disponiveis <= 0:
            return []

        qtd_a_gerar = min(self.tamanho_lote(self.tempo_decorrido), vagas_disponiveis)
        novos_inimigos = []

        for _ in range(qtd_a_gerar):
            sx, sy = self.gerar_posicao_spawn(
                camera_x=camera_x,
                camera_y=camera_y,
                view_w=view_w,
                view_h=view_h,
                arena_w=arena_w,
                arena_h=arena_h
            )
            novo = InimigoPadrao(x=sx, y=sy)
            novos_inimigos.append(novo)

        return novos_inimigos
