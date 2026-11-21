"""
Sistema de Drops — Protocolo: Batata
Gerencia a criação de drops na arena após a morte de inimigos, tabela de probabilidades,
atualização de ciclo de vida e coleta por contato do jogador.
"""

import random
import math
from src.entidades.drop import ItemDrop
from src.utils.math_utils import colisao_aabb
from src.utils.constantes import (
    DROP_XP_VALOR_BASE, DROP_CURA_VALOR_BASE,
    DROP_TEMPO_DESAPARECER, DROP_TEMPO_SCAVENGER_ATIVAR,
    DROP_LARGURA, DROP_ALTURA,
    obter_caminho_asset
)


class SistemaDrops:
    """
    Gerenciador de drops e itens no chão da arena.
    """

    MAX_DROPS = 300

    def __init__(self):
        self.drops: list[ItemDrop] = []
        self.cooldown_caixa_atual: float = 0.0
        self._proximo_par_capsula_id: int = 1

    def _adicionar_drop(self, drop: ItemDrop):
        """Adiciona um drop respeitando o limite MAX_DROPS (remove o drop mais antigo se exceder)."""
        self.drops.append(drop)
        if len(self.drops) > self.MAX_DROPS:
            del self.drops[:len(self.drops) - self.MAX_DROPS]

    def gerar_drop_morte_inimigo(
        self,
        x: float,
        y: float,
        tipo_inimigo: str = "padrao",
        bonus_chance_drop: float = 0.0,
        mult_chance_drop: float = 1.0,
        xp_base: int = None,
        loot_enriquecido: bool = False,
        chance_arma: float = None,
        chance_equipamento: float = None,
        is_elite: bool = False,
        modo_boss: bool = False,
        abate_rapido: bool = False
    ) -> list[ItemDrop]:
        """
        Gera os drops ao eliminar um inimigo:
        - No modo_boss (durante a luta contra Geladeira Tsunami):
          Zero gemas de XP, chance de drop reduzida em 60% (multiplicador 0.40 * (1.0 + bonus_chance_drop) * mult_chance_drop)
          com 10% Cura, 45% Arma e 45% Equipamento.
        - Inimigos Elite / Mini-Bosses geram garantidamente um cluster de 50 XP (5 gemas de 10 XP),
          uma caixa de arma especial, uma caixa de equipamento / drone e um Núcleo de Overclock.
        - Inimigos normais geram ao menos 1 gema de XP e rolam chances para cura, arma e equipamento.
        """
        novos_drops = []
        offset_drop_x = -float(DROP_LARGURA) / 2.0
        offset_drop_y = -float(DROP_ALTURA) / 2.0

        # Modo Boss (Geladeira Tsunami): Drops especiais sem XP, -60% taxa, 10% Cura, 45% Arma, 45% Equipamento
        # Checado antes de is_elite para garantir 0% XP durante a luta contra o Boss
        if modo_boss:
            mult_boss = 0.40 * (1.0 + bonus_chance_drop) * mult_chance_drop
            # Rola se haverá drop
            if random.random() < mult_boss:
                r_tipo = random.random()
                offset_x = random.uniform(-16.0, 16.0)
                offset_y = random.uniform(-16.0, 16.0)
                if r_tipo < 0.10:
                    d = ItemDrop(
                        x=x + offset_x + offset_drop_x,
                        y=y + offset_y + offset_drop_y,
                        tipo="cura",
                        valor=DROP_CURA_VALOR_BASE,
                        tempo_vida=DROP_TEMPO_DESAPARECER,
                        tempo_scavenger=DROP_TEMPO_SCAVENGER_ATIVAR
                    )
                elif r_tipo < 0.55:
                    d = ItemDrop(
                        x=x + offset_x + offset_drop_x,
                        y=y + offset_y + offset_drop_y,
                        tipo="arma",
                        valor=1,
                        tempo_vida=DROP_TEMPO_DESAPARECER,
                        tempo_scavenger=DROP_TEMPO_SCAVENGER_ATIVAR
                    )
                else:
                    d = ItemDrop(
                        x=x + offset_x + offset_drop_x,
                        y=y + offset_y + offset_drop_y,
                        tipo="equipamento",
                        valor=1,
                        tempo_vida=DROP_TEMPO_DESAPARECER,
                        tempo_scavenger=DROP_TEMPO_SCAVENGER_ATIVAR
                    )
                novos_drops.append(d)
                self._adicionar_drop(d)
            return novos_drops

        if is_elite:
            # 1. Cluster de 50 XP (5 gemas de 10 XP distribuídas em anel)
            for i in range(5):
                ang = i * (2.0 * math.pi / 5.0)
                offset_x = math.cos(ang) * 24.0
                offset_y = math.sin(ang) * 24.0
                gema_elite = ItemDrop(
                    x=x + offset_x - 8.0,
                    y=y + offset_y - 8.0,
                    tipo="xp",
                    valor=10,
                    tempo_vida=DROP_TEMPO_DESAPARECER,
                    tempo_scavenger=DROP_TEMPO_SCAVENGER_ATIVAR
                )
                novos_drops.append(gema_elite)
                self._adicionar_drop(gema_elite)

            # 2. Caixa de Arma Garantida
            drop_arma = ItemDrop(
                x=x - 20.0 - 8.0,
                y=y - 8.0,
                tipo="arma",
                valor=1,
                tempo_vida=DROP_TEMPO_DESAPARECER,
                tempo_scavenger=DROP_TEMPO_SCAVENGER_ATIVAR
            )
            if abate_rapido:
                drop_arma.bonus_municao_mult = 1.5
            novos_drops.append(drop_arma)
            self._adicionar_drop(drop_arma)

            # 3. Caixa de Equipamento Garantida
            drop_equip = ItemDrop(
                x=x + 20.0 - 8.0,
                y=y - 8.0,
                tipo="equipamento",
                valor=1,
                tempo_vida=DROP_TEMPO_DESAPARECER,
                tempo_scavenger=DROP_TEMPO_SCAVENGER_ATIVAR
            )
            novos_drops.append(drop_equip)
            self._adicionar_drop(drop_equip)

            # 4. Núcleo de Overclock Garantido
            drop_overclock = ItemDrop(
                x=x - 8.0,
                y=y - 24.0,
                tipo="overclock",
                valor=1,
                tempo_vida=DROP_TEMPO_DESAPARECER,
                tempo_scavenger=DROP_TEMPO_SCAVENGER_ATIVAR
            )
            novos_drops.append(drop_overclock)
            self._adicionar_drop(drop_overclock)

            # 5. Caixa de Cura (50% de chance para Mini-Boss, ou 100% com dobro de valor se abate_rapido)
            if abate_rapido or random.random() < 0.50:
                drop_cura = ItemDrop(
                    x=x - 8.0,
                    y=y + 24.0,
                    tipo="cura",
                    valor=DROP_CURA_VALOR_BASE * 2 if abate_rapido else DROP_CURA_VALOR_BASE,
                    tempo_vida=DROP_TEMPO_DESAPARECER,
                    tempo_scavenger=DROP_TEMPO_SCAVENGER_ATIVAR
                )
                novos_drops.append(drop_cura)
                self._adicionar_drop(drop_cura)

            return novos_drops

        # 1. Gema de XP Normal
        valor_xp = int(xp_base) if xp_base is not None else DROP_XP_VALOR_BASE
        gema_xp = ItemDrop(
            x=x + offset_drop_x,
            y=y + offset_drop_y,
            tipo="xp",
            valor=valor_xp,
            tempo_vida=DROP_TEMPO_DESAPARECER,
            tempo_scavenger=DROP_TEMPO_SCAVENGER_ATIVAR
        )
        novos_drops.append(gema_xp)
        self._adicionar_drop(gema_xp)

        # 2. Chance de Drop de Cura
        chance_cura_base = 0.08
        chance_cura_efetiva = min(1.0, chance_cura_base * (1.0 + bonus_chance_drop) * mult_chance_drop)
        if random.random() < chance_cura_efetiva:
            offset_x = random.uniform(-16.0, 16.0)
            offset_y = random.uniform(-16.0, 16.0)
            drop_cura = ItemDrop(
                x=x + offset_x + offset_drop_x,
                y=y + offset_y + offset_drop_y,
                tipo="cura",
                valor=DROP_CURA_VALOR_BASE,
                tempo_vida=DROP_TEMPO_DESAPARECER,
                tempo_scavenger=DROP_TEMPO_SCAVENGER_ATIVAR
            )
            novos_drops.append(drop_cura)
            self._adicionar_drop(drop_cura)

        # 3. Chance de Drop de Arma / Caixa Especial (+40% de frequência com chance explícita ou base dinâmica com cooldown)
        gerar_arma = False
        if chance_arma is not None:
            chance_arma_base = float(chance_arma) * 1.40
            chance_arma_efetiva = min(1.0, chance_arma_base * (1.0 + bonus_chance_drop) * mult_chance_drop)
            if random.random() < chance_arma_efetiva:
                gerar_arma = True
        else:
            if self.cooldown_caixa_atual <= 0.0:
                chance_arma_base = (0.06 if (loot_enriquecido or tipo_inimigo == "ranged") else 0.012)
                chance_arma_efetiva = min(1.0, chance_arma_base * (1.0 + bonus_chance_drop) * mult_chance_drop)
                if random.random() < chance_arma_efetiva:
                    gerar_arma = True
                    self.cooldown_caixa_atual = 6.0

        if gerar_arma:
            offset_x = random.uniform(-16.0, 16.0)
            offset_y = random.uniform(-16.0, 16.0)
            drop_arma = ItemDrop(
                x=x + offset_x + offset_drop_x,
                y=y + offset_y + offset_drop_y,
                tipo="arma",
                valor=1,
                tempo_vida=DROP_TEMPO_DESAPARECER,
                tempo_scavenger=DROP_TEMPO_SCAVENGER_ATIVAR
            )
            novos_drops.append(drop_arma)
            self._adicionar_drop(drop_arma)

        # 4. Chance de Drop de Equipamento / Drone (+40% de frequência com chance explícita ou base dinâmica com cooldown)
        gerar_equip = False
        if chance_equipamento is not None:
            chance_equip_base = float(chance_equipamento) * 1.40
            chance_equip_efetiva = min(1.0, chance_equip_base * (1.0 + bonus_chance_drop) * mult_chance_drop)
            if random.random() < chance_equip_efetiva:
                gerar_equip = True
        else:
            if self.cooldown_caixa_atual <= 0.0:
                chance_equip_base = (0.05 if (loot_enriquecido or tipo_inimigo == "ranged") else 0.012)
                chance_equip_efetiva = min(1.0, chance_equip_base * (1.0 + bonus_chance_drop) * mult_chance_drop)
                if random.random() < chance_equip_efetiva:
                    gerar_equip = True
                    self.cooldown_caixa_atual = 6.0

        if gerar_equip:
            offset_x = random.uniform(-16.0, 16.0)
            offset_y = random.uniform(-16.0, 16.0)
            drop_equip = ItemDrop(
                x=x + offset_x + offset_drop_x,
                y=y + offset_y + offset_drop_y,
                tipo="equipamento",
                valor=1,
                tempo_vida=DROP_TEMPO_DESAPARECER,
                tempo_scavenger=DROP_TEMPO_SCAVENGER_ATIVAR
            )
            novos_drops.append(drop_equip)
            self._adicionar_drop(drop_equip)

        return novos_drops

    def gerar_capsulas_powerup(self, centro_x: float, centro_y: float, opcoes: list[dict]) -> list[ItemDrop]:
        """Gera 2 cápsulas holográficas de escolha de power-up na arena vinculadas pelo mesmo par_id."""
        par_id = self._proximo_par_capsula_id
        self._proximo_par_capsula_id += 1
        criadas = []
        offsets_x = [-145.0, 145.0]
        from src.utils.constantes import LARGURA_ARENA, ALTURA_ARENA
        for idx, op in enumerate(opcoes[:2]):
            ox = offsets_x[idx] if idx < len(offsets_x) else 0.0
            cx_cap = max(48.0, min(float(LARGURA_ARENA - 48), centro_x + ox - float(DROP_LARGURA) / 2.0))
            cy_cap = max(48.0, min(float(ALTURA_ARENA - 48), centro_y - 36.0 - float(DROP_ALTURA) / 2.0))
            cap = ItemDrop(
                x=cx_cap,
                y=cy_cap,
                tipo="capsula_powerup",
                valor=int(op.get("valor", 1) if isinstance(op.get("valor", 1), (int, float)) and op.get("valor", 1) >= 1 else 1),
                tempo_vida=15.0,
                tempo_scavenger=999.0,
                largura=26,
                altura=26,
                subtipo=str(op.get("subtipo", op.get("tipo", "buff_dano_temp"))),
                rotulo=str(op.get("nome", "Suprimento")),
                par_id=par_id
            )
            cap.pickup_cooldown = 0.65
            criadas.append(cap)
            self._adicionar_drop(cap)
        return criadas

    def update(self, dt: float, pausar_despawn: bool = False):
        """Atualiza timers de todos os drops e remove expirados."""
        self.cooldown_caixa_atual = max(0.0, self.cooldown_caixa_atual - dt)
        for drop in self.drops:
            drop.update(dt, pausar_despawn=pausar_despawn)

        self.drops = [d for d in self.drops if d.ativo and not d.coletado]

    def coletar_jogador(self, jogador, mult_valor_drop: float = 1.0, mult_xp: float = 1.0) -> list[dict]:
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
            if getattr(drop, "pickup_cooldown", 0.0) > 0.0 and drop.tempo_decorrido < drop.pickup_cooldown:
                continue

            if colisao_aabb(j_x, j_y, j_w, j_h, drop.x, drop.y, drop.largura, drop.altura):
                drop.coletado = True
                drop.ativo = False

                if getattr(drop, "par_id", None) is not None:
                    for d in self.drops:
                        if d is not drop and getattr(d, "par_id", None) == drop.par_id:
                            d.ativo = False
                            d.coletado = True

                valor_efetivo = int(round(drop.valor * mult_valor_drop))
                sfx_nome = "sfx_pickup_xp"

                if drop.tipo == "cura":
                    sfx_nome = "sfx_pickup_cura"
                    if hasattr(jogador, "curar"):
                        jogador.curar(valor_efetivo)

                elif drop.tipo == "xp":
                    sfx_nome = "sfx_pickup_xp"
                    if hasattr(jogador, "ganhar_xp"):
                        jogador.ganhar_xp(valor_efetivo, mult_xp=mult_xp)

                elif drop.tipo == "overclock":
                    sfx_nome = "sfx_pickup_arma"

                elif drop.tipo == "arma":
                    sfx_nome = "sfx_pickup_arma"
                    from src.armas import Minigun, Shotgun, RifleAssalto, LancaFoguetes, LancaGranadas, Railgun
                    armas_especiais = [Minigun, Shotgun, RifleAssalto, LancaFoguetes, LancaGranadas, Railgun]
                    classe_arma = random.choice(armas_especiais)
                    nova_arma = classe_arma()

                    # Se Config 15 (coleta_inimiga) ativa (mult_valor_drop >= 2.0), dobra a munição
                    if mult_valor_drop > 1.0:
                        nova_arma.municao_max = int(round(nova_arma.municao_max * mult_valor_drop))
                        nova_arma.municao_atual = nova_arma.municao_max

                    bonus_mun = float(getattr(drop, "bonus_municao_mult", 1.0))
                    if bonus_mun > 1.0:
                        nova_arma.municao_max = int(round(nova_arma.municao_max * bonus_mun))
                        nova_arma.municao_atual = nova_arma.municao_max

                    if hasattr(jogador, "equipar_arma_especial"):
                        jogador.equipar_arma_especial(nova_arma)
                    elif hasattr(jogador, "arma_especial"):
                        if getattr(jogador, "bios_modding", False):
                            if jogador.arma_especial is None:
                                jogador.arma_especial = nova_arma
                                if hasattr(jogador, "selecionar_slot"):
                                    jogador.selecionar_slot(3)
                            else:
                                if len(jogador.armas) > 1:
                                    jogador.armas[1] = nova_arma
                                jogador.arma_especial_secundaria = nova_arma
                                if hasattr(jogador, "selecionar_slot"):
                                    jogador.selecionar_slot(2)
                                elif hasattr(jogador, "slot_ativo"):
                                    jogador.slot_ativo = 2
                        else:
                            jogador.arma_especial = nova_arma
                            if hasattr(jogador, "selecionar_slot"):
                                jogador.selecionar_slot(3)
                            elif hasattr(jogador, "slot_ativo"):
                                jogador.slot_ativo = 3

                elif drop.tipo == "equipamento":
                    sfx_nome = "sfx_pickup_equipamento"
                    from src.equipamentos import DroneCura, DroneCombate, DroneSuporte
                    drones = [DroneCura, DroneCombate, DroneSuporte]
                    classe_drone = random.choice(drones)
                    duracao = 30.0 * mult_valor_drop
                    novo_drone = classe_drone(tempo_vida=duracao)

                    if hasattr(jogador, "adicionar_drone"):
                        jogador.adicionar_drone(novo_drone)
                    elif hasattr(jogador, "drone"):
                        jogador.drone = novo_drone

                try:
                    from PPlay.sound import Sound
                    sfx = Sound(obter_caminho_asset(sfx_nome))
                    sfx.play()
                except Exception:
                    pass

                evento = {
                    "tipo": drop.tipo,
                    "valor": valor_efetivo,
                    "drop": drop,
                    "mult_drop": mult_valor_drop,
                    "x": drop.x,
                    "y": drop.y
                }
                if drop.tipo == "arma":
                    evento["arma"] = nova_arma
                coletados.append(evento)

        return coletados

    def desenhar(self, janela, camera=None, pausar_despawn: bool = False):
        """Renderiza todos os drops ativos."""
        for drop in self.drops:
            drop.desenhar(janela, camera, pausar_despawn=pausar_despawn)

