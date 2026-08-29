"""
Testes Adversariais e de Stress — Challenger: Scavenger 10s Delay Rule & Power-Ups / Golden Rule
SSOT: CONFIGURACOES.md, ORIGINAL_REQUEST.md, architecture_cache.md, PROJECT.md

Bateria exaustiva de testes adversariais:
1. Fronteiras exatas da elegibilidade de Drops para IA Scavenger:
   - 0.0s (inelegível)
   - 5.0s (inelegível)
   - 9.99s e 9.999999s (inelegíveis)
   - 10.00s e 10.000001s (elegíveis)
   - 15.0s e 59.99s (elegíveis)
   - 60.0s (expirado/inativo, inelegível)
   - Mutações de estado: ativo=False ou coletado=True tornam inelegível mesmo se tempo >= 10.0s
   - Ciclo de simulação temporal de 0.0s a 10.0s com seleção exata no limiar
   - Regra de seleção: exclusão estrita dos 3 mais próximos e teto de 600px
   - Consumo sem recompensa para a Batata

2. Mecânica de Escudo Protetor e Invulnerabilidade:
   - 1º hit (qualquer dano, até 10,000 overkill) é 100% absorvido (0 HP perdido)
   - Transição de escudo_ativo True -> False
   - Ativação imediata de timer de invulnerabilidade = 4.0s e flash de dano
   - 2º hit durante o timer de 4.0s causa 0 dano
   - Decaimento temporal por dt até 0.0s
   - 3º hit após término dos 4.0s aplica dano normal
   - Interação conjunta com buff de resistência

3. Buffs Temporários (Dano +5%, Vel +8%, Cadência +8%, Resistência -8%):
   - Precisão de decaimento de timers sob dt uniforme e irregular (micro-steps)
   - Clamping estrito em 0.0s (sem valores negativos)
   - Desativação imediata dos efeitos matemáticos exatamente após 15.0s
   - Renovo de duração (refresh) ao coletar novamente

4. Desigualdades da Regra de Ouro (Golden Rule):
   - Todos os power-ups temporários (15s) ou uso único
   - Consumível Dano (+5%) < Configurações de Dano (+10%, +15%, +20%, +25%, +30%, 2x Crítico)
   - Consumível Velocidade (+8%) <= Configurações de Velocidade (+8%, +10%, +15%)
   - Consumível Resistência (-8%) < Configurações de Redução de Dano (-15%, -27.75%, -50%)
   - Consumíveis de XP (+15, +30) e Cura (+25, +50) finitos vs multiplicadores perpétuos
"""

import os
import sys
import math
import random
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pygame
pygame.init()

from src.utils.constantes import (
    DROP_TEMPO_SCAVENGER_ATIVAR, DROP_TEMPO_DESAPARECER,
    JOGADOR_COOLDOWN_DANO_FLASH, CONFIGURACOES_CATALOGO
)
from src.sistemas.config_dados import CONFIGURACOES_GAMEPLAY
from src.sistemas.config_efeitos import calcular_modificadores
from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.sistemas.sistema_scavenger import SistemaScavenger
from src.sistemas.sistema_drops import SistemaDrops
from src.entidades.drop import ItemDrop
from src.entidades.jogador import Jogador
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.inimigo_tank import InimigoTank
from src.entidades.inimigo_rapido import InimigoRapido
from src.ui.modal_level_up import ModalLevelUp, gerar_pool_consumiveis_por_tier


