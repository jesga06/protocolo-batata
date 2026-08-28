"""
Sistema de Drops — Protocolo: Batata
Gerencia a criação de drops na arena após a morte de inimigos, tabela de probabilidades,
atualização de ciclo de vida e coleta por contato do jogador.
"""

import random
from src.entidades.drop import ItemDrop
from src.utils.math_utils import colisao_aabb
from src.utils.constantes import (
    DROP_XP_VALOR_BASE, DROP_CURA_VALOR_BASE,
    DROP_TEMPO_DESAPARECER, DROP_TEMPO_SCAVENGER_ATIVAR,
    obter_caminho_asset
)


class SistemaDrops:
    """
    Gerenciador de drops e itens no chão da arena.
    """

    def __init__(self):
        self.drops: list[ItemDrop] = []

    def gerar_drop_morte_inimigo(
        self,
        x: float,
        y: float,
        tipo_inimigo: str = "padrao",
        bonus_chance_drop: float = 0.0,
        mult_chance_drop: float = 1.0,
        xp_base: int = None,
        loot_enriquecido: bool = False
    ) -> list[ItemDrop]:
        """
        Gera os drops ao eliminar um inimigo:
        - Sempre gera ao menos 1 gema de XP.
        - Calcula probabilidades para caixas de cura ou caixas de armas especiais.
        """
        novos_drops = []

        # 1. Gema de XP
        valor_xp = int(xp_base) if xp_base is not None else DROP_XP_VALOR_BASE
        gema_xp = ItemDrop(
            x=x - 8.0,
            y=y - 8.0,
            tipo="xp",
            valor=valor_xp,
            tempo_vida=DROP_TEMPO_DESAPARECER,
            tempo_scavenger=DROP_TEMPO_SCAVENGER_ATIVAR
        )
        novos_drops.append(gema_xp)
        self.drops.append(gema_xp)

        # 2. Chance de Drop de Cura
        chance_cura_base = 0.08
        chance_cura_efetiva = min(1.0, (chance_cura_base + bonus_chance_drop) * mult_chance_drop)
        if random.random() < chance_cura_efetiva:
            offset_x = random.uniform(-16.0, 16.0)
            offset_y = random.uniform(-16.0, 16.0)
            drop_cura = ItemDrop(
                x=x + offset_x - 8.0,
                y=y + offset_y - 8.0,
                tipo="cura",
                valor=DROP_CURA_VALOR_BASE,
                tempo_vida=DROP_TEMPO_DESAPARECER,
                tempo_scavenger=DROP_TEMPO_SCAVENGER_ATIVAR
            )
            novos_drops.append(drop_cura)
            self.drops.append(drop_cura)

        # 3. Chance de Drop de Arma / Caixa Especial
        chance_arma_base = 0.15 if loot_enriquecido else 0.04
        chance_arma_efetiva = min(1.0, (chance_arma_base + bonus_chance_drop) * mult_chance_drop)
        if random.random() < chance_arma_efetiva:
            offset_x = random.uniform(-16.0, 16.0)
            offset_y = random.uniform(-16.0, 16.0)
            drop_arma = ItemDrop(
                x=x + offset_x - 8.0,
                y=y + offset_y - 8.0,
                tipo="arma",
                valor=1,
                tempo_vida=DROP_TEMPO_DESAPARECER,
                tempo_scavenger=DROP_TEMPO_SCAVENGER_ATIVAR
            )
            novos_drops.append(drop_arma)
            self.drops.append(drop_arma)

        return novos_drops

    def update(self, dt: float):
        """Atualiza timers de todos os drops e remove expirados."""
        for drop in self.drops:
            drop.update(dt)

        self.drops = [d for d in self.drops if d.ativo and not d.coletado]

    def coletar_jogador(self, jogador, mult_valor_drop: float = 1.0) -> list[dict]:
        """
        Testa colisão do jogador com drops ativos.
        Aplica efeitos imediatos e retorna lista de eventos de coleta ocorridos.
        """
        if not getattr(jogador, "vivo", True):
            return []

        j_x = jogador.x
        j_y = jogador.y
        j_w = getattr(jogador, "largura", 32)
        j_h = getattr(jogador, "altura", 32)

        coletados = []
        for drop in self.drops:
            if not drop.ativo or drop.coletado:
                continue

            if colisao_aabb(j_x, j_y, j_w, j_h, drop.x, drop.y, drop.largura, drop.altura):
                drop.coletado = True
                drop.ativo = False

                valor_efetivo = int(round(drop.valor * mult_valor_drop))
                if drop.tipo == "cura":
                    if hasattr(jogador, "curar"):
                        jogador.curar(valor_efetivo)

                try:
                    from PPlay.sound import Sound
                    sfx_nome = "sfx_coleta_xp" if drop.tipo == "xp" else "sfx_pickup"
                    sfx = Sound(obter_caminho_asset(sfx_nome))
                    sfx.play()
                except Exception:
                    pass

                coletados.append({
                    "tipo": drop.tipo,
                    "valor": valor_efetivo,
                    "drop": drop
                })

        return coletados

    def desenhar(self, janela, camera=None):
        """Renderiza todos os drops ativos."""
        for drop in self.drops:
            drop.desenhar(janela, camera)
