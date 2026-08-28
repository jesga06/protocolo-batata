"""
Drone Base — Protocolo: Batata
Classe base para todos os Drones Companheiros de suporte e combate que orbitam o jogador (Slot 4).
Implementa física orbital R=48px, theta(t) = theta_0 + omega*t, duração de 30s e vulnerabilidade a fogo amigo.
"""

import math
import os
import pygame
from src.utils.constantes import ASSETS_DIR, ASSET_PATHS, obter_caminho_asset, AZUL_CIANO, VERDE_CURA, DOURADO
from src.utils.math_utils import normalizar_vetor


class DroneBase:
    """
    Entidade base de Drone Orbital no Slot 4 de equipamentos.
    """
    _sprites: dict = {}

    def __init__(
        self,
        nome: str = "Drone Base",
        icone_asset: str = "drone_combate",
        sprite_key: str = "drone_combate",
        tempo_vida: float = 30.0,
        raio_orbita: float = 48.0,
        velocidade_angular: float = 2.5,
        hp: int = 1,
        largura: int = 24,
        altura: int = 24
    ):
        self.nome = str(nome)
        self.icone_asset = str(icone_asset)
        self.sprite_key = str(sprite_key)
        self.tempo_vida = float(tempo_vida)
        self.tempo_restante = float(tempo_vida)
        self.raio_orbita = float(raio_orbita)
        self.angulo_orbita = 0.0
        self.velocidade_angular = float(velocidade_angular)
        self.hp = int(hp)
        self.hp_max = int(hp)
        self.largura = int(largura)
        self.altura = int(altura)
        self.width = self.largura
        self.height = self.altura

        self.x = 0.0
        self.y = 0.0
        self.ativo = True

    @classmethod
    def _carregar_sprite(cls, sprite_key: str):
        if sprite_key not in cls._sprites:
            try:
                caminho = obter_caminho_asset(sprite_key)
                if os.path.isfile(caminho):
                    cls._sprites[sprite_key] = pygame.image.load(caminho).convert_alpha()
                else:
                    cls._sprites[sprite_key] = None
            except Exception:
                cls._sprites[sprite_key] = None
        return cls._sprites.get(sprite_key)

    def receber_dano(self, dano: int):
        """Aplica dano ao drone (regra de Fogo Amigo com 1 HP)."""
        self.hp = max(0, self.hp - int(dano))
        if self.hp <= 0:
            self.ativo = False

    def update(self, dt: float, jogador=None, *args, **kwargs):
        """
        Atualiza o timer de vida, a física orbital ao redor do jogador e a posição no mundo.
        """
        if not self.ativo:
            return

        self.tempo_restante -= dt
        if self.tempo_restante <= 0.0 or self.hp <= 0:
            self.ativo = False
            return

        # Incrementa o ângulo orbital
        self.angulo_orbita = (self.angulo_orbita + self.velocidade_angular * dt) % (2.0 * math.pi)

        # Atualiza coordenadas orbitais a partir do centro do jogador
        if jogador is not None:
            cx = jogador.x + getattr(jogador, "largura", 32) / 2.0
            cy = jogador.y + getattr(jogador, "altura", 32) / 2.0
            self.x = cx + self.raio_orbita * math.cos(self.angulo_orbita) - self.largura / 2.0
            self.y = cy + self.raio_orbita * math.sin(self.angulo_orbita) - self.altura / 2.0

    def get_rect(self) -> tuple[float, float, int, int]:
        """Retorna (x, y, largura, altura) para colisões AABB."""
        return (self.x, self.y, self.largura, self.altura)

    def desenhar(self, janela, camera=None):
        """Renderiza o drone e um indicador sutil de órbita."""
        if not self.ativo:
            return

        draw_x = camera.transform_x(self.x) if camera else self.x
        draw_y = camera.transform_y(self.y) if camera else self.y

        if draw_x < -40 or draw_x > janela.largura + 40 or draw_y < -40 or draw_y > janela.altura + 40:
            return

        sprite = self._carregar_sprite(self.sprite_key)
        if sprite is not None:
            janela.screen.blit(sprite, (int(draw_x), int(draw_y)))
        else:
            cor = AZUL_CIANO
            if "cura" in self.sprite_key:
                cor = VERDE_CURA
            elif "suporte" in self.sprite_key:
                cor = DOURADO
            pygame.draw.circle(
                janela.screen,
                cor,
                (int(draw_x + self.largura / 2.0), int(draw_y + self.altura / 2.0)),
                self.largura // 2
            )