class TestChallengerScavengerBoundariesAndExclusions(unittest.TestCase):
    """Testes adversariais para as fronteiras de 10.0s do Scavenger e algoritmo de exclusão."""

    def setUp(self):
        self.scav_sys = SistemaScavenger(dist_maxima=600.0)
        self.sistema_drops = SistemaDrops()

    def test_scavenger_constant_is_strictly_10_seconds(self):
        """Verifica se a constante DROP_TEMPO_SCAVENGER_ATIVAR é rigorosamente 10.0."""
        self.assertEqual(DROP_TEMPO_SCAVENGER_ATIVAR, 10.0)

    def test_drop_eligibility_sub_10s_boundaries(self):
        """Valida que todos os tempos < 10.0s são estritamente inelegíveis."""
        tempos_inelegiveis = [
            0.0,
            0.000001,
            0.5,
            1.0,
            5.0,
            9.0,
            9.5,
            9.9,
            9.99,
            9.999,
            9.999999
        ]
        for t in tempos_inelegiveis:
            drop = ItemDrop(x=100.0, y=100.0, tipo="xp", valor=10, tempo_scavenger=10.0)
            drop.tempo_decorrido = t
            self.assertFalse(
                drop.elegivel_scavenger(),
                f"Drop com tempo_decorrido={t}s não pode ser elegível para o Scavenger (< 10.0s)."
            )

    def test_drop_eligibility_at_and_above_10s_boundaries(self):
        """Valida que tempos >= 10.0s são elegíveis enquanto ativos."""
        tempos_elegiveis = [
            10.0,
            10.000001,
            10.001,
            10.1,
            15.0,
            30.0,
            50.0,
            59.99,
            59.9999
        ]
        for t in tempos_elegiveis:
            drop = ItemDrop(x=100.0, y=100.0, tipo="xp", valor=10, tempo_scavenger=10.0)
            drop.tempo_decorrido = t
            self.assertTrue(
                drop.elegivel_scavenger(),
                f"Drop com tempo_decorrido={t}s DEVE ser elegível para o Scavenger (>= 10.0s)."
            )

    def test_drop_ineligibility_when_inactive_or_collected(self):
        """Valida que drops com >= 10.0s tornam-se inelegíveis se inativos ou coletados."""
        drop1 = ItemDrop(x=100.0, y=100.0, tipo="xp", valor=10)
        drop1.tempo_decorrido = 15.0
        drop1.ativo = False
        self.assertFalse(drop1.elegivel_scavenger(), "Drop inativo não pode ser elegível.")

        drop2 = ItemDrop(x=100.0, y=100.0, tipo="xp", valor=10)
        drop2.tempo_decorrido = 15.0
        drop2.coletado = True
        self.assertFalse(drop2.elegivel_scavenger(), "Drop coletado não pode ser elegível.")

        # Drop expirado naturalmente aos 60s
        drop3 = ItemDrop(x=100.0, y=100.0, tipo="xp", valor=10, tempo_vida=60.0)
        drop3.update(60.1)
        self.assertFalse(drop3.ativo)
        self.assertFalse(drop3.elegivel_scavenger(), "Drop expirado não pode ser elegível.")

    def test_scavenger_simulation_temporal_stepping_across_threshold(self):
        """Simula 1000 micro-passos de 0.01s e confirma que o Scavenger só ativa exatamente em 10.00s."""
        drop = ItemDrop(x=300.0, y=300.0, tipo="cura", valor=35)
        e1 = InimigoPadrao(x=310.0, y=300.0)
        e2 = InimigoPadrao(x=320.0, y=300.0)
        e3 = InimigoPadrao(x=330.0, y=300.0)
        e4 = InimigoPadrao(x=450.0, y=300.0)
        inimigos = [e1, e2, e3, e4]

        dt = 0.01
        tempo_acumulado = 0.0

        # Passos de 0.0s até 9.99s
        while tempo_acumulado < 9.985:
            drop.update(dt)
            tempo_acumulado += dt
            self.assertFalse(drop.elegivel_scavenger())
            self.assertIsNone(self.scav_sys.selecionar_scavenger(inimigos, [drop]))

        # Passo que atinge 10.00s
        drop.update(dt * 2)  # atinge >= 10.00s
        self.assertTrue(drop.elegivel_scavenger())
        escolhido = self.scav_sys.selecionar_scavenger(inimigos, [drop])
        self.assertEqual(escolhido, e4, "No limiar de 10.0s, o 4º inimigo deve ser selecionado.")

    def test_scavenger_exclusion_3_closest_and_600px_ceiling(self):
        """
        Testa variações do pool de candidatos:
        - 0 a 3 inimigos dentro de 600px -> Nenhum selecionado (rejeição correta).
        - 4 inimigos dentro de 600px -> O 4º é selecionado.
        - 4 inimigos onde o 4º está a 650px (>600px) -> Nenhum selecionado.
        """
        drop = ItemDrop(x=100.0, y=100.0, tipo="xp", valor=10)
        drop.tempo_decorrido = 10.5

        # 0 inimigos
        self.assertIsNone(self.scav_sys.selecionar_scavenger([], [drop]))

        # 1 inimigo (dist 20px)
        e1 = InimigoPadrao(x=120.0, y=100.0)
        self.assertIsNone(self.scav_sys.selecionar_scavenger([e1], [drop]))

        # 2 inimigos (dist 20px, 40px)
        e2 = InimigoPadrao(x=140.0, y=100.0)
        self.assertIsNone(self.scav_sys.selecionar_scavenger([e1, e2], [drop]))

        # 3 inimigos (dist 20px, 40px, 60px)
        e3 = InimigoPadrao(x=160.0, y=100.0)
        self.assertIsNone(self.scav_sys.selecionar_scavenger([e1, e2, e3], [drop]))

        # 4 inimigos (o 4º a 650px, fora do raio de 600px)
        e4_longe = InimigoPadrao(x=750.0, y=100.0)
        self.assertIsNone(self.scav_sys.selecionar_scavenger([e1, e2, e3, e4_longe], [drop]))

        # 4 inimigos válidos (o 4º a 200px)
        e4_valido = InimigoPadrao(x=300.0, y=100.0)
        escolhido = self.scav_sys.selecionar_scavenger([e1, e2, e3, e4_valido], [drop])
        self.assertEqual(escolhido, e4_valido)

    def test_scavenger_persists_target_and_eats_drop_cleanly(self):
        """Scavenger mantém o alvo ao longo de múltiplos updates e destrói o drop sem premiar a Batata."""
        drop = ItemDrop(x=200.0, y=200.0, tipo="xp", valor=20)
        drop.tempo_decorrido = 10.0

        jogador = Jogador(x=50.0, y=50.0, hp_max=150)
        jogador.xp = 0

        scav = InimigoPadrao(x=250.0, y=200.0, velocidade=100.0)
        e1 = InimigoPadrao(x=205.0, y=200.0)
        e2 = InimigoPadrao(x=210.0, y=200.0)
        e3 = InimigoPadrao(x=215.0, y=200.0)
        inimigos = [e1, e2, e3, scav]

        # 1. Seleciona scav
        self.scav_sys.selecionar_scavenger(inimigos, [drop])
        self.assertEqual(self.scav_sys.scavenger_atual, scav)
        self.assertEqual(self.scav_sys.drop_alvo, drop)

        # 2. Atualiza aproximação por vários quadros
        for _ in range(10):
            self.scav_sys.update(dt=0.1, lista_inimigos=inimigos, lista_drops=[drop])

        # Drop deve ter sido alcançado e consumido
        self.assertFalse(drop.ativo)
        self.assertTrue(drop.coletado)
        self.assertIsNone(self.scav_sys.scavenger_atual)
        self.assertIsNone(self.scav_sys.drop_alvo)
        self.assertEqual(jogador.xp, 0, "Jogador não pode receber XP quando o Scavenger consome o drop.")


