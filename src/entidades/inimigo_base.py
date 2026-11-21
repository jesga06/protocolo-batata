"""
Inimigo Base — Protocolo: Batata
Classe base abstrata para todos os arquétipos de inimigos da arena.
Implementa IA beeline direta, controle de cooldown individual de dano de contato,
recebimento de dano, knockback e renderização.
"""

import os
import math
import pygame
from src.utils.constantes import ASSETS_DIR, ASSET_PATHS, obter_caminho_asset, INIMIGO_PADRAO_HP
from src.utils.math_utils import vetor_direcao, colisao_aabb, lerp


class InimigoBase:
    """
    Classe base para inimigos.
    """
    _sprite_cache = {}
    _aura_cache = {}
    _flash_cache = {}

    def __init__(
        self,
        x: float,
        y: float,
        hp: int = INIMIGO_PADRAO_HP,
        velocidade: float = 100.0,
        dano_contato: int = 10,
        cooldown_contato: float = 0.4,
        xp_valor: int = 5,
        score_valor: int = 100,
        largura: int = 28,
        altura: int = 28,
        sprite_key: str = "inimigo_padrao",
        is_elite: bool = False,
        nome_elite: str = ""
    ):
        self.x = float(x)
        self.y = float(y)
        self.is_elite = bool(is_elite)
        self.nome_elite = str(nome_elite)

        if self.is_elite:
            self.largura = int(largura * 2)
            self.altura = int(altura * 2)
            self.hp_max = int(hp * 3)
            self.hp = self.hp_max
            self.score_valor = int(score_valor * 10)
            self.xp_valor = 50
            self.tempo_vida_restante = 60.0
            self.thermal_overload_timer = 60.0
            self.tempo_vida_elite = 60.0
            self.superaqueceu = False
        else:
            self.largura = int(largura)
            self.altura = int(altura)
            self.hp_max = int(hp)
            self.hp = int(hp)
            self.score_valor = int(score_valor)
            self.xp_valor = int(xp_valor)
            self.tempo_vida_restante = None
            self.thermal_overload_timer = None
            self.tempo_vida_elite = None
            self.superaqueceu = False

        self.width = self.largura
        self.height = self.altura

        self.velocidade = float(velocidade)
        self.dano_contato = int(dano_contato)
        self.cooldown_contato_max = float(cooldown_contato)
        self.cooldown_contato_atual = 0.0  # Cooldown individual por instância
        self.cooldown_ram_atual = 0.0
        self.slow_timer = 0.0
        self.slow_fator = 1.0
        self.vivo = True
        self.flash_timer = 0.0

        self.vx_knockback = 0.0
        self.vy_knockback = 0.0
        self.sprite_key = sprite_key


    @classmethod
    def _obter_sprite(cls, chave):
        if chave not in cls._sprite_cache:
            if isinstance(chave, tuple):
                chave_base, w, h = chave
                base_sprite = cls._obter_sprite(chave_base)
                if base_sprite is not None:
                    try:
                        cls._sprite_cache[chave] = pygame.transform.scale(base_sprite, (int(w), int(h)))
                    except Exception:
                        cls._sprite_cache[chave] = None
                else:
                    cls._sprite_cache[chave] = None
            else:
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
        tx, ty = getattr(self, "pos_alvo_override", None) or pos_alvo

        # Cálculo do vetor unitário beeline a partir do centro real
        ux, uy = vetor_direcao(cx, cy, tx, ty)

        # Atualiza posição combinando velocidade própria (respeitando slow_timer) e knockback residual
        vel_efetiva = self.velocidade * (self.slow_fator if getattr(self, "slow_timer", 0.0) > 0.0 else 1.0)
        vx = ux * vel_efetiva + self.vx_knockback
        vy = uy * vel_efetiva + self.vy_knockback

        self.x += vx * dt
        self.y += vy * dt

        # Decrementa timer de superaquecimento para Mini-Bosses / Elites (60s)
        if self.is_elite and self.tempo_vida_restante is not None:
            self.tempo_vida_restante -= dt
            self.thermal_overload_timer = self.tempo_vida_restante
            self.tempo_vida_elite = self.tempo_vida_restante
            if self.tempo_vida_restante <= 0.0:
                self.tempo_vida_restante = 0.0
                self.thermal_overload_timer = 0.0
                self.tempo_vida_elite = 0.0
                self.superaqueceu = True
                self.vivo = False
                self.xp_valor = 0
                return

        # Decaimento suave do knockback
        self.vx_knockback = lerp(self.vx_knockback, 0.0, min(1.0, 10.0 * dt))
        self.vy_knockback = lerp(self.vy_knockback, 0.0, min(1.0, 10.0 * dt))

        # Atualiza cooldown individual de contato
        if self.cooldown_contato_atual > 0.0:
            self.cooldown_contato_atual = max(0.0, self.cooldown_contato_atual - dt)

        # Decrementa slow_timer e cooldown_ram_atual
        if self.slow_timer > 0.0:
            self.slow_timer = max(0.0, self.slow_timer - dt)
            if self.slow_timer <= 0.0:
                self.slow_fator = 1.0
        if self.cooldown_ram_atual > 0.0:
            self.cooldown_ram_atual = max(0.0, self.cooldown_ram_atual - dt)

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

    def receber_dano(self, quantidade: int, *args, **kwargs) -> int:
        """Reduz o HP do inimigo, aciona flash de hit, dispara destruição ao zerar e retorna o dano efetivo aplicado."""
        if not self.vivo or int(quantidade) <= 0:
            return 0

        dano_aplicado = int(quantidade)
        self.hp -= dano_aplicado
        self.flash_timer = 0.10

        if self.hp <= 0:
            self.vivo = False
            try:
                from PPlay.sound import Sound
                sfx = Sound(obter_caminho_asset("sfx_morte_inimigo"))
                sfx.play()
            except Exception:
                pass
        return dano_aplicado

    def aplicar_knockback(self, dir_x: float, dir_y: float, forca: float):
        """Aplica impulso de repulsão na direção especificada."""
        self.vx_knockback += dir_x * float(forca)
        self.vy_knockback += dir_y * float(forca)

    def get_rect(self) -> tuple[float, float, int, int]:
        return (self.x, self.y, self.largura, self.altura)

    def _obter_cor_low_graphics(self) -> tuple[int, int, int]:
        if "rapido" in self.sprite_key:
            return (255, 180, 20)
        elif "tank" in self.sprite_key:
            return (140, 30, 40)
        elif "ranged" in self.sprite_key:
            return (40, 200, 180)
        elif "blindado" in self.sprite_key:
            return (80, 110, 150)
        elif "phasing" in self.sprite_key:
            return (180, 70, 220)
        elif "boss" in self.sprite_key:
            return (50, 140, 240)
        return (220, 50, 50)

    def desenhar(self, janela, camera=None):
        """Renderiza o sprite do inimigo na tela virtual com suporte à câmera e modo low_graphics."""
        if not self.vivo:
            return

        draw_x = camera.transform_x(self.x) if camera else self.x
        draw_y = camera.transform_y(self.y) if camera else self.y

        # Não desenha se fora da tela (margem dinâmica baseada no tamanho da entidade)
        largura_tela = getattr(janela, "largura", 800)
        altura_tela = getattr(janela, "altura", 600)
        margem = max(80, self.largura, self.altura)
        if draw_x < -margem or draw_x > largura_tela + margem or draw_y < -margem or draw_y > altura_tela + margem:
            return

        screen = getattr(janela, "screen", janela)

        # Suporte a modo low_graphics (Config 2: retângulos e formas geométricas coloridas)
        if getattr(janela, "low_graphics", False):
            cor = (255, 255, 255) if self.flash_timer > 0.0 else self._obter_cor_low_graphics()
            ix, iy = int(draw_x), int(draw_y)
            w, h = self.largura, self.altura
            cx, cy = ix + w // 2, iy + h // 2

            if "rapido" in self.sprite_key:
                pts = [(cx, iy), (ix + w, iy + h), (ix, iy + h)]
                pygame.draw.polygon(screen, cor, pts)
                pygame.draw.polygon(screen, (0, 0, 0), pts, width=1)
            elif "ranged" in self.sprite_key:
                pts = [(cx, iy), (ix + w, cy), (cx, iy + h), (ix, cy)]
                pygame.draw.polygon(screen, cor, pts)
                pygame.draw.polygon(screen, (0, 0, 0), pts, width=1)
            elif "tank" in self.sprite_key:
                c = max(4, w // 4)
                pts = [
                    (ix + c, iy), (ix + w - c, iy),
                    (ix + w, iy + c), (ix + w, iy + h - c),
                    (ix + w - c, iy + h), (ix + c, iy + h),
                    (ix, iy + h - c), (ix, iy + c)
                ]
                pygame.draw.polygon(screen, cor, pts)
                pygame.draw.polygon(screen, (0, 0, 0), pts, width=2)
            elif "blindado" in self.sprite_key:
                pygame.draw.rect(screen, cor, (ix, iy, w, h))
                pygame.draw.rect(screen, (200, 220, 240), (ix, iy, w, h), width=3)
            elif "phasing" in self.sprite_key:
                pts = [(cx, iy), (ix + w, cy), (cx, iy + h), (ix, cy)]
                pygame.draw.polygon(screen, cor, pts)
                pygame.draw.polygon(screen, (220, 180, 255), pts, width=2)
            else:
                pygame.draw.rect(screen, cor, (ix, iy, w, h))
                pygame.draw.rect(screen, (0, 0, 0), (ix, iy, w, h), width=1)

            if getattr(self, "is_elite", False):
                pygame.draw.rect(screen, (255, 215, 0), (ix - 2, iy - 2, w + 4, h + 4), width=2)
            return

        # Renderiza aura pulsante roxa e dourada se for Elite/Mini-Boss
        display_inited = pygame.display.get_init()
        if getattr(self, "is_elite", False):
            try:
                ticks = pygame.time.get_ticks() if display_inited else 0
                pulso = math.sin(ticks / 150.0) * 4.0
                raio_aura = max(self.largura, self.altura) / 2.0 + 8.0 + pulso
                centro_x = int(draw_x + self.largura / 2.0)
                centro_y = int(draw_y + self.altura / 2.0)

                dim_aura = max(10, int((raio_aura + 4.0) * 2))
                if display_inited and dim_aura in self._aura_cache:
                    aura_surf = self._aura_cache[dim_aura]
                else:
                    aura_surf = pygame.Surface((dim_aura, dim_aura), pygame.SRCALPHA)
                    aura_cx = dim_aura // 2
                    aura_cy = dim_aura // 2
                    raio_desenho = max(1, int(raio_aura))
                    pygame.draw.circle(aura_surf, (175, 75, 255, 90), (aura_cx, aura_cy), raio_desenho)
                    pygame.draw.circle(aura_surf, (255, 215, 0, 180), (aura_cx, aura_cy), raio_desenho, width=2)
                    if display_inited:
                        self._aura_cache[dim_aura] = aura_surf

                aura_cx = dim_aura // 2
                aura_cy = dim_aura // 2
                screen.blit(aura_surf, (centro_x - aura_cx, centro_y - aura_cy))
            except Exception:
                pass

        sprite = self._obter_sprite(self.sprite_key)
        if sprite is not None:
            if getattr(self, "is_elite", False):
                cache_key = (self.sprite_key, self.largura, self.altura)
                if cache_key not in self._sprite_cache:
                    self._sprite_cache[cache_key] = pygame.transform.scale(sprite, (self.largura, self.altura))
                sprite = self._sprite_cache[cache_key]
            sw, sh = sprite.get_width(), sprite.get_height()
            blit_x = int(draw_x + (self.largura - sw) // 2)
            blit_y = int(draw_y + (self.altura - sh) // 2)
            if self.flash_timer > 0.0:
                flash_key = (id(sprite), sw, sh)
                if display_inited and flash_key in self._flash_cache:
                    sprite_flash = self._flash_cache[flash_key]
                else:
                    sprite_flash = sprite.copy()
                    sprite_flash.fill((255, 200, 200, 200), special_flags=pygame.BLEND_ADD)
                    if display_inited:
                        self._flash_cache[flash_key] = sprite_flash
                screen.blit(sprite_flash, (blit_x, blit_y))
            else:
                screen.blit(sprite, (blit_x, blit_y))
        else:
            cor = (255, 255, 255) if self.flash_timer > 0.0 else (220, 50, 50)
            pygame.draw.rect(
                screen,
                cor,
                (int(draw_x), int(draw_y), self.largura, self.altura)
            )

