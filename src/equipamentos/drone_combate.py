"""
Drone de Combate — Protocolo: Batata
Equipamento de Slot 4: orbita o jogador, rastreia o inimigo mais próximo em um raio de 350px e dispara a cada 1.0s (dano 8).
"""

from src.equipamentos.drone_base import DroneBase
from src.entidades.projetil import Projetil
from src.utils.math_utils import distancia, vetor_direcao
from src.utils.constantes import obter_caminho_asset
from src.utils.traducao import t


class DroneCombate(DroneBase):
    """
    Drone de suporte balístico com mira automática e disparos periódicos.
    """

    def __init__(
        self,
        tempo_vida: float = 30.0,
        cooldown_tiro: float = 1.0,
        dano: int = 8,
        alcance_deteccao: float = 350.0,
        velocidade_projetil: float = 480.0,
        raio_orbita: float = 48.0,
        velocidade_angular: float = 2.5
    ):
        super().__init__(
            nome=t("combate_entidades", "drone_combate"),
            icone_asset="drone_combate",
            sprite_key="drone_combate",
            tempo_vida=tempo_vida,
            raio_orbita=raio_orbita,
            velocidade_angular=velocidade_angular,
            hp=1
        )
        self.cooldown_tiro = float(cooldown_tiro)
        self.timer_tiro = 0.0
        self.dano = int(dano)
        self._dano_base = int(dano)
        self._cooldown_base = float(cooldown_tiro)
        self.alcance_deteccao = float(alcance_deteccao)
        self.velocidade_projetil = float(velocidade_projetil)
        self.alvo_atual = None

    def disparar_no_alvo(self, alvo, mult_dano: float = 1.0) -> list[Projetil]:
        """Gera um projétil apontado do centro do drone para o alvo com spawn centralizado."""
        from src.utils.math_utils import rotacionar_vetor

        d_cx = self.x + self.largura / 2.0
        d_cy = self.y + self.altura / 2.0
        a_cx = alvo.x + getattr(alvo, "largura", 28) / 2.0
        a_cy = alvo.y + getattr(alvo, "altura", 28) / 2.0

        dir_x, dir_y = vetor_direcao(d_cx, d_cy, a_cx, a_cy)
        if dir_x == 0.0 and dir_y == 0.0:
            dir_x = 1.0

        dano_final = max(1, int(round(self.dano * float(mult_dano))))
        d_largura = 8
        d_altura = 8
        proj = Projetil(
            x=d_cx - d_largura / 2.0,
            y=d_cy - d_altura / 2.0,
            dir_x=dir_x,
            dir_y=dir_y,
            velocidade=self.velocidade_projetil,
            dano=dano_final,
            tempo_vida=1.8,
            dono="jogador",
            largura=d_largura,
            altura=d_altura,
            sprite_key="projetil_pistola",
            knockback_forca=9.0
        )

        projeteis = [proj]
        mk = getattr(self, "nivel_mk", 1)
        if mk == 2:
            dx_extra, dy_extra = rotacionar_vetor(dir_x, dir_y, 0.10)
            proj_extra = Projetil(
                x=d_cx - d_largura / 2.0,
                y=d_cy - d_altura / 2.0,
                dir_x=dx_extra,
                dir_y=dy_extra,
                velocidade=self.velocidade_projetil,
                dano=dano_final,
                tempo_vida=1.8,
                dono="jogador",
                largura=d_largura,
                altura=d_altura,
                sprite_key="projetil_pistola",
                knockback_forca=9.0
            )
            projeteis.append(proj_extra)
        elif mk >= 3:
            for rad in (-0.10, 0.10):
                dx_extra, dy_extra = rotacionar_vetor(dir_x, dir_y, rad)
                proj_extra = Projetil(
                    x=d_cx - d_largura / 2.0,
                    y=d_cy - d_altura / 2.0,
                    dir_x=dx_extra,
                    dir_y=dy_extra,
                    velocidade=self.velocidade_projetil,
                    dano=dano_final,
                    tempo_vida=1.8,
                    dono="jogador",
                    largura=d_largura,
                    altura=d_altura,
                    sprite_key="projetil_pistola",
                    knockback_forca=9.0
                )
                projeteis.append(proj_extra)

        try:
            from PPlay.sound import Sound
            sfx = Sound(obter_caminho_asset("sfx_tiro_pistola"))
            sfx.play()
        except Exception:
            pass

        return projeteis

    def update(
        self,
        dt: float,
        jogador=None,
        inimigos: list = None,
        mult_dano: float = 1.0,
        mult_cadencia: float = 1.0,
        *args,
        **kwargs
    ) -> list[Projetil]:
        """
        Atualiza órbita e executa aquisição de alvos dentro de 350px para disparo.
        Pula inimigos em fase (getattr(e, 'em_fase', False)).
        Limita timer_tiro para não acumular tempo excessivo.
        Recebe e aplica modificadores mult_dano e mult_cadencia.
        Retorna lista de novos projéteis gerados.
        """
        super().update(dt, jogador=jogador, *args, **kwargs)
        if not self.ativo:
            return []

        # Extrai modificadores de kwargs ou do jogador se disponíveis
        m_dano = float(kwargs.get("mult_dano", mult_dano))
        m_cadencia = float(kwargs.get("mult_cadencia", mult_cadencia))

        if jogador is not None:
            if "mult_dano" not in kwargs and mult_dano == 1.0:
                m_dano *= getattr(jogador, "mult_dano_config", 1.0)
                if getattr(jogador, "buff_dano_timer", 0.0) > 0.0:
                    m_dano *= 1.05
            if "mult_cadencia" not in kwargs and mult_cadencia == 1.0:
                if getattr(jogador, "buff_cadencia_timer", 0.0) > 0.0:
                    m_cadencia *= 1.08

        # Atualiza timer_tiro acelerado por mult_cadencia
        self.timer_tiro += dt * max(0.01, m_cadencia)
        cooldown_efetivo = max(0.01, self.cooldown_tiro)
        # Limita timer_tiro para evitar acumular excesso (teto em 2 * cooldown)
        if self.timer_tiro > 2.0 * cooldown_efetivo:
            self.timer_tiro = 2.0 * cooldown_efetivo
        elif self.timer_tiro < 0.0:
            self.timer_tiro = 0.0

        if self.timer_tiro >= cooldown_efetivo:
            if inimigos:
                d_cx = self.x + self.largura / 2.0
                d_cy = self.y + self.altura / 2.0

                melhor_alvo = None
                menor_dist = self.alcance_deteccao

                for inimigo in inimigos:
                    if not getattr(inimigo, "vivo", True) or getattr(inimigo, "em_fase", False):
                        continue
                    e_cx = inimigo.x + getattr(inimigo, "largura", 28) / 2.0
                    e_cy = inimigo.y + getattr(inimigo, "altura", 28) / 2.0
                    dist = distancia(d_cx, d_cy, e_cx, e_cy)

                    if dist <= menor_dist:
                        menor_dist = dist
                        melhor_alvo = inimigo

                if melhor_alvo is not None:
                    self.alvo_atual = melhor_alvo
                    self.timer_tiro -= cooldown_efetivo
                    if self.timer_tiro < 0.0:
                        self.timer_tiro = 0.0
                    return self.disparar_no_alvo(melhor_alvo, mult_dano=m_dano)
                else:
                    self.alvo_atual = None
            else:
                self.alvo_atual = None
        elif inimigos:
            d_cx = self.x + self.largura / 2.0
            d_cy = self.y + self.altura / 2.0
            melhor_alvo = None
            menor_dist = self.alcance_deteccao
            for inimigo in inimigos:
                if not getattr(inimigo, "vivo", True) or getattr(inimigo, "em_fase", False):
                    continue
                e_cx = inimigo.x + getattr(inimigo, "largura", 28) / 2.0
                e_cy = inimigo.y + getattr(inimigo, "altura", 28) / 2.0
                dist = distancia(d_cx, d_cy, e_cx, e_cy)
                if dist <= menor_dist:
                    menor_dist = dist
                    melhor_alvo = inimigo
            self.alvo_atual = melhor_alvo
        else:
            self.alvo_atual = None

        return []