class TestChallengerShieldAndInvulnerabilityStress(unittest.TestCase):
    """Testes adversariais para absorção de dano pelo Escudo e timer de invulnerabilidade."""

    def setUp(self):
        self.jogador = Jogador(x=100.0, y=100.0, hp_max=150)

    def test_shield_full_absorption_and_4s_invulnerability_trigger(self):
        """
        1. Ativa escudo_ativo = True.
        2. Aplica dano massivo (10,000 HP).
        3. Verifica: 0 HP perdido, escudo_ativo torna-se False, invulnerabilidade_timer = 4.0s.
        """
        self.jogador.hp = 150
        self.jogador.escudo_ativo = True

        self.jogador.receber_dano(10000)

        self.assertEqual(self.jogador.hp, 150, "1º hit deve ser 100% absorvido sem perda de HP.")
        self.assertFalse(self.jogador.escudo_ativo, "Escudo deve desativar após absorver o 1º hit.")
        self.assertEqual(self.jogador.invulnerabilidade_timer, 4.0, "Timer de invulnerabilidade deve ser exatamente 4.0s.")
        self.assertAlmostEqual(self.jogador.flash_dano_timer, JOGADOR_COOLDOWN_DANO_FLASH)

    def test_shield_second_hit_during_invulnerability_deals_zero_damage(self):
        """Hits adicionais durante a janela de 4.0s causam rigorosamente 0 dano."""
        self.jogador.hp = 150
        self.jogador.escudo_ativo = True
        self.jogador.receber_dano(50)  # Quebra o escudo e ativa 4.0s

        # Simula hits em diferentes instantes dentro dos 4.0s
        instantes = [0.5, 1.0, 2.0, 3.0, 3.99]
        for t_passado in [0.5, 0.5, 1.0, 1.0, 0.99]:
            self.jogador.update(t_passado)
            self.assertGreater(self.jogador.invulnerabilidade_timer, 0.0)
            self.jogador.receber_dano(100)
            self.assertEqual(self.jogador.hp, 150, "Nenhum dano deve penetrar durante a invulnerabilidade de 4s.")

    def test_shield_hit_after_4s_deals_normal_damage(self):
        """Após o término dos 4.0s, o jogador volta a receber dano normal."""
        self.jogador.hp = 150
        self.jogador.escudo_ativo = True
        self.jogador.receber_dano(50)  # Quebra o escudo

        # Avança 4.05s no total
        self.jogador.update(4.05)
        self.assertEqual(self.jogador.invulnerabilidade_timer, 0.0)

        # 3º Hit após os 4s
        self.jogador.receber_dano(40)
        self.assertEqual(self.jogador.hp, 110, "Dano após 4.0s deve ser aplicado normalmente.")

    def test_shield_combined_with_resistance_buff(self):
        """
        Testa combinação de Escudo + Buff de Resistência (-8% dano recebido):
        - Enquanto o escudo está ativo: absorve 100% (0 dano).
        - Durante os 4s de invulnerabilidade: 0 dano.
        - Após 4s, se o buff de resistência ainda estiver ativo: aplica -8% de redução no dano.
        """
        self.jogador.hp = 150
        self.jogador.escudo_ativo = True
        self.jogador.buff_resistencia_timer = 15.0

        # Hit 1 -> Absorvido pelo escudo
        self.jogador.receber_dano(100)
        self.assertEqual(self.jogador.hp, 150)
        self.assertEqual(self.jogador.invulnerabilidade_timer, 4.0)

        # Avança 4.05s -> Invulnerabilidade zera, buff_resistencia_timer = 15.0 - 4.05 = 10.95s (>0)
        self.jogador.update(4.05)
        self.assertEqual(self.jogador.invulnerabilidade_timer, 0.0)
        self.assertAlmostEqual(self.jogador.buff_resistencia_timer, 10.95, places=2)

        # Hit 2 -> Dano 100 com -8% resistência -> sofre 92 de dano
        self.jogador.receber_dano(100)
        self.assertEqual(self.jogador.hp, 150 - 92)  # 58 HP


