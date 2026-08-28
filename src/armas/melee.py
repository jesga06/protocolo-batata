"""
Ataque Melee (Chave de Manutenção) — Protocolo: Batata
Arma de Slot 1 permanente do jogador com dano em arco curto e repulsão (knockback).
"""

from src.armas.arma_base import ArmaBase
from src.utils.math_utils import distancia, vetor_direcao
from src.utils.constantes import (
    MELEE_DANO, MELEE_COOLDOWN, MELEE_ALCANCE,
    MELEE_KNOCKBACK, MELEE_ALVOS_MAX, obter_caminho_asset
)


class Melee(ArmaBase):
    """
    Ataque corpo-a-corpo de curto alcance com dano em área e repulsão nos alvos mais próximos.
    """

    def __init__(
        self,
        dano: int = 20,
        cooldown: float = 0.6,
        alcance: float = 140.0,
        knockback_forca: float = 180.0,
        max_alvos_knockback: int = 2
    ):
        super().__init__(
            nome="Chave de Manutenção",
            dano=dano,
            cooldown=cooldown,
            municao_infinita=True,
            slot=1,
            icone_asset="arma_melee"
        )
        self.alcance = float(alcance)
        self.knockback_forca = float(knockback_forca)
        self.max_alvos_knockback = int(max_alvos_knockback)

    def disparar(self, origem_x: float, origem_y: float, destino_x: float, destino_y: float) -> list:
        """Melee não dispara projéteis balísticos convencionais."""
        return []

    def executar_ataque(self, origem_x: float, origem_y: float, lista_inimigos: list) -> list:
        """
        Executa o golpe corpo-a-corpo: causa dano a todos os inimigos no raio de alcance
        e aplica knockback aos 2 mais próximos.
        Retorna a lista de inimigos atingidos.
        """
        if not self.pode_atirar():
            return []

        self.tempo_recarga_restante = self.cooldown

        # Efeito sonoro do golpe (sempre que desfere o ataque)
        try:
            from PPlay.sound import Sound
            sfx_path = obter_caminho_asset("sfx_ataque_melee")
            sfx = Sound(sfx_path)
            sfx.play()
        except Exception:
            pass

        atingidos = []
        for inimigo in lista_inimigos:
            if not getattr(inimigo, "vivo", True):
                continue

            centro_e_x = inimigo.x + getattr(inimigo, "largura", 28) / 2.0
            centro_e_y = inimigo.y + getattr(inimigo, "altura", 28) / 2.0
            dist = distancia(origem_x, origem_y, centro_e_x, centro_e_y)

            if dist <= self.alcance:
                atingidos.append((inimigo, dist, centro_e_x, centro_e_y))

        if not atingidos:
            return []

        # Ordena do mais próximo para o mais distante
        atingidos.sort(key=lambda item: item[1])

        # Aplica dano a todos os atingidos no raio
        inimigos_afetados = []
        for idx, (inimigo, dist, cx, cy) in enumerate(atingidos):
            inimigo.receber_dano(self.dano)
            inimigos_afetados.append(inimigo)

            # Aplica knockback aos N alvos mais próximos
            if idx < self.max_alvos_knockback:
                dir_x, dir_y = vetor_direcao(origem_x, origem_y, cx, cy)
                if dir_x == 0.0 and dir_y == 0.0:
                    dir_x = 1.0
                if hasattr(inimigo, "aplicar_knockback"):
                    inimigo.aplicar_knockback(dir_x, dir_y, self.knockback_forca)

        return inimigos_afetados
