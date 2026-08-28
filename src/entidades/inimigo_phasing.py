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
        tempo_fase: float = 1.2
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
            sprite_key="inimigo_phasing"
        )
        self.tempo_ciclo = float(tempo_ciclo)
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
        """Renderiza o inimigo com transparência (alpha ~90) quando em fase."""
        if not self.vivo:
            return

        draw_x = camera.transform_x(self.x) if camera else self.x
        draw_y = camera.transform_y(self.y) if camera else self.y

        # Não desenha se estiver completamente fora da tela
        if draw_x < -45 or draw_x > janela.largura + 45 or draw_y < -45 or draw_y > janela.altura + 45:
            return

        sprite = self._obter_sprite(self.sprite_key)

        if self.em_fase:
            # Renderização translúcida em fase (alpha ~75) + anel etéreo ciano pulsante
            pulso = math.sin(self.timer_ciclo * 10.0) * 3.0
            # Renderização translúcida com aura ciano brilhante em fase (alpha ~90)
            if sprite is not None:
                sprite_fase = sprite.copy()
                sprite_fase.set_alpha(90)
                janela.screen.blit(sprite_fase, (int(draw_x), int(draw_y)))
                # Aura sutil ciano
                aura_surf = pygame.Surface((self.largura + 6, self.altura + 6), pygame.SRCALPHA)
                pygame.draw.rect(aura_surf, (0, 220, 255, 60), (0, 0, self.largura + 6, self.altura + 6), width=2, border_radius=4)
                janela.screen.blit(aura_surf, (int(draw_x - 3), int(draw_y - 3)))
            else:
                surf = pygame.Surface((self.largura, self.altura), pygame.SRCALPHA)
                surf.fill((0, 220, 255, 90))
                pygame.draw.rect(surf, (0, 255, 255, 160), (0, 0, self.largura, self.altura), width=2)
                janela.screen.blit(surf, (int(draw_x), int(draw_y)))
        else:
            # Renderização padrão opaca com suporte a flash de hit
            super().desenhar(janela, camera)
