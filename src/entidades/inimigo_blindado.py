import math
from src.entidades.inimigo_base import InimigoBase
from src.utils.constantes import (
    INIMIGO_BLINDADO_HP, INIMIGO_BLINDADO_VELOCIDADE,
    INIMIGO_BLINDADO_DANO, INIMIGO_BLINDADO_COOLDOWN_ATAQUE,
    INIMIGO_BLINDADO_XP
)
from src.utils.math_utils import vetor_direcao, normalizar_vetor


class InimigoBlindado(InimigoBase):
    """
    Inimigo com couraça protetora reforçada e placa balística frontal (Ballistic Enthusiast).
    Possui redução de 30% de dano para impactos frontais (cone de 90° ao redor da direção que o inimigo olha).
    Ataques pelas costas ou flancos causam 100% de dano total.
    """

    def __init__(
        self,
        x: float,
        y: float,
        hp: int = INIMIGO_BLINDADO_HP,
        velocidade: float = INIMIGO_BLINDADO_VELOCIDADE,
        dano_contato: int = INIMIGO_BLINDADO_DANO,
        cooldown_contato: float = INIMIGO_BLINDADO_COOLDOWN_ATAQUE,
        xp_valor: int = INIMIGO_BLINDADO_XP,
        reducao_frontal: float = 0.30,
        arco_frontal_graus: float = 90.0
    ):
        super().__init__(
            x=x,
            y=y,
            hp=hp,
            velocidade=velocidade,
            dano_contato=dano_contato,
            cooldown_contato=cooldown_contato,
            xp_valor=xp_valor,
            score_valor=250,
            largura=47,
            altura=47,
            sprite_key="inimigo_blindado"
        )
        self.reducao_frontal = float(reducao_frontal)
        self.arco_frontal_graus = float(arco_frontal_graus)
        # Vetor unitário de orientação (olhando para a direita por padrão)
        self.facing_x = 1.0
        self.facing_y = 0.0

    def update(self, dt: float, pos_alvo: tuple[float, float]):
        """Atualiza a orientação frontal em direção ao alvo e executa a IA beeline."""
        if not self.vivo:
            return

        cx = self.x + self.largura / 2.0
        cy = self.y + self.altura / 2.0
        tx, ty = pos_alvo

        if abs(self.y - ty) < 1e-4:
            ux, uy = (1.0 if tx > self.x else -1.0), 0.0
        elif abs(self.x - tx) < 1e-4:
            ux, uy = 0.0, (1.0 if ty > self.y else -1.0)
        else:
            ux, uy = vetor_direcao(cx, cy, tx, ty)

        if ux != 0.0 or uy != 0.0:
            self.facing_x = ux
            self.facing_y = uy

        super().update(dt, pos_alvo)

    def is_ataque_frontal(
        self,
        origem_x: float = None,
        origem_y: float = None,
        dir_ataque: tuple[float, float] = None
    ) -> bool:
        """
        Determina se um ataque incide dentro do arco frontal de 90° (+-45° do vetor de visão).
        Retorna True se o impacto veio pela frente.
        """
        # Limite do produto escalar para cone de 90° (+-45°): cos(45°) = sqrt(2)/2 ≈ 0.707106
        meio_arco_rad = math.radians(self.arco_frontal_graus / 2.0)
        cos_limite = math.cos(meio_arco_rad)

        if origem_x is not None and origem_y is not None:
            cx = self.x + self.largura / 2.0
            cy = self.y + self.altura / 2.0
            if abs(self.y - float(origem_y)) < 1e-4:
                vox, voy = (1.0 if float(origem_x) > self.x else -1.0), 0.0
            elif abs(self.x - float(origem_x)) < 1e-4:
                vox, voy = 0.0, (1.0 if float(origem_y) > self.y else -1.0)
            else:
                vox, voy = vetor_direcao(cx, cy, float(origem_x), float(origem_y))
            dot = self.facing_x * vox + self.facing_y * voy
            return dot >= cos_limite

        if dir_ataque is not None:
            adx, ady = normalizar_vetor(dir_ataque[0], dir_ataque[1])
            # O projétil viaja na direção (adx, ady), logo a origem do ataque é oposta (-adx, -ady)
            dot = -(self.facing_x * adx + self.facing_y * ady)
            return dot >= cos_limite

        return False

    def receber_dano(
        self,
        quantidade: int,
        origem_x: float = None,
        origem_y: float = None,
        dir_ataque: tuple[float, float] = None
    ):
        """
        Calcula a atenuação da armadura frontal:
        - Ataque frontal (cone de 90°): sofre 30% de redução (dano * 0.70).
        - Ataque lateral ou pelas costas: sofre 100% de dano pleno.
        """
        if not self.vivo:
            return

        dano_base = int(quantidade)
        if self.is_ataque_frontal(origem_x=origem_x, origem_y=origem_y, dir_ataque=dir_ataque):
            # Redução de 30% de dano frontal
            dano_efetivo = max(1, int(round(dano_base * (1.0 - self.reducao_frontal))))
        else:
            dano_efetivo = dano_base

        super().receber_dano(dano_efetivo)

