"""
Entidade de Projétil — Protocolo: Batata
Controla a física, tempo de vida, renderização e colisões de tiros no jogo.
"""

import os
import pygame
from src.utils.constantes import ASSETS_DIR, ASSET_PATHS, obter_caminho_asset, AMARELO_XP
from src.utils.math_utils import normalizar_vetor


class Projetil:
    """
    Representa um projétil disparado pelo jogador ou inimigos.
    """
    _sprite_surface = None

    def __init__(
        self,
        x: float,
        y: float,
        dir_x: float,
        dir_y: float,
        velocidade: float = 420.0,
        dano: int = 12,
        tempo_vida: float = 2.5,
        dono: str = "jogador",
        largura: int = 8,
        altura: int = 8
    ):
        self.x = float(x)
        self.y = float(y)
        self.dir_x, self.dir_y = normalizar_vetor(dir_x, dir_y)
        self.velocidade = float(velocidade)
        self.dano = int(dano)
        self.tempo_vida = float(tempo_vida)
        self.tempo_vida_restante = float(tempo_vida)
        self.dono = dono
        self.largura = int(largura)
        self.altura = int(altura)
        self.width = self.largura
        self.height = self.altura
        self.ativo = True

    @classmethod
    def _carregar_sprite(cls):
        if cls._sprite_surface is None:
            try:
                caminho = obter_caminho_asset("projetil_pistola")
                if os.path.isfile(caminho):
                    cls._sprite_surface = pygame.image.load(caminho).convert_alpha()
            except Exception:
                cls._sprite_surface = None
        return cls._sprite_surface

    def update(self, dt: float):
        """Atualiza a posição do projétil e decrementa o tempo de vida."""
        if not self.ativo:
            return

        self.x += self.dir_x * self.velocidade * dt
        self.y += self.dir_y * self.velocidade * dt
        self.tempo_vida_restante -= dt

        if self.tempo_vida_restante <= 0.0:
            self.ativo = False

    def get_rect(self) -> tuple[float, float, int, int]:
        """Retorna (x, y, largura, altura) para teste de colisão AABB."""
        return (self.x, self.y, self.largura, self.altura)

    def desenhar(self, janela, camera=None):
        """Renderiza o projétil na tela virtual com coordenadas de câmera."""
        if not self.ativo:
            return

        draw_x = camera.transform_x(self.x) if camera else self.x
        draw_y = camera.transform_y(self.y) if camera else self.y

        # Não desenha se estiver completamente fora da tela visível
        if draw_x < -20 or draw_x > janela.largura + 20 or draw_y < -20 or draw_y > janela.altura + 20:
            return

        sprite = self._carregar_sprite()
        if sprite is not None:
            janela.screen.blit(sprite, (draw_x, draw_y))
        else:
            # Fallback gráfico: retângulo amarelo vibrante
            pygame.draw.rect(
                janela.screen,
                AMARELO_XP,
                (int(draw_x), int(draw_y), self.largura, self.altura)
            )
