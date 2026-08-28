"""
Entidade do Jogador (Batata) — Protocolo: Batata
Controla o avatar principal do jogo, movimento com normalização diagonal,
mira virtual, recebimento de dano, inventário de armas e renderização.
"""

import os
import pygame
from src.armas.melee import Melee
from src.armas.pistola import Pistola
from src.utils.constantes import (
    JOGADOR_HP_MAX_PADRAO, JOGADOR_VELOCIDADE_PADRAO,
    JOGADOR_LARGURA, JOGADOR_ALTURA, JOGADOR_COOLDOWN_DANO_FLASH,
    obter_caminho_asset, VERDE_CURA, VERMELHO_HP
)
from src.utils.math_utils import normalizar_vetor, clamp


class Jogador:
    """
    Representa o avatar da Batata controlada pelo jogador.
    """
    _sprite_idle = None
    _sprite_dano = None

    def __init__(
        self,
        x: float,
        y: float,
        hp_max: int = JOGADOR_HP_MAX_PADRAO,
        velocidade: float = JOGADOR_VELOCIDADE_PADRAO
    ):
        self.x = float(x)
        self.y = float(y)
        self.largura = int(JOGADOR_LARGURA)
        self.altura = int(JOGADOR_ALTURA)
        self.width = self.largura
        self.height = self.altura

        self.hp_max = int(hp_max)
        self.hp = int(hp_max)
        self.velocidade_base = float(velocidade)
        self.velocidade_atual = float(velocidade)

        self.vivo = True
        self.facing_right = True
        self.flash_dano_timer = 0.0
        self.invulnerabilidade_timer = 0.0

        # Inventário de armas inicial (Slot 1: Melee, Slot 2: Pistola, Slot 3: Especial)
        self.armas = [Melee(), Pistola()]
        self.arma_especial = None
        self.drone = None
        self.slot_ativo = 2  # Padrão: Slot 2 (Pistola)

    def selecionar_slot(self, slot: int):
        """Alterna a arma ativa para o slot 1, 2 ou 3."""
        if slot in (1, 2, 3):
            self.slot_ativo = slot

    def obter_arma_ativa(self):
        """Retorna a instância da arma correspondente ao slot_ativo atual."""
        if self.slot_ativo == 1:
            for arma in self.armas:
                if isinstance(arma, Melee) or getattr(arma, "slot", None) == 1:
                    return arma
            return self.armas[0] if self.armas else None
        elif self.slot_ativo == 2:
            for arma in self.armas:
                if isinstance(arma, Pistola) or getattr(arma, "slot", None) == 2:
                    return arma
            return self.armas[1] if len(self.armas) > 1 else (self.armas[0] if self.armas else None)
        elif self.slot_ativo == 3:
            return self.arma_especial
        return None

    @classmethod
    def _carregar_sprites(cls):
        if cls._sprite_idle is None:
            try:
                caminho_idle = obter_caminho_asset("jogador_idle")
                if os.path.isfile(caminho_idle):
                    cls._sprite_idle = pygame.image.load(caminho_idle).convert_alpha()
            except Exception:
                cls._sprite_idle = None

        if cls._sprite_dano is None:
            try:
                caminho_dano = obter_caminho_asset("jogador_dano")
                if os.path.isfile(caminho_dano):
                    cls._sprite_dano = pygame.image.load(caminho_dano).convert_alpha()
            except Exception:
                cls._sprite_dano = None

    def processar_input(
        self,
        teclado,
        mouse,
        dt: float,
        config_sistema=None,
        limite_arena: tuple[float, float] = (1600.0, 1200.0)
    ):
        """
        Processa teclas de movimento (WASD e Setas), seleção de armas (1, 2, 3),
        normaliza movimento diagonal e restringe o jogador aos limites da arena.
        """
        if not self.vivo:
            return

        dx = 0.0
        dy = 0.0

        if teclado is not None:
            # Troca de armas via teclas numéricas 1, 2 e 3
            if teclado.key_pressed("1"):
                self.selecionar_slot(1)
            elif teclado.key_pressed("2"):
                self.selecionar_slot(2)
            elif teclado.key_pressed("3"):
                self.selecionar_slot(3)

            # Movimento
            if teclado.key_pressed("a") or teclado.key_pressed("left") or teclado.key_pressed("LEFT"):
                dx -= 1.0
            if teclado.key_pressed("d") or teclado.key_pressed("right") or teclado.key_pressed("RIGHT"):
                dx += 1.0
            if teclado.key_pressed("w") or teclado.key_pressed("up") or teclado.key_pressed("UP"):
                dy -= 1.0
            if teclado.key_pressed("s") or teclado.key_pressed("down") or teclado.key_pressed("DOWN"):
                dy += 1.0

        # Normalização diagonal exata (dx, dy * 0.7071 ou vetor unitário)
        if dx != 0.0 and dy != 0.0:
            dx *= 0.70710678118
            dy *= 0.70710678118

        # Atualiza posição com velocidade por segundo
        self.x += dx * self.velocidade_atual * dt
        self.y += dy * self.velocidade_atual * dt

        # Boundary clamping estrito dentro dos limites da arena
        max_x = max(0.0, float(limite_arena[0]) - self.largura)
        max_y = max(0.0, float(limite_arena[1]) - self.altura)
        self.x = clamp(self.x, 0.0, max_x)
        self.y = clamp(self.y, 0.0, max_y)

        # Orientação visual (facing) baseado na posição virtual do mouse ou na direção
        if mouse is not None:
            try:
                mx, _ = mouse.get_position()
                # Se mouse estiver à esquerda do centro do jogador, vira para a esquerda
                if mx < self.x + self.largura / 2.0:
                    self.facing_right = False
                else:
                    self.facing_right = True
            except Exception:
                if dx < 0:
                    self.facing_right = False
                elif dx > 0:
                    self.facing_right = True
        else:
            if dx < 0:
                self.facing_right = False
            elif dx > 0:
                self.facing_right = True

    def receber_dano(self, quantidade: int):
        """Aplica dano ao jogador, aciona flash visual e testa condição de morte."""
        if not self.vivo:
            return

        self.hp = max(0, self.hp - int(quantidade))
        self.flash_dano_timer = JOGADOR_COOLDOWN_DANO_FLASH

        if self.hp <= 0:
            self.vivo = False
            try:
                from PPlay.sound import Sound
                sfx = Sound(obter_caminho_asset("sfx_morte_jogador"))
                sfx.play()
            except Exception:
                pass
        else:
            try:
                from PPlay.sound import Sound
                sfx = Sound(obter_caminho_asset("sfx_dano_jogador"))
                sfx.play()
            except Exception:
                pass

    def curar(self, quantidade: int):
        """Restaura HP do jogador até o teto de hp_max."""
        if not self.vivo:
            return
        self.hp = min(self.hp_max, self.hp + int(quantidade))

    def update(self, dt: float):
        """Atualiza timers de flash de dano e cooldowns das armas."""
        if self.flash_dano_timer > 0.0:
            self.flash_dano_timer = max(0.0, self.flash_dano_timer - dt)

        if self.invulnerabilidade_timer > 0.0:
            self.invulnerabilidade_timer = max(0.0, self.invulnerabilidade_timer - dt)

        for arma in self.armas:
            arma.update(dt)

        if self.arma_especial is not None:
            self.arma_especial.update(dt)

    def get_rect(self) -> tuple[float, float, int, int]:
        """Retorna caixa delimitadora (x, y, w, h)."""
        return (self.x, self.y, self.largura, self.altura)

    def desenhar(self, janela, camera=None):
        """Renderiza o avatar da batata com suporte a câmera e efeito de dano."""
        draw_x = camera.transform_x(self.x) if camera else self.x
        draw_y = camera.transform_y(self.y) if camera else self.y

        self._carregar_sprites()

        # Seleciona sprite apropriado (idle ou dano)
        sprite_base = self._sprite_dano if (self.flash_dano_timer > 0.0 and self._sprite_dano) else self._sprite_idle

        if sprite_base is not None:
            # Se virado para a esquerda, inverte horizontalmente
            surface_to_draw = sprite_base
            if not self.facing_right:
                surface_to_draw = pygame.transform.flip(sprite_base, True, False)
            janela.screen.blit(surface_to_draw, (int(draw_x), int(draw_y)))
        else:
            # Fallback visual
            cor = (255, 80, 80) if self.flash_dano_timer > 0.0 else (190, 150, 90)
            pygame.draw.rect(
                janela.screen,
                cor,
                (int(draw_x), int(draw_y), self.largura, self.altura),
                border_radius=8
            )