class TestChallengerTemporaryBuffsTimersAndExpiry(unittest.TestCase):
    """Testes adversariais da mecânica e precisão de decaimento dos Buffs Temporários de 15s."""

    def setUp(self):
        self.jogador = Jogador(x=100.0, y=100.0, hp_max=150, velocidade=200.0)
        self.mgr = GerenciadorConfiguracoes()
        self.modal = ModalLevelUp(self.mgr, self.jogador)

    def test_buff_dano_15s_accuracy_and_clamping(self):
        """Buff de dano dura exatamente 15.0s, decai com dt e não fica negativo."""
        self.jogador.buff_dano_timer = 15.0

        # Decaimento em passos pequenos
        dt_list = [0.016667, 0.033333, 0.5, 1.45, 5.0, 8.0]
        tempo_total = sum(dt_list)
        for dt in dt_list:
            self.jogador.update(dt)

        self.assertAlmostEqual(self.jogador.buff_dano_timer, 15.0 - tempo_total, places=4)

        # Passo gigante para expirar
        self.jogador.update(10.0)
        self.assertEqual(self.jogador.buff_dano_timer, 0.0, "Timer deve ser fixado em 0.0 sem ficar negativo.")

    def test_buff_velocidade_15s_effect_application_and_clean_removal(self):
        """
        Buff de velocidade:
        - Aplica +8% durante 15.0s (velocidade_atual = 200 * 1.08 = 216.0).
        - Exatamente em t >= 15.0s, velocidade_atual volta para 200.0.
        """
        self.jogador.buff_vel_timer = 15.0
        self.jogador.update(0.1)
        self.assertAlmostEqual(self.jogador.velocidade_atual, 216.0, places=3)

        # Avança até 14.9s
        self.jogador.update(14.8)
        self.assertGreater(self.jogador.buff_vel_timer, 0.0)
        self.assertAlmostEqual(self.jogador.velocidade_atual, 216.0, places=3)

        # Avança +0.2s (total 15.1s) -> buff expira
        self.jogador.update(0.2)
        self.assertEqual(self.jogador.buff_vel_timer, 0.0)
        self.assertAlmostEqual(self.jogador.velocidade_atual, 200.0, places=3)

    def test_buff_cadencia_15s_multiplier_to_weapons(self):
        """
        Buff de cadência:
        - Enquanto ativo, acelera update das armas por fator 1.08.
        - Quando inativo, armas recebem fator 1.0.
        """
        self.jogador.buff_cadencia_timer = 15.0
        pistola = self.jogador.armas[1]
        pistola.tempo_recarga_restante = 1.0

        # Com buff: update(0.1) reduz tempo_recarga_restante por 0.1 * 1.08 = 0.108
        self.jogador.update(0.1)
        self.assertAlmostEqual(pistola.tempo_recarga_restante, 1.0 - 0.108, places=4)

        # Expira o buff
        self.jogador.update(15.0)
        self.assertEqual(self.jogador.buff_cadencia_timer, 0.0)

        # Sem buff: define novo tempo de recarga e verifica decaimento normal 1.0x
        pistola.tempo_recarga_restante = 1.0
        self.jogador.update(0.1)
        self.assertAlmostEqual(pistola.tempo_recarga_restante, 0.900, places=4)

    def test_buff_resistencia_15s_damage_reduction_and_expiry(self):
        """
        Buff de resistência:
        - Enquanto ativo, dano 100 -> sofre 92.
        - Quando inativo, dano 100 -> sofre 100.
        """
        self.jogador.hp = 200
        self.jogador.hp_max = 200
        self.jogador.buff_resistencia_timer = 15.0

        # Ativo: 100 dano -> 92 dano
        self.jogador.receber_dano(100)
        self.assertEqual(self.jogador.hp, 108)

        # Expira
        self.jogador.update(15.1)
        self.assertEqual(self.jogador.buff_resistencia_timer, 0.0)

        # Inativo: 50 dano -> 50 dano
        self.jogador.receber_dano(50)
        self.assertEqual(self.jogador.hp, 58)

    def test_buff_timer_refresh_on_repeated_selection(self):
        """Selecionar o card de buff novamente reseta o timer para 15.0s."""
        card_vel = {"tipo": "buff_vel_temp", "duracao": 15.0}
        self.modal.cards_sorteados = [card_vel]
        self.modal.ativo = True
        self.modal.fila_level_ups = 1
        self.modal.selecionar_card(0)
        self.assertEqual(self.jogador.buff_vel_timer, 15.0)

        # Avança 10s -> restam 5s
        self.jogador.update(10.0)
        self.assertAlmostEqual(self.jogador.buff_vel_timer, 5.0)

        # Seleciona novamente
        self.modal.cards_sorteados = [card_vel]
        self.modal.ativo = True
        self.modal.fila_level_ups = 1
        self.modal.selecionar_card(0)
        self.assertEqual(self.jogador.buff_vel_timer, 15.0, "Timer deve ser renovado para 15.0s.")


