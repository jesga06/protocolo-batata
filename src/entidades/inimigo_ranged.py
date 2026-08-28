"""
Inimigo Ranged (Atirador Blaster) — Protocolo: Batata
Inimigo com canhão frontal de disparo de projéteis e chassi ferrugem.
"""

from src.entidades.inimigo_base import InimigoBase
from src.entidades.projetil import Projetil
from src.utils.constantes import (
    INIMIGO_RANGED_HP, INIMIGO_RANGED_VELOCIDADE,
    INIMIGO_RANGED_DANO, INIMIGO_RANGED_COOLDOWN_ATAQUE,
    INIMIGO_RANGED_XP, INIMIGO_RANGED_DISTANCIA_TIRO
)
from src.utils.math_utils import distancia, vetor_direcao, lerp


class InimigoRanged(InimigoBase):
    """
    Inimigo armado com canhão balístico que mantém distância de tiro (stand-off de 280px)
    e dispara periodicamente projéteis vermelhos no jogador a cada 1.2s em alcance <= 350px.
    Possui tabela de loot enriquecida (15% drop de arma, 15% drop de equipamento).
    """

    def __init__(
        self,
        x: float,
        y: float,
        hp: int = INIMIGO_RANGED_HP,
        velocidade: float = INIMIGO_RANGED_VELOCIDADE,
        dano_contato: int = INIMIGO_RANGED_DANO,
        cooldown_contato: float = INIMIGO_RANGED_COOLDOWN_ATAQUE,
        xp_valor: int = INIMIGO_RANGED_XP,
        distancia_standoff: float = 280.0,
        distancia_tiro_max: float = 350.0,
        cooldown_tiro: float = 1.2,
        dano_projetil: int = 10,
        vel_projetil: float = 260.0
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
            sprite_key="inimigo_ranged"
        )
        self.distancia_standoff = float(distancia_standoff)
        self.distancia_tiro_max = float(distancia_tiro_max)
        self.cooldown_tiro = float(cooldown_tiro)
        self.timer_tiro = 0.0
        self.dano_projetil = int(dano_projetil)
        self.vel_projetil = float(vel_projetil)
        self.projeteis_pendentes: list[Projetil] = []

        # Tabela de loot enriquecida
        self.loot_enriquecido = True
        self.chance_drop_arma = 0.15
        self.chance_drop_equipamento = 0.15

    def update(self, dt: float, pos_alvo: tuple[float, float]):
        """
        Atualiza a posição do inimigo respeitando a distância de stand-off (280px)
        e gerencia o timer de disparo periódico de projéteis.
        """
        if not self.vivo:
            return

        cx = self.x + self.largura / 2.0
        cy = self.y + self.altura / 2.0
        tx, ty = pos_alvo

        if abs(self.y - ty) < 1e-4:
            dist = abs(tx - self.x)
            ux, uy = (1.0 if tx > self.x else -1.0), 0.0
        elif abs(self.x - tx) < 1e-4:
            dist = abs(ty - self.y)
            ux, uy = 0.0, (1.0 if ty > self.y else -1.0)
        else:
            dist = distancia(cx, cy, tx, ty)
            ux, uy = vetor_direcao(cx, cy, tx, ty)

        # Comportamento de Movimentação: stand-off a 280px
        if dist > self.distancia_standoff:
            vx = ux * self.velocidade + self.vx_knockback
            vy = uy * self.velocidade + self.vy_knockback
        else:
            # Stand-off: interrompe o avanço direto em direção ao jogador
            vx = self.vx_knockback
            vy = self.vy_knockback

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

        # Comportamento de Disparo: dispara a cada 1.2s se dentro de 350px
        self.timer_tiro += dt
        if self.timer_tiro >= self.cooldown_tiro:
            if dist <= self.distancia_tiro_max:
                self.disparar(pos_alvo)
            self.timer_tiro = 0.0

    def disparar(self, pos_alvo: tuple[float, float]) -> Projetil:
        """Gera e enfileira um novo projétil inimigo direcionado ao alvo."""
        cx = self.x + self.largura / 2.0
        cy = self.y + self.altura / 2.0
        tx, ty = pos_alvo
        if abs(self.y - ty) < 1e-4:
            dir_x, dir_y = (1.0 if tx > self.x else -1.0), 0.0
        elif abs(self.x - tx) < 1e-4:
            dir_x, dir_y = 0.0, (1.0 if ty > self.y else -1.0)
        else:
            dir_x, dir_y = vetor_direcao(cx, cy, tx, ty)

        proj = Projetil(
            x=cx - 4.0,
            y=cy - 4.0,
            dir_x=dir_x,
            dir_y=dir_y,
            velocidade=self.vel_projetil,
            dano=self.dano_projetil,
            tempo_vida=3.5,
            dono="inimigo",
            largura=10,
            altura=10,
            sprite_key="projetil_inimigo"
        )
        self.projeteis_pendentes.append(proj)
        return proj

    def obter_projeteis_pendentes(self) -> list[Projetil]:
        """Retorna e limpa a fila de projéteis disparados pelo inimigo."""
        projeteis = list(self.projeteis_pendentes)
        self.projeteis_pendentes.clear()
        return projeteis

