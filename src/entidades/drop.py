"""
Entidade de Item Drop — Protocolo: Batata
Representa itens e gemas de XP dropados no chão da arena após a derrota de inimigos.
Possui tempo de vida de 10.0s e período de carência de 1.0s antes de habilitar coleta inimiga (Scavenger).
"""

import math
import pygame
from src.utils.constantes import (
    DROP_XP_VALOR_BASE, DROP_CURA_VALOR_BASE,
    DROP_TEMPO_DESAPARECER, DROP_TEMPO_SCAVENGER_ATIVAR,
    DROP_LARGURA, DROP_ALTURA,
    AMARELO_XP, VERDE_CURA, AZUL_CIANO, DOURADO, BRANCO
)


class ItemDrop:
    """
    Representa uma entidade de drop coletável na arena.
    """

    def __init__(
        self,
        x: float,
        y: float,
        tipo: str = "xp",
        valor: int = DROP_XP_VALOR_BASE,
        tempo_vida: float = DROP_TEMPO_DESAPARECER,
        tempo_scavenger: float = DROP_TEMPO_SCAVENGER_ATIVAR,
        largura: int = DROP_LARGURA,
        altura: int = DROP_ALTURA
    ):
        self.x = float(x)
        self.y = float(y)
        self.largura = int(largura)
        self.altura = int(altura)
        self.width = self.largura
        self.height = self.altura

        self.tipo = str(tipo)  # "xp", "cura", "arma"
        self.valor = int(valor)
        self.tempo_vida = float(tempo_vida)
        self.tempo_scavenger = float(tempo_scavenger)
        self.tempo_decorrido = 0.0

        self.ativo = True
        self.coletado = False
        self.alvo_scavenger = False  # Flag quando um inimigo scavenger está a caminho

    @property
    def tempo_restante(self) -> float:
        return max(0.0, self.tempo_vida - self.tempo_decorrido)

    def elegivel_scavenger(self) -> bool:
        """Retorna True se o item estiver no chão há pelo menos 1s e ainda estiver ativo."""
        return self.ativo and not self.coletado and (self.tempo_decorrido >= self.tempo_scavenger)

    def update(self, dt: float):
        """Atualiza o tempo de vida do drop e desativa quando expira."""
        if not self.ativo or self.coletado:
            return

        self.tempo_decorrido += dt
        if self.tempo_decorrido >= self.tempo_vida:
            self.ativo = False

    def get_rect(self) -> tuple[float, float, int, int]:
        return (self.x, self.y, self.largura, self.altura)

    def desenhar(self, janela, camera=None):
        """Renderiza o item com efeitos visuais e piscamento nos últimos segundos."""
        if not self.ativo or self.coletado:
            return

        # Efeito de piscar quando restam menos de 2.5s
        if self.tempo_restante < 2.5:
            # Pisca a cada 120ms
            if int(self.tempo_decorrido * 8) % 2 == 0:
                return

        draw_x = camera.transform_x(self.x) if camera else self.x
        draw_y = camera.transform_y(self.y) if camera else self.y
        screen = janela.screen

        cx = int(draw_x + self.largura / 2.0)
        cy = int(draw_y + self.altura / 2.0)

        # Pulso sutil de tamanho/brilho
        pulso = math.sin(self.tempo_decorrido * 6.0) * 1.5

        if self.tipo == "xp":
            # Gema em forma de losango brilhante grande (raio 16px)
            r = int(16 + pulso)
            pontos = [
                (cx, cy - r),
                (cx + r, cy),
                (cx, cy + r),
                (cx - r, cy)
            ]
            cor_corpo = AMARELO_XP if self.valor <= 15 else AZUL_CIANO
            pygame.draw.polygon(screen, cor_corpo, pontos)
            pygame.draw.polygon(screen, BRANCO, pontos, width=2)
            # Brilho central
            pygame.draw.circle(screen, BRANCO, (cx, cy), max(2, int(5 + pulso * 0.5)))

        elif self.tipo == "cura":
            # Caixa médica com cruz (32x32px)
            tam = int(32 + pulso)
            rect_x = cx - tam // 2
            rect_y = cy - tam // 2
            pygame.draw.rect(screen, (30, 140, 50), (rect_x, rect_y, tam, tam), border_radius=6)
            pygame.draw.rect(screen, (220, 255, 220), (rect_x, rect_y, tam, tam), width=2, border_radius=6)
            # Cruz branca
            pygame.draw.rect(screen, BRANCO, (cx - 3, cy - 10, 6, 20))
            pygame.draw.rect(screen, BRANCO, (cx - 10, cy - 3, 20, 6))

        elif self.tipo == "arma":
            # Caixa de arma dourada (34x34px)
            tam = int(34 + pulso)
            rect_x = cx - tam // 2
            rect_y = cy - tam // 2
            pygame.draw.rect(screen, (70, 50, 20), (rect_x, rect_y, tam, tam), border_radius=6)
            pygame.draw.rect(screen, DOURADO, (rect_x, rect_y, tam, tam), width=3, border_radius=6)
            pygame.draw.circle(screen, DOURADO, (cx, cy), 6)

        elif self.tipo == "equipamento":
            # Caixa de equipamento laranja (34x34px)
            tam = int(34 + pulso)
            rect_x = cx - tam // 2
            rect_y = cy - tam // 2
            pygame.draw.rect(screen, (75, 40, 15), (rect_x, rect_y, tam, tam), border_radius=6)
            pygame.draw.rect(screen, (255, 140, 0), (rect_x, rect_y, tam, tam), width=3, border_radius=6)
            pygame.draw.circle(screen, (255, 180, 50), (cx, cy), 6)
