"""
Inimigo Base — Protocolo: Batata
Classe base abstrata para todos os arquétipos de inimigos da arena.
Implementa IA beeline direta, controle de cooldown individual de dano de contato,
recebimento de dano, knockback e renderização.
"""

import os
import pygame
from src.utils.constantes import ASSETS_DIR, ASSET_PATHS, obter_caminho_asset, INIMIGO_PADRAO_HP
from src.utils.math_utils import vetor_direcao, colisao_aabb, lerp


class InimigoBase:
    """
    Classe base para inimigos.
    """
    _sprite_cache = {}

    def __init__(
        self,
        x: float,
        y: float,
        hp: int = INIMIGO_PADRAO_HP,
        velocidade: float = 100.0,
        dano_contato: int = 10,
        cooldown_contato: float = 0.4,
        xp_valor: int = 10,
        score_valor: int = 100,
        largura: int = 28,
        altura: int = 28,
        sprite_key: str = "inimigo_padrao"
    ):
        self.x = float(x)
        self.y = float(y)
        self.largura = int(largura)
        self.altura = int(altura)
        self.width = self.largura
        self.height = self.altura

        self.hp_max = int(hp)
        self.hp = int(hp)
        self.velocidade = float(velocidade)
        self.dano_contato = int(dano_contato)
        self.cooldown_contato_max = float(cooldown_contato)
        self.cooldown_contato_atual = 0.0  # Cooldown individual por instância

        self.xp_valor = int(xp_valor)
        self.score_valor = int(score_valor)
        self.vivo = True
        self.flash_timer = 0.0

        self.vx_knockback = 0.0
        self.vy_knockback = 0.0
        self.sprite_key = sprite_key

    @classmethod
    def _obter_sprite(cls, chave: str):
        if chave not in cls._sprite_cache:
            try:
                caminho = obter_caminho_asset(chave)
                if os.path.isfile(caminho):
                    cls._sprite_cache[chave] = pygame.image.load(caminho).convert_alpha()
                else:
                    cls._sprite_cache[chave] = None
            except Exception:
                cls._sprite_cache[chave] = None
        return cls._sprite_cache[chave]

    def update(self, dt: float, pos_alvo: tuple[float, float]):
        """
        Atualiza a posição do inimigo com IA beeline direta em direção a pos_alvo.
        Aplica decaimento de knockback e decrementa timers de cooldown e flash.
        """
        if not self.vivo:
            return

        cx = self.x + self.largura / 2.0
        cy = self.y + self.altura / 2.0
        tx, ty = pos_alvo

        # Cálculo do vetor unitário beeline
        ux, uy = vetor_direcao(cx, cy, tx, ty)

        # Atualiza posição combinando velocidade própria e knockback residual
        vx = ux * self.velocidade + self.vx_knockback
        vy = uy * self.velocidade + self.vy_knockback

        self.x += vx * dt
        self.y += vy * dt

        # Decaimento suave do knockback
        self.vx_knockback = lerp(self.vx_knockback, 0.0, min(1.0, 10.0 * dt))
        self.vy_knockback = lerp(self.vy_knockback, 0.0, min(1.0, 10.0 * dt))

        # Atualiza cooldown individual de contato
        if self.cooldown_contato_atual > 0.0:
            self.cooldown_contato_atual = max(0.0, self.cooldown_contato_atual - dt)

        # Atualiza flash visual de hit
        if self.flash_timer > 0.0:
            self.flash_timer = max(0.0, self.flash_timer - dt)

    def tentar_causar_dano_contato(self, jogador) -> bool:
        """
        Verifica sobreposição com o jogador e aplica dano se o cooldown individual estiver zerado.
        Retorna True se dano foi causado com sucesso neste frame.
        """
        if not self.vivo or not getattr(jogador, "vivo", True):
            return False

        if colisao_aabb(self.x, self.y, self.largura, self.altura,
                        jogador.x, jogador.y, jogador.largura, jogador.altura):
            if self.cooldown_contato_atual <= 0.0:
                jogador.receber_dano(self.dano_contato)
                self.cooldown_contato_atual = self.cooldown_contato_max
                return True
        return False

    def receber_dano(self, quantidade: int):
        """Reduz o HP do inimigo, aciona flash de hit e dispara destruição ao zerar."""
        if not self.vivo:
            return

        self.hp -= int(quantidade)
        self.flash_timer = 0.10

        if self.hp <= 0:
            self.vivo = False
            try:
                from PPlay.sound import Sound
                sfx = Sound(obter_caminho_asset("sfx_morte_inimigo"))
                sfx.play()
            except Exception:
                pass

    def aplicar_knockback(self, dir_x: float, dir_y: float, forca: float):
        """Aplica impulso de repulsão na direção especificada."""
        self.vx_knockback += dir_x * float(forca)
        self.vy_knockback += dir_y * float(forca)

    def get_rect(self) -> tuple[float, float, int, int]:
        return (self.x, self.y, self.largura, self.altura)

    def desenhar(self, janela, camera=None):
        """Renderiza o sprite do inimigo na tela virtual com suporte à câmera."""
        if not self.vivo:
            return

        draw_x = camera.transform_x(self.x) if camera else self.x
        draw_y = camera.transform_y(self.y) if camera else self.y

        # Não desenha se fora da tela
        if draw_x < -40 or draw_x > janela.largura + 40 or draw_y < -40 or draw_y > janela.altura + 40:
            return

        sprite = self._obter_sprite(self.sprite_key)
        if sprite is not None:
            if self.flash_timer > 0.0:
                # Efeito flash: desenha versão avermelhada/brilhante
                sprite_flash = sprite.copy()
                sprite_flash.fill((255, 200, 200, 200), special_flags=pygame.BLEND_ADD)
                janela.screen.blit(sprite_flash, (int(draw_x), int(draw_y)))
            else:
                janela.screen.blit(sprite, (int(draw_x), int(draw_y)))
        else:
            cor = (255, 255, 255) if self.flash_timer > 0.0 else (220, 50, 50)
            pygame.draw.rect(
                janela.screen,
                cor,
                (int(draw_x), int(draw_y), self.largura, self.altura)
            )
