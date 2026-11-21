"""
Entidade de Item Drop — Protocolo: Batata
Representa itens e gemas de XP dropados no chão da arena após a derrota de inimigos.
Possui tempo de vida de 60.0s e período de carência de 10.0s antes de habilitar coleta inimiga (Scavenger).
"""

import math
import pygame
from src.utils.constantes import (
    DROP_XP_VALOR_BASE, DROP_CURA_VALOR_BASE,
    DROP_TEMPO_DESAPARECER, DROP_TEMPO_SCAVENGER_ATIVAR,
    DROP_LARGURA, DROP_ALTURA,
    AMARELO_XP, VERDE_CURA, AZUL_CIANO, DOURADO, BRANCO, ROXO_ACENTO,
    ASSETS_DIR
)

MAPA_CORES_FALLBACK = {
    "xp": AMARELO_XP,
    "cura": VERDE_CURA,
    "arma": DOURADO,
    "equipamento": (255, 160, 50),
    "config": ROXO_ACENTO,
    "overclock": ROXO_ACENTO,
}


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
        self.tempo_despawn = 0.0

        self.ativo = True
        self.coletado = False
        self.alvo_scavenger = False  # Flag quando um inimigo scavenger está a caminho

    @property
    def tempo_no_chao(self) -> float:
        return self.tempo_decorrido

    @property
    def tempo_restante(self) -> float:
        return max(0.0, self.tempo_vida - self.tempo_despawn)

    def elegivel_scavenger(self) -> bool:
        """Retorna True se o item estiver no chão há pelo menos 10.0s e ainda estiver ativo."""
        return self.ativo and not self.coletado and (self.tempo_decorrido >= self.tempo_scavenger)

    def update(self, dt: float, pausar_despawn: bool = False):
        """Atualiza o tempo de vida do drop e desativa quando expira (a menos que o despawn esteja pausado)."""
        if not self.ativo or self.coletado:
            return

        self.tempo_decorrido += dt
        if not pausar_despawn:
            self.tempo_despawn += dt
            if self.tempo_despawn >= self.tempo_vida:
                self.ativo = False

    def get_rect(self) -> tuple[float, float, int, int]:
        return (self.x, self.y, self.largura, self.altura)

    _sprites: dict = {}
    _base_sprite_cache: dict = {}

    @classmethod
    def _obter_sprite(cls, tipo: str, largura: int, altura: int):
        if tipo not in cls._base_sprite_cache:
            import os
            mapa_arquivos = {
                "xp": "drop_xp.png",
                "cura": "drop_cura.png",
                "arma": "drop_arma.png",
                "equipamento": "drop_equipamento.png",
                "config": "drop_config.png",
                "overclock": "drop_config.png"
            }
            nome_arquivo = mapa_arquivos.get(tipo, "drop_xp.png")
            caminho = os.path.join(ASSETS_DIR, "sprites", "drops", nome_arquivo)
            if os.path.isfile(caminho):
                try:
                    cls._base_sprite_cache[tipo] = pygame.image.load(caminho).convert_alpha()
                except Exception:
                    cls._base_sprite_cache[tipo] = None
            else:
                cls._base_sprite_cache[tipo] = None

        base_img = cls._base_sprite_cache.get(tipo)
        if base_img is None:
            return None

        chave = (tipo, largura, altura)
        if chave not in cls._sprites:
            try:
                cls._sprites[chave] = pygame.transform.scale(base_img, (largura, altura))
            except Exception:
                cls._sprites[chave] = None
        return cls._sprites[chave]

    def desenhar(self, janela, camera=None, pausar_despawn: bool = False):
        """Renderiza o item utilizando seu sprite PNG autêntico com pulso sutil e efeito de piscar ao expirar."""
        if not self.ativo or self.coletado:
            return

        # Efeito de piscar quando restam menos de 4.0s (desativado se despawn pausado)
        if not pausar_despawn and self.tempo_restante < 4.0:
            if int(self.tempo_decorrido * 8) % 2 == 0:
                return

        draw_x = camera.transform_x(self.x) if camera else self.x
        draw_y = camera.transform_y(self.y) if camera else self.y

        # Culling fora da tela / câmera
        largura_tela = getattr(janela, "largura", 800)
        altura_tela = getattr(janela, "altura", 600)
        margem = 64
        if draw_x < -margem or draw_x > largura_tela + margem or draw_y < -margem or draw_y > altura_tela + margem:
            return

        screen = getattr(janela, "screen", janela)

        cx = int(draw_x + self.largura / 2.0)
        cy = int(draw_y + self.altura / 2.0)

        # Pulso sutil de tamanho
        pulso = int(math.sin(self.tempo_decorrido * 5.0) * 2.0)
        largura_render = max(8, self.largura + pulso)
        altura_render = max(8, self.altura + pulso)

        cor_fallback = MAPA_CORES_FALLBACK.get(self.tipo, AMARELO_XP)

        # Suporte a modo low_graphics (Config 2: retângulos e formas geométricas coloridas)
        if getattr(janela, "low_graphics", False):
            tam = largura_render
            rect_x = cx - tam // 2
            rect_y = cy - tam // 2
            if self.tipo == "xp":
                pts = [(cx, rect_y), (cx + tam // 2, cy), (cx, rect_y + tam), (cx - tam // 2, cy)]
                pygame.draw.polygon(screen, cor_fallback, pts)
            elif self.tipo == "cura":
                w_bar = max(2, tam // 3)
                pygame.draw.rect(screen, cor_fallback, (cx - w_bar // 2, rect_y, w_bar, tam))
                pygame.draw.rect(screen, cor_fallback, (rect_x, cy - w_bar // 2, tam, w_bar))
            else:
                pygame.draw.rect(screen, cor_fallback, (rect_x, rect_y, tam, tam))
                pygame.draw.rect(screen, BRANCO, (rect_x, rect_y, tam, tam), width=1)
            return

        sprite = self._obter_sprite(self.tipo, largura_render, altura_render)
        if sprite is not None:
            rect_x = cx - largura_render // 2
            rect_y = cy - altura_render // 2
            screen.blit(sprite, (rect_x, rect_y))
        else:
            # Fallback seguro
            tam = largura_render
            rect_x = cx - tam // 2
            rect_y = cy - tam // 2
            pygame.draw.rect(screen, cor_fallback, (rect_x, rect_y, tam, tam), border_radius=4)
