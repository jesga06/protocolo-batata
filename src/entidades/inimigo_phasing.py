import math
import pygame
from src.entidades.inimigo_base import InimigoBase
from src.utils.constantes import (
    INIMIGO_PHASING_HP, INIMIGO_PHASING_VELOCIDADE,
    INIMIGO_PHASING_DANO, INIMIGO_PHASING_COOLDOWN_ATAQUE,
    INIMIGO_PHASING_XP, INIMIGO_PHASING_CICLO
)


class InimigoPhasing(InimigoBase):
    """
    Inimigo etéreo que alterna ciclicamente entre o estado tangível e o estado em fase (Warranty Void).
    Ciclo de 3.0s: durante 1.2s entra em fase, tornando-se semi-transparente (alpha ~90) e
    completamente imune a todo tipo de dano, enquanto continua perseguindo a batata normalmente.
    """

    _alpha_cache = {}
    _aura_retangular_cache = {}
    _fallback_fase_cache = {}
    _flash_cache = {}

    def __init__(
        self,
        x: float,
        y: float,
        hp: int = INIMIGO_PHASING_HP,
        velocidade: float = INIMIGO_PHASING_VELOCIDADE,
        dano_contato: int = INIMIGO_PHASING_DANO,
        cooldown_contato: float = INIMIGO_PHASING_COOLDOWN_ATAQUE,
        xp_valor: int = INIMIGO_PHASING_XP,
        tempo_ciclo: float = INIMIGO_PHASING_CICLO,
        tempo_fase: float = 1.2,
        is_elite: bool = False,
        nome_elite: str = ""
    ):
        super().__init__(
            x=x,
            y=y,
            hp=hp,
            velocidade=velocidade,
            dano_contato=dano_contato,
            cooldown_contato=cooldown_contato,
            xp_valor=xp_valor,
            score_valor=200,
            largura=42,
            altura=42,
            sprite_key="inimigo_phasing",
            is_elite=is_elite,
            nome_elite=nome_elite
        )

        self.tempo_ciclo = max(0.01, float(tempo_ciclo))
        self.tempo_fase = float(tempo_fase)
        self.timer_ciclo = 0.0

    @property
    def em_fase(self) -> bool:
        """Retorna True se o inimigo está atualmente na janela de fase invulnerável (1.2s a cada 3.0s)."""
        return (self.timer_ciclo % self.tempo_ciclo) < self.tempo_fase

    def update(self, dt: float, pos_alvo: tuple[float, float]):
        """Atualiza a IA beeline normal e avança o temporizador de alternância de fase."""
        if not self.vivo:
            return

        self.timer_ciclo = (self.timer_ciclo + dt) % self.tempo_ciclo
        super().update(dt, pos_alvo)

    def receber_dano(self, quantidade: int, *args, **kwargs):
        """
        Aplica dano ao inimigo.
        Se estiver em fase (em_fase == True), o dano é completamente anulado e ignorado.
        """
        if not self.vivo:
            return

        if self.em_fase:
            # Imunidade absoluta: dano anulado e ignorado
            return

        super().receber_dano(quantidade)

    def desenhar(self, janela, camera=None):
        """Renderiza o inimigo com transparência (alpha ~90) quando em fase e suporte a low_graphics."""
        if not self.vivo:
            return

        draw_x = camera.transform_x(self.x) if camera else self.x
        draw_y = camera.transform_y(self.y) if camera else self.y

        # Não desenha se estiver completamente fora da tela
        largura_tela = getattr(janela, "largura", 800)
        altura_tela = getattr(janela, "altura", 600)
        limite_tela = max(80, self.largura, self.altura)
        if draw_x < -limite_tela or draw_x > largura_tela + limite_tela or draw_y < -limite_tela or draw_y > altura_tela + limite_tela:
            return

        screen = getattr(janela, "screen", janela)

        # Suporte a modo low_graphics (Config 2: retângulos e formas geométricas coloridas)
        if getattr(janela, "low_graphics", False):
            ix, iy = int(draw_x), int(draw_y)
            w, h = self.largura, self.altura
            cx, cy = ix + w // 2, iy + h // 2
            pts = [(cx, iy), (ix + w, cy), (cx, iy + h), (ix, cy)]

            if self.em_fase:
                # Na fase: contorno ciano/etéreo semi-transparente ou vazado
                cor_fase = (0, 220, 255) if self.flash_timer <= 0.0 else (255, 255, 255)
                pygame.draw.polygon(screen, cor_fase, pts, width=2)
            else:
                cor = (255, 255, 255) if self.flash_timer > 0.0 else self._obter_cor_low_graphics()
                pygame.draw.polygon(screen, cor, pts)
                pygame.draw.polygon(screen, (220, 180, 255), pts, width=2)

            if getattr(self, "is_elite", False):
                pygame.draw.rect(screen, (255, 215, 0), (ix - 2, iy - 2, w + 4, h + 4), width=2)
            return

        display_inited = pygame.display.get_init()

        if self.em_fase:
            # Renderiza aura pulsante roxa e dourada se for Elite/Mini-Boss
            if getattr(self, "is_elite", False) and display_inited:
                try:
                    ticks = pygame.time.get_ticks()
                    pulso_aura = math.sin(ticks / 150.0) * 4.0
                    raio_aura = max(self.largura, self.altura) / 2.0 + 8.0 + pulso_aura
                    centro_x = int(draw_x + self.largura / 2.0)
                    centro_y = int(draw_y + self.altura / 2.0)

                    dim_aura = max(10, int((raio_aura + 4.0) * 2))
                    if dim_aura not in self._aura_cache:
                        aura_surf = pygame.Surface((dim_aura, dim_aura), pygame.SRCALPHA)
                        aura_cx = dim_aura // 2
                        aura_cy = dim_aura // 2
                        pygame.draw.circle(aura_surf, (175, 75, 255, 90), (aura_cx, aura_cy), max(1, int(raio_aura)))
                        pygame.draw.circle(aura_surf, (255, 215, 0, 180), (aura_cx, aura_cy), max(1, int(raio_aura)), width=2)
                        self._aura_cache[dim_aura] = aura_surf
                    else:
                        aura_surf = self._aura_cache[dim_aura]

                    aura_cx = dim_aura // 2
                    aura_cy = dim_aura // 2
                    screen.blit(aura_surf, (centro_x - aura_cx, centro_y - aura_cy))
                except Exception:
                    pass

            sprite = self._obter_sprite(self.sprite_key)

            if sprite is not None:
                if (sprite.get_width(), sprite.get_height()) != (self.largura, self.altura):
                    cache_key = (self.sprite_key, self.largura, self.altura)
                    if cache_key not in self._sprite_cache:
                        self._sprite_cache[cache_key] = pygame.transform.scale(sprite, (self.largura, self.altura))
                    sprite = self._sprite_cache[cache_key]

                if display_inited:
                    alpha_key = (self.sprite_key, self.largura, self.altura, 90)
                    if alpha_key not in self._alpha_cache:
                        sprite_fase = sprite.copy()
                        sprite_fase.set_alpha(90)
                        self._alpha_cache[alpha_key] = sprite_fase
                    else:
                        sprite_fase = self._alpha_cache[alpha_key]

                    screen.blit(sprite_fase, (int(draw_x), int(draw_y)))

                    # Aura sutil ciano
                    aura_rect_key = (self.largura + 6, self.altura + 6)
                    if aura_rect_key not in self._aura_retangular_cache:
                        aura_surf = pygame.Surface(aura_rect_key, pygame.SRCALPHA)
                        pygame.draw.rect(aura_surf, (0, 220, 255, 60), (0, 0, aura_rect_key[0], aura_rect_key[1]), width=2, border_radius=4)
                        self._aura_retangular_cache[aura_rect_key] = aura_surf
                    else:
                        aura_surf = self._aura_retangular_cache[aura_rect_key]

                    screen.blit(aura_surf, (int(draw_x - 3), int(draw_y - 3)))
                else:
                    # Fallback sem display_init: desenha sem cachear
                    sprite_fase = sprite.copy()
                    sprite_fase.set_alpha(90)
                    screen.blit(sprite_fase, (int(draw_x), int(draw_y)))
            else:
                if display_inited:
                    fallback_key = (self.largura, self.altura)
                    if fallback_key not in self._fallback_fase_cache:
                        surf = pygame.Surface(fallback_key, pygame.SRCALPHA)
                        surf.fill((0, 220, 255, 90))
                        pygame.draw.rect(surf, (0, 255, 255, 160), (0, 0, self.largura, self.altura), width=2)
                        self._fallback_fase_cache[fallback_key] = surf
                    else:
                        surf = self._fallback_fase_cache[fallback_key]
                    screen.blit(surf, (int(draw_x), int(draw_y)))
                else:
                    surf = pygame.Surface((self.largura, self.altura), pygame.SRCALPHA)
                    surf.fill((0, 220, 255, 90))
                    pygame.draw.rect(surf, (0, 255, 255, 160), (0, 0, self.largura, self.altura), width=2)
                    screen.blit(surf, (int(draw_x), int(draw_y)))
        else:
            # Renderização padrão opaca com suporte a flash de hit cacheado
            if self.flash_timer > 0.0 and display_inited:
                sprite = self._obter_sprite(self.sprite_key)
                if sprite is not None:
                    if getattr(self, "is_elite", False):
                        cache_key = (self.sprite_key, self.largura, self.altura)
                        if cache_key not in self._sprite_cache:
                            self._sprite_cache[cache_key] = pygame.transform.scale(sprite, (self.largura, self.altura))
                        sprite = self._sprite_cache[cache_key]

                    flash_key = (self.sprite_key, self.largura, self.altura, "flash")
                    if flash_key not in self._flash_cache:
                        sprite_flash = sprite.copy()
                        sprite_flash.fill((255, 200, 200, 200), special_flags=pygame.BLEND_ADD)
                        self._flash_cache[flash_key] = sprite_flash
                    else:
                        sprite_flash = self._flash_cache[flash_key]

                    screen.blit(sprite_flash, (int(draw_x), int(draw_y)))
                    return

            super().desenhar(janela, camera)