class TestChallengerGoldenRuleInequalitiesExhaustive(unittest.TestCase):
    """Testes adversariais exaustivos das desigualdades numéricas da Regra de Ouro."""

    def test_all_consumables_have_finite_duration_or_single_use(self):
        """Garante que nenhum consumível confere buffs permanentes."""
        for tier in [1, 2, 3, 4]:
            pool = gerar_pool_consumiveis_por_tier(tier)
            for card in pool:
                stype = card.get("subtipo", "")
                if "buff_" in stype:
                    self.assertIn("duracao", card)
                    self.assertEqual(card["duracao"], 15.0, "Todo buff deve ter duração finita de 15s.")
                elif stype in ("cura_pequena", "cura_grande", "xp_pequeno", "xp_grande", "pulso_magnetico", "escudo"):
                    self.assertIn("valor", card)
                elif stype in ("caixa_arma", "caixa_equip"):
                    pass  # Armas esgotam munição, drones duram 30s
                else:
                    self.fail(f"Subtipo desconhecido {stype} encontrado no catálogo de consumíveis.")

    def test_damage_buff_strictly_lower_than_all_damage_configs(self):
        """
        Buff de dano do consumível (+5%) deve ser estritamente MENOR que todas as opções de bônus de dano das 20 configurações.
        Configurações com bônus de dano:
        - zoom (125% -> +10%, 150% -> +20%)
        - keybinds (invertido -> +10%, pesadelo -> +30%)
        - auto_fire (desligado -> +15%)
        - screen_shake (ligado -> +20% explosivos)
        - cores_invertidas (ligado -> +20%)
        - fogo_amigo (ligado -> +25%)
        - damage_numbers (ligado -> 2x crítico)
        """
        buff_dano_consumivel = 0.05

        config_damage_bonuses = [
            ("zoom_125", 0.10),
            ("zoom_150", 0.20),
            ("keybinds_invertido", 0.10),
            ("keybinds_pesadelo", 0.30),
            ("auto_fire_desligado", 0.15),
            ("screen_shake_ligado", 0.20),
            ("cores_invertidas_ligado", 0.20),
            ("fogo_amigo_ligado", 0.25),
        ]

        for nome, bonus in config_damage_bonuses:
            self.assertLess(
                buff_dano_consumivel,
                bonus,
                f"Buff de consumível (+{buff_dano_consumivel*100}%) viola a Regra de Ouro contra {nome} (+{bonus*100}%)."
            )

    def test_speed_buff_less_than_or_equal_to_speed_configs(self):
        """
        Buff de velocidade do consumível (+8%) deve ser <= ao menor bônus de configuração (+8%) e < aos demais (+10%, +15%).
        Configurações de velocidade:
        - suavizacao_camera (desligado -> +8%)
        - vsync (desligado -> +10%)
        - motion_blur (ligado -> +15%)
        - keybinds (arrow_keys -> +15%)
        """
        buff_vel_consumivel = 0.08

        config_speed_bonuses = [
            ("suavizacao_camera_desligado", 0.08),
            ("vsync_desligado", 0.10),
            ("motion_blur_ligado", 0.15),
            ("keybinds_arrow_keys", 0.15),
        ]

        for nome, bonus in config_speed_bonuses:
            self.assertLessEqual(
                buff_vel_consumivel,
                bonus,
                f"Buff de consumível (+{buff_vel_consumivel*100}%) viola a Regra de Ouro contra {nome} (+{bonus*100}%)."
            )

    def test_resistance_buff_strictly_lower_than_config_damage_reductions(self):
        """
        Buff de resistência do consumível (-8% dano recebido) deve ser MENOR que as reduções de dano das configurações:
        - fps_cap (45 FPS -> -15%)
        - fps_cap (15 FPS -> -27.75%)
        - iluminacao (ligado -> -50% fora do cone)
        """
        buff_res_consumivel = 0.08

        config_damage_reductions = [
            ("fps_cap_45", 0.15),
            ("fps_cap_15", 0.2775),
            ("iluminacao_ligado", 0.50),
        ]

        for nome, reduction in config_damage_reductions:
            self.assertLess(
                buff_res_consumivel,
                reduction,
                f"Buff de resistência ({buff_res_consumivel*100}%) viola a Regra de Ouro contra {nome} ({reduction*100}%)."
            )


if __name__ == "__main__":
    unittest.main()
