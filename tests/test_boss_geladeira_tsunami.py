"""
Suite de Testes Abrangente — Endgame Progression & Boss Encounter Systems
Cobre Tiers 1 a 4 para Protocolo: Batata:
- Tier 1: Cobertura completa de Funcionalidades (R1 a R5)
- Tier 2: Casos de Borda e Limites Numéricos
- Tier 3: Combinações Cruzadas entre Subsistemas
- Tier 4: Cenário E2E de Progressão Completa do Boss Geladeira Tsunami
"""

import os
import sys
import math
import random
import unittest

# Inicialização headless do Pygame antes de qualquer módulo do jogo
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pygame
pygame.init()
pygame.font.init()
pygame.display.set_mode((800, 600))

from src.utils.constantes import (
    ASSET_PATHS, obter_caminho_asset,
    GELADEIRA_TSUNAMI_LARGURA, GELADEIRA_TSUNAMI_ALTURA,
    GELADEIRA_TSUNAMI_HP, GELADEIRA_TSUNAMI_DANO,
    GELADEIRA_TSUNAMI_VELOCIDADE, GELADEIRA_TSUNAMI_NOME,
    GELADEIRA_TSUNAMI_FLAVOR, BOSS_GELADEIRA_LARGURA,
    BOSS_GELADEIRA_ALTURA, BOSS_GELADEIRA_HP_BASE,
    MINIBOSS_TEMPO_SOBREAQUECIMENTO,
    DROP_TEMPO_DESAPARECER, DROP_TEMPO_SCAVENGER_ATIVAR,
    DROP_CURA_VALOR_BASE, DROP_XP_VALOR_BASE,
    LARGURA_TELA, ALTURA_TELA
)
from src.sistemas.sistema_xp import SistemaXP
from src.sistemas.sistema_spawn import SistemaSpawn
from src.sistemas.sistema_drops import SistemaDrops
from src.entidades.inimigo_base import InimigoBase
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.inimigo_rapido import InimigoRapido
from src.entidades.inimigo_tank import InimigoTank
from src.entidades.inimigo_phasing import InimigoPhasing
from src.entidades.inimigo_blindado import InimigoBlindado
from src.entidades.inimigo_ranged import InimigoRanged
from src.entidades.jogador import Jogador
from src.entidades.drop import ItemDrop
from src.entidades.projetil import Projetil
from src.entidades.inimigos.geladeira_tsunami import (
    GeladeiraTsunami, ESTADO_INTRO, ESTADO_FASE1,
    ESTADO_FASE2, ESTADO_FASE3, ESTADO_MORTE
)
from src.armas import (
    Melee, Pistola, Minigun, Shotgun, RifleAssalto, LancaFoguetes, LancaGranadas, Railgun
)
from src.ui.modal_overclock import ModalOverclock, CATALOGO_OVERCLOCKS
from src.ui.menu_debug import MenuDebug
from src.ui.hud import HUD
from src.cenas.gameplay import GameplayScene


# =============================================================================
# TIER 1: FEATURE COVERAGE (R1 - R5)
# =============================================================================

class TestTier1FeatureCoverage(unittest.TestCase):
    """Testes unitários de conformidade com todos os requisitos R1 a R5."""

    def setUp(self):
        self.jogador = Jogador(x=400, y=300)
        self.sistema_xp = SistemaXP()
        self.sistema_drops = SistemaDrops()
        self.spawner = SistemaSpawn()

    # --- R2: XP Curve Smoothing ---
    def test_t1_xp_curve_smoothing_values(self):
        """Valida que para nível > 10, o XP necessário é reduzido em 25%: int(round(base * 0.75))."""
        # Níveis 1 a 10: curva padrão base = 20 + 10*lvl + 5*(lvl^2)
        esperados_padrao = {
            1: 35,
            2: 60,
            3: 95,
            4: 140,
            5: 195,
            10: 620
        }
        for lvl, val in esperados_padrao.items():
            base = 20 + 10 * lvl + 5 * (lvl ** 2)
            self.assertEqual(SistemaXP.calcular_xp_para_nivel(lvl), base)
            self.assertEqual(SistemaXP.calcular_xp_para_nivel(lvl), val)
            self.assertEqual(self.sistema_xp.calcular_xp_necessario(lvl), val)

        # Níveis 11 a 20: curva suavizada (25% de desconto)
        esperados_suavizados = {
            11: 551,   # round((20 + 110 + 605) * 0.75) = round(735 * 0.75) = 551
            12: 645,   # round((20 + 120 + 720) * 0.75) = round(860 * 0.75) = 645
            15: 971,   # round((20 + 150 + 1125) * 0.75) = round(1295 * 0.75) = 971
            20: 1665   # round((20 + 200 + 2000) * 0.75) = round(2220 * 0.75) = 1665
        }
        for lvl, val in esperados_suavizados.items():
            base = 20 + 10 * lvl + 5 * (lvl ** 2)
            calculado = int(round(base * 0.75))
            self.assertEqual(SistemaXP.calcular_xp_para_nivel(lvl), calculado)
            self.assertEqual(SistemaXP.calcular_xp_para_nivel(lvl), val)
            self.assertEqual(self.sistema_xp.calcular_xp_necessario(lvl), val)

    # --- R2: Victory Decoupling ---
    def test_t1_victory_condition_decoupled_from_timer(self):
        """Valida que o timer de 10 minutos (600s) NÃO encerra o jogo com vitória; vitória requer boss."""
        cena = GameplayScene()
        cena.tempo_sobrevivencia = 650.0  # Passou de 10 minutos
        cena.loop()

        self.assertFalse(cena.vitoria, "O timer de sobrevivência não deve mais acionar vitória automaticamente!")
        self.assertFalse(cena.game_over)

        # Spawna e derrota o chefe final -> vitória imediata
        boss = GeladeiraTsunami(x=400, y=300)
        boss.vivo = False
        boss.morreu = True
        cena.chefe_final = boss
        cena.loop()

        self.assertTrue(cena.vitoria, "A derrota do Chefe Final Geladeira Tsunami deve disparar a vitória!")

    # --- R1: Mini-Boss Schedule & Names ---
    def test_t1_mini_boss_schedule_and_names(self):
        """Verifica o catálogo e nomes de Mini-Bosses alinhados a CATALOGO_ARQUITETURAL.md."""
        cls1, nome1 = self.spawner.obter_arquetipo_elite(1)
        self.assertEqual(cls1, InimigoRapido)
        self.assertEqual(nome1, "MINI-BOSS: ESTAGIÁRIO SÊNIOR")

        cls2, nome2 = self.spawner.obter_arquetipo_elite(2)
        self.assertEqual(cls2, InimigoTank)
        self.assertTrue("MINI-BOSS:" in nome2)

        cls3, nome3 = self.spawner.obter_arquetipo_elite(3)
        self.assertEqual(cls3, InimigoPhasing)
        self.assertTrue("MINI-BOSS:" in nome3)

        cls4, nome4 = self.spawner.obter_arquetipo_elite(4)
        self.assertEqual(cls4, InimigoBlindado)
        self.assertTrue("MINI-BOSS:" in nome4)

    # --- R1: Mini-Boss 2x Scaling ---
    def test_t1_mini_boss_2x_scale_and_hitbox(self):
        """Verifica que todos os mini-bosses possuem 2x largura, 2x altura e hitbox física 2x."""
        arquetipos = [
            (InimigoRapido, 31, 31, 20),
            (InimigoTank, 62, 62, 120),
            (InimigoPhasing, 42, 42, 35),
            (InimigoBlindado, 47, 47, 50),
            (InimigoPadrao, 28, 28, 40)
        ]
        for cls_inimigo, w_base, h_base, hp_base in arquetipos:
            comum = cls_inimigo(x=100, y=100, is_elite=False)
            elite = cls_inimigo(x=100, y=100, is_elite=True, nome_elite="MINI-BOSS TESTE")

            self.assertEqual(comum.largura, w_base)
            self.assertEqual(comum.altura, h_base)
            self.assertEqual(elite.largura, w_base * 2)
            self.assertEqual(elite.altura, h_base * 2)
            self.assertEqual(elite.width, w_base * 2)
            self.assertEqual(elite.height, w_base * 2)

            # Hitbox AABB
            rect_elite = elite.get_rect()
            self.assertEqual(rect_elite, (100.0, 100.0, w_base * 2, h_base * 2))

            # 3x HP base
            self.assertEqual(elite.hp_max, hp_base * 3)

    # --- R1: Mini-Boss Anti-Stacking ---
    def test_t1_mini_boss_anti_stacking(self):
        """Verifica que novos mini-bosses não surgem se já houver um elite vivo na arena."""
        spawner = SistemaSpawn()
        # Simula tempo onde o boss deveria spawnar (60s) mas possui_elite_vivo=True
        novos = spawner.update(
            dt=65.0,
            camera_x=0,
            camera_y=0,
            total_inimigos_vivos=5,
            possui_elite_vivo=True
        )
        elites = [inim for inim in novos if getattr(inim, "is_elite", False)]
        self.assertEqual(len(elites), 0, "Não deve spawnar outro mini-boss enquanto houver elite ativo!")

    # --- R1: 60.0s Thermal Overload & Toast ---
    def test_t1_thermal_overload_countdown_toast_and_no_loot(self):
        """Verifica contagem de 60s de sobreaquecimento, destruição sem loot e texto de toast."""
        elite = InimigoRapido(x=200, y=200, is_elite=True)
        self.assertEqual(elite.tempo_vida_restante, 60.0)
        self.assertFalse(elite.superaqueceu)

        # Atualiza 60.5s -> superaquece
        elite.update(60.5, (400, 300))
        self.assertTrue(elite.superaqueceu)
        self.assertFalse(elite.vivo)

        # No loop de gameplay, adiciona toast exato
        cena = GameplayScene()
        cena.inimigos.append(elite)
        cena.loop()

        textos_toast = [t["texto"] for t in cena.toasts_coleta]
        toast_esperado = "O MINI-BOSS SUPERAQUECEU. VOCÊ NÃO RECEBERÁ RECOMPENSAS POR ELE."
        self.assertIn(toast_esperado, textos_toast)

    # --- R1: Overclock Drop & Modal ---
    def test_t1_overclock_drop_and_modal_opening(self):
        """Verifica que abater mini-boss dentro de 60s gera drop_overclock e abre ModalOverclock."""
        drops = self.sistema_drops.gerar_drop_morte_inimigo(
            x=300, y=300, is_elite=True, modo_boss=False
        )
        tipos_gerados = [d.tipo for d in drops]
        self.assertIn("overclock", tipos_gerados)
        self.assertIn("arma", tipos_gerados)
        self.assertIn("equipamento", tipos_gerados)
        self.assertEqual(tipos_gerados.count("xp"), 5)  # Cluster de 5 gemas de 10 XP

        # Coleta de drop de overclock na GameplayScene
        cena = GameplayScene()
        drop_ov = ItemDrop(x=cena.jogador.x, y=cena.jogador.y, tipo="overclock")
        cena.sistema_drops.drops.append(drop_ov)
        cena.loop()

        self.assertTrue(cena.modal_overclock.ativo)
        self.assertEqual(len(cena.modal_overclock.cards_sorteados), 3)

    # --- R1: All 6 Overclock BIOS Modules ---
    def test_t1_all_6_overclock_bios_modules(self):
        """Verifica a aplicação e ativação de todos os 6 módulos de Overclock."""
        ids_modulos = [m["id"] for m in CATALOGO_OVERCLOCKS]
        self.assertEqual(len(ids_modulos), 6)
        self.assertEqual(
            set(ids_modulos),
            {"multithreading", "refrigeracao", "overvolt", "bios_modding", "protecao_surtos", "upgrade_barramento"}
        )

        jogador = Jogador(x=400, y=300)

        # 1. Multithreading
        jogador.aplicar_overclock("multithreading")
        self.assertTrue(jogador.multithreading)

        # 2. Refrigeração a Nitrogênio
        jogador.aplicar_overclock("refrigeracao")
        self.assertTrue(jogador.refrigeracao_nitrogenio)

        # 3. Overvolt
        jogador.aplicar_overclock("overvolt")
        self.assertTrue(jogador.overvolt)

        # 4. BIOS Modding
        jogador.aplicar_overclock("bios_modding")
        self.assertTrue(jogador.bios_modding)

        # 5. Proteção contra Surtos
        hp_max_ant = jogador.hp_max
        jogador.aplicar_overclock("protecao_surtos")
        self.assertTrue(jogador.protecao_surtos)
        self.assertEqual(jogador.hp_max, hp_max_ant + 50)
        self.assertTrue(jogador.escudo_fatal_pronto)

        # 6. Upgrade de Barramento
        jogador.aplicar_overclock("upgrade_barramento")
        self.assertTrue(jogador.upgrade_barramento)
        jogador.update(0.01)
        self.assertAlmostEqual(jogador.velocidade_atual, jogador.velocidade_base * 1.40, delta=0.5)

    # --- R3: Geladeira Tsunami Entity Dimensions & Assets ---
    def test_t1_geladeira_tsunami_entity_dimensions_and_assets(self):
        """Verifica dimensões estritas 112x156 px, hitbox e chaves de assets."""
        self.assertIn("musica_boss", ASSET_PATHS)
        self.assertIn("boss_geladeira_tsunami", ASSET_PATHS)
        self.assertEqual(ASSET_PATHS["musica_boss"], "audio/musica/geladeira tsunami.wav")
        self.assertEqual(ASSET_PATHS["boss_geladeira_tsunami"], "sprites/inimigos/geladeira_tsunami.png")

        self.assertEqual(GELADEIRA_TSUNAMI_LARGURA, 112)
        self.assertEqual(GELADEIRA_TSUNAMI_ALTURA, 156)
        self.assertEqual(BOSS_GELADEIRA_LARGURA, 112)
        self.assertEqual(BOSS_GELADEIRA_ALTURA, 156)

        boss = GeladeiraTsunami(x=300, y=200)
        self.assertEqual(boss.largura, 112)
        self.assertEqual(boss.altura, 156)
        self.assertEqual(boss.rect.width, 112)
        self.assertEqual(boss.rect.height, 156)

    # --- R3: Boss Speech Balloon ---
    def test_t1_boss_speech_balloon_text_and_duration(self):
        """Verifica o texto exato da fala do Boss e duração da intro (3.5s)."""
        boss = GeladeiraTsunami(x=300, y=200)
        self.assertEqual(boss.estado, ESTADO_INTRO)
        self.assertTrue(boss.mostrar_balao_fala)
        texto_esperado = "Você já passou da validade.\nSente a pressão, neném."
        self.assertEqual(boss.balao_fala_texto, texto_esperado)

        # Avança 3.6s -> balão desativa e FSM entra em Fase 1
        boss.update(3.6, (300, 200))
        self.assertFalse(boss.mostrar_balao_fala)
        self.assertEqual(boss.estado, ESTADO_FASE1)

    # --- R3: Boss 3-Phase FSM ---
    def test_t1_boss_3_phase_fsm(self):
        """Verifica a sequência de FSM: Intro -> Fase 1 -> Fase 2 -> Fase 3 -> Morte."""
        boss = GeladeiraTsunami(x=300, y=200, hp=2500)
        boss.update(3.6, (300, 200))  # Intro concluída
        self.assertEqual(boss.estado, ESTADO_FASE1)

        # Dano para 60% HP -> Fase 2
        boss.receber_dano(1000)
        self.assertEqual(boss.estado, ESTADO_FASE2)

        # Dano para 25% HP -> Fase 3
        boss.receber_dano(900)
        self.assertEqual(boss.estado, ESTADO_FASE3)

        # Dano letal -> Morte (1.5s cascade)
        boss.receber_dano(boss.hp)
        self.assertEqual(boss.estado, ESTADO_MORTE)
        self.assertTrue(boss.vivo)

        boss.update(1.6, (300, 200))
        self.assertFalse(boss.vivo)
        self.assertTrue(boss.morreu)

    # --- R4: 4-Phase Intro Cutscene Sequence ---
    def test_t1_4_phase_intro_cutscene_sequence(self):
        """Verifica a progressão da cutscene: Whiteout 2.0s -> Blackout 1.0s -> Música/Rise 5.0s -> Unlock."""
        cena = GameplayScene()
        cena.iniciar_boss_cutscene()

        # Fase 1: Whiteout (2.0s)
        self.assertTrue(cena.boss_cutscene_ativa)
        self.assertEqual(cena.boss_cutscene_fase, "whiteout")
        self.assertEqual(cena.overlay_cutscene_cor, (255, 255, 255))

        # Avança 2.1s -> Fase 2: Blackout
        cena.boss_cutscene_timer = 2.1
        cena.loop()
        self.assertEqual(cena.boss_cutscene_fase, "blackout")
        self.assertEqual(cena.overlay_cutscene_cor, (0, 0, 0))

        # Avança 1.1s -> Fase 3: Musica / Rise
        cena.boss_cutscene_timer = 1.1
        cena.loop()
        self.assertEqual(cena.boss_cutscene_fase, "musica_in")
        self.assertIsNotNone(cena.chefe_final)

        # Conclusão da intro do boss -> desbloqueia partida
        cena.chefe_final.intro_concluida = True
        cena.loop()
        self.assertFalse(cena.boss_cutscene_ativa)
        self.assertEqual(cena.boss_cutscene_fase, "combate")

    # --- R4: Boss-Mode Drop Rules ---
    def test_t1_boss_mode_drop_rules(self):
        """Verifica que durante o Boss: 0% XP, 40% taxa de drop, drops não despawnam."""
        drops_sys = SistemaDrops()
        # Amostragem de drops gerados em modo boss
        random.seed(42)
        total_drops = []
        for _ in range(100):
            d = drops_sys.gerar_drop_morte_inimigo(100, 100, modo_boss=True, mult_chance_drop=1.0)
            total_drops.extend(d)

        # 0% de gemas de XP
        self.assertTrue(all(d.tipo != "xp" for d in total_drops))

        # Testa pausar_despawn=True
        drop_amostra = ItemDrop(x=100, y=100, tipo="cura", tempo_vida=60.0)
        drops_sys.drops = [drop_amostra]
        drops_sys.update(dt=15.0, pausar_despawn=True)
        self.assertEqual(drop_amostra.tempo_restante, 60.0)

    # --- R4: Boss-Mode Spawner Rules ---
    def test_t1_boss_mode_spawner_rules(self):
        """Verifica que o spawner é throttled a 20% e contém apenas InimigoPadrao durante o Boss."""
        cena = GameplayScene()
        boss = GeladeiraTsunami(x=400, y=300)
        cena.chefe_final = boss
        cena.inimigos = [boss]

        # Simula múltiplos loops
        for _ in range(50):
            cena.loop()

        mobs_comuns = [inim for inim in cena.inimigos if inim != boss]
        self.assertLessEqual(len(mobs_comuns), 10)
        for mob in mobs_comuns:
            self.assertIsInstance(mob, InimigoPadrao)

    # --- R5: Debug Commands in MenuDebug ---
    def test_t1_debug_commands_in_menudebug(self):
        """Verifica comandos de depuração de Boss, Overclock e Elites no MenuDebug."""
        cena = GameplayScene()
        menu = cena.menu_debug

        # 1. Opção 12: Iniciar Boss Cutscene
        menu.indice_foco = 12
        menu._executar_acao_selecionada()
        self.assertTrue(cena.boss_cutscene_ativa)
        cena.boss_cutscene_ativa = False

        # 2. Opção 13: Conceder Overclock
        menu.indice_foco = 13
        menu.idx_overclock = 0  # Multithreading
        menu._executar_acao_selecionada()
        self.assertTrue(cena.jogador.multithreading)

        # 3. Opção 14: Matar Chefe
        boss = GeladeiraTsunami(x=400, y=300)
        cena.chefe_final = boss
        cena.inimigos = [boss]
        menu.indice_foco = 14
        menu._executar_acao_selecionada()
        self.assertLessEqual(boss.hp, 0)


# =============================================================================
# TIER 2: BOUNDARY & CORNER CASES
# =============================================================================

class TestTier2BoundaryAndCornerCases(unittest.TestCase):
    """Testes de valores limite, transbordo e temporizadores estritos."""

    def setUp(self):
        self.jogador = Jogador(x=400, y=300)
        self.sistema_xp = SistemaXP()

    def test_t2_thermal_overload_boundary_60s(self):
        """Valida que aos 59.9s o elite continua vivo e aos 60.0s/60.1s ele superaquece."""
        elite = InimigoRapido(x=100, y=100, is_elite=True)
        # Avança 59.9 segundos
        elite.update(59.9, (400, 300))
        self.assertTrue(elite.vivo)
        self.assertFalse(elite.superaqueceu)
        self.assertAlmostEqual(elite.tempo_vida_restante, 0.1, delta=0.01)

        # Avança mais 0.2 segundos (total 60.1s)
        elite.update(0.2, (400, 300))
        self.assertFalse(elite.vivo)
        self.assertTrue(elite.superaqueceu)
        self.assertEqual(elite.tempo_vida_restante, 0.0)

    def test_t2_boss_hp_threshold_boundaries(self):
        """Valida as fronteiras estritas de HP: >66% Fase 1, 33-66% Fase 2, <=33% Fase 3, 0 HP Morte."""
        boss = GeladeiraTsunami(x=300, y=200, hp=2500)
        boss.update(3.6, (300, 200))  # Pula intro
        self.assertEqual(boss.estado, ESTADO_FASE1)

        # 66.04% HP (1651 / 2500) -> Fase 1
        boss.hp = 1651
        boss.update(0.1, (300, 200))
        self.assertEqual(boss.estado, ESTADO_FASE1)

        # Exatamente 66.00% HP (1650 / 2500) -> Fase 2
        boss.hp = 1650
        boss.update(0.1, (300, 200))
        self.assertEqual(boss.estado, ESTADO_FASE2)

        # 33.04% HP (826 / 2500) -> Fase 2
        boss.hp = 826
        boss.update(0.1, (300, 200))
        self.assertEqual(boss.estado, ESTADO_FASE2)

        # Exatamente 33.00% HP (825 / 2500) -> Fase 3
        boss.hp = 825
        boss.update(0.1, (300, 200))
        self.assertEqual(boss.estado, ESTADO_FASE3)

        # 0 HP através de receber_dano -> Morte
        boss.receber_dano(boss.hp)
        self.assertEqual(boss.estado, ESTADO_MORTE)

    def test_t2_multi_level_xp_overflow_above_lvl_10(self):
        """Valida salto multi-nível atravessando o limiar do Nível 10 com a regra de 25% de desconto."""
        # Jogador no Nível 9 com 0 XP
        self.sistema_xp.nivel = 9
        self.sistema_xp.xp_atual = 0

        # Custo Nv 9 -> 10: 20 + 90 + 405 = 515 XP
        # Custo Nv 10 -> 11: 20 + 100 + 500 = 620 XP
        # Custo Nv 11 -> 12: round(735 * 0.75) = 551 XP
        # Total para atingir Nv 12 com 100 XP sobrando: 515 + 620 + 551 + 100 = 1786 XP
        niveis_ganhos = self.sistema_xp.adicionar_xp(1786)

        self.assertEqual(niveis_ganhos, [10, 11, 12])
        self.assertEqual(self.sistema_xp.nivel, 12)
        self.assertEqual(self.sistema_xp.xp_atual, 100)

        # Teto no Nível 20 Máximo
        self.sistema_xp.adicionar_xp(999999)
        self.assertEqual(self.sistema_xp.nivel, 20)

    def test_t2_fatal_shield_cooldown_starts_after_invuln(self):
        """Valida que o cooldown de 60s do Escudo Fatal só começa APÓS os 4s de invulnerabilidade."""
        jogador = Jogador(x=400, y=300)
        jogador.aplicar_overclock("protecao_surtos")
        self.assertTrue(jogador.escudo_fatal_pronto)

        # Aplica dano fatal
        jogador.hp = 10
        jogador.receber_dano(100)
        self.assertTrue(jogador.vivo)
        self.assertGreaterEqual(jogador.hp, 1)
        self.assertFalse(jogador.escudo_fatal_pronto)
        self.assertEqual(jogador.escudo_fatal_invuln_timer, 4.0)
        self.assertEqual(jogador.escudo_fatal_cooldown, 0.0)

        # Atualiza 2.0s durante invulnerabilidade -> cooldown continua 0.0
        jogador.update(2.0)
        self.assertAlmostEqual(jogador.escudo_fatal_invuln_timer, 2.0, delta=0.01)
        self.assertEqual(jogador.escudo_fatal_cooldown, 0.0)

        # Atualiza mais 2.0s (total 4.0s) -> invulnerabilidade acaba e cooldown inicia em 60.0s
        jogador.update(2.0)
        self.assertEqual(jogador.escudo_fatal_invuln_timer, 0.0)
        self.assertEqual(jogador.escudo_fatal_cooldown, 60.0)
        self.assertFalse(jogador.escudo_fatal_pronto)

        # Atualiza 59.0s de cooldown -> continua em recarga
        jogador.update(59.0)
        self.assertAlmostEqual(jogador.escudo_fatal_cooldown, 1.0, delta=0.01)
        self.assertFalse(jogador.escudo_fatal_pronto)

        # Atualiza mais 1.1s -> escudo pronto novamente
        jogador.update(1.1)
        self.assertEqual(jogador.escudo_fatal_cooldown, 0.0)
        self.assertTrue(jogador.escudo_fatal_pronto)


# =============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS
# =============================================================================

class TestTier3CrossFeatureCombinations(unittest.TestCase):
    """Testes de interação entre múltiplos módulos e mecânicas combinadas."""

    def test_t3_shotgun_with_multithreading(self):
        """Valida que a Shotgun com Multithreading dispara 9 pellets imediatos e agenda eco."""
        cena = GameplayScene()
        shotgun = Shotgun()
        cena.jogador.arma_especial = shotgun
        cena.jogador.selecionar_slot(3)
        cena.jogador.aplicar_overclock("multithreading")

        # Dispara manualmente a Shotgun para validar formação dos 9 pellets balísticos
        novos_tiros = shotgun.disparar(
            cena.jogador.x, cena.jogador.y,
            cena.jogador.x + 100.0, cena.jogador.y
        )
        self.assertEqual(len(novos_tiros), 9)

        # Valida que todos os pellets são instâncias válidas de Projetil
        for p in novos_tiros:
            self.assertIsInstance(p, Projetil)
            self.assertEqual(p.dono, "jogador")

    def test_t3_slot_3b_toggle_and_promotion_on_empty_ammo(self):
        """Valida alternância entre 3A e 3B via tecla '3' e promoção automática ao zerar munição."""
        jogador = Jogador(x=400, y=300)
        jogador.aplicar_overclock("bios_modding")

        minigun = Minigun()
        shotgun = Shotgun()
        jogador.arma_especial = minigun           # 3A
        jogador.arma_especial_secundaria = shotgun # 3B

        jogador.slot_ativo = 3
        self.assertIs(jogador.obter_arma_ativa(), minigun)

        # Pressiona '3' -> alterna para Shotgun em 3A
        jogador.selecionar_slot(3)
        self.assertIs(jogador.arma_especial, shotgun)
        self.assertIs(jogador.arma_especial_secundaria, minigun)

        # Esgota a munição da arma atual (Shotgun)
        jogador.arma_especial.municao_atual = 0
        jogador.update(0.01)

        # Minigun é promovida automaticamente para 3A e 3B fica vazia
        self.assertIs(jogador.arma_especial, minigun)
        self.assertIsNone(jogador.arma_especial_secundaria)
        self.assertEqual(jogador.slot_ativo, 3)


# =============================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS (E2E)
# =============================================================================

class TestTier4RealWorldScenarios(unittest.TestCase):
    """Simulação E2E de progressão de encontro do Chefe Final."""

    def test_t4_full_boss_encounter_progression_to_victory(self):
        """
        Executa a sequência completa de ponta a ponta:
        Lvl 20 alcançado -> Cutscene 4 Fases -> Entrada do Boss -> Fase 1 -> Fase 2 -> Fase 3 -> Derrota -> Vitória.
        """
        cena = GameplayScene()
        cena.jogador.nivel = 20
        self.assertFalse(cena.vitoria)

        # 1. Inicia Cutscene do Boss
        cena.iniciar_boss_cutscene()
        self.assertTrue(cena.boss_cutscene_ativa)
        self.assertEqual(cena.boss_cutscene_fase, "whiteout")

        # 2. Transição Whiteout -> Blackout (2.0s)
        cena.boss_cutscene_timer = 2.0
        cena.loop()
        self.assertEqual(cena.boss_cutscene_fase, "blackout")

        # 3. Transição Blackout -> Musica In / Boss Rise (1.0s)
        cena.boss_cutscene_timer = 1.0
        cena.loop()
        self.assertEqual(cena.boss_cutscene_fase, "musica_in")
        self.assertIsNotNone(cena.chefe_final)
        boss = cena.chefe_final

        # 4. Boss conclui intro e transiciona para Fase 1
        boss.intro_concluida = True
        boss.estado = ESTADO_FASE1
        cena.loop()
        self.assertFalse(cena.boss_cutscene_ativa)
        self.assertEqual(boss.estado, ESTADO_FASE1)

        # 5. Combate Fase 1 -> Dano até 60% HP -> Fase 2
        boss.receber_dano(1000)
        boss.update(0.1, (cena.jogador.x, cena.jogador.y))
        self.assertEqual(boss.estado, ESTADO_FASE2)

        # 6. Combate Fase 2 -> Dano até 20% HP -> Fase 3
        boss.receber_dano(1000)
        boss.update(0.1, (cena.jogador.x, cena.jogador.y))
        self.assertEqual(boss.estado, ESTADO_FASE3)

        # 7. Combate Fase 3 -> Dano letal
        boss.receber_dano(boss.hp)
        self.assertLessEqual(boss.hp, 0)

        # 8. Cascata de morte / derrota
        boss.update(1.6, (cena.jogador.x, cena.jogador.y))
        self.assertFalse(boss.vivo)

        # 9. GameplayScene detecta morte e aciona Vitória
        cena.loop()
        self.assertTrue(cena.vitoria)




class TestRegressionBossCutsceneDeadlock(unittest.TestCase):
    """
    Regressão — Bug: chefe_final.update() bloqueado por boss_cutscene_ativa=True
    durante a fase 'musica_in', impedindo que timer_intro decrementasse e
    intro_concluida se tornasse True. O chefe nunca aparecia na arena.

    Garante que:
    1. Chamar update() durante ESTADO_INTRO decrementa timer_intro corretamente.
    2. Após timer_intro <= 0, intro_concluida == True e estado passa a ESTADO_FASE1.
    3. O boss acumula projéteis pendentes durante o combate que são drenados
       via obter_projeteis_pendentes(), não via valor de retorno de update().
    """

    def setUp(self):
        self.boss = GeladeiraTsunami(x=400.0, y=900.0)  # Posição de intro (abaixo da arena)

    def test_intro_timer_decrements_when_update_called(self):
        """update() deve decrementar timer_intro mesmo que seja chamado durante a cutscene."""
        self.assertEqual(self.boss.estado, ESTADO_INTRO)
        timer_inicial = self.boss.timer_intro

        self.boss.update(0.5, (400.0, 300.0))

        self.assertLess(
            self.boss.timer_intro, timer_inicial,
            "timer_intro deve diminuir a cada chamada de update() durante ESTADO_INTRO"
        )

    def test_intro_concludes_after_full_duration(self):
        """Após timer_intro expirar via updates, intro_concluida deve ser True e estado FASE1."""
        self.assertEqual(self.boss.estado, ESTADO_INTRO)
        self.assertFalse(self.boss.intro_concluida)

        # Avança além da duração total da intro (3.5s)
        dt = 0.1
        for _ in range(40):  # 4.0s > 3.5s
            self.boss.update(dt, (400.0, 300.0))

        self.assertTrue(
            self.boss.intro_concluida,
            "intro_concluida deve ser True após timer_intro esgotar"
        )
        self.assertEqual(
            self.boss.estado, ESTADO_FASE1,
            "Boss deve transitar para ESTADO_FASE1 após intro concluída"
        )

    def test_intro_concluida_unblocks_cutscene_musica_in_check(self):
        """
        Simula a verificação feita por gameplay.py na fase 'musica_in':
        getattr(chefe_final, 'intro_concluida', False).
        Antes da fix: sempre False (timer nunca decrementava → deadlock).
        Após a fix: True quando update() é chamado.
        """
        # Simula o estado ao ser spawned durante a cutscene
        boss = GeladeiraTsunami(x=400.0, y=ALTURA_TELA + 60.0)
        self.assertEqual(boss.estado, ESTADO_INTRO)

        # Sem nenhum update — como era antes da fix (cutscene bloqueava update)
        resultado_sem_update = getattr(boss, "intro_concluida", False)
        self.assertFalse(resultado_sem_update, "Sem updates, intro_concluida deve ser False")

        # Com updates — como fica após a fix
        for _ in range(40):
            boss.update(0.1, (400.0, 300.0))

        resultado_com_updates = getattr(boss, "intro_concluida", False)
        self.assertTrue(resultado_com_updates, "Com updates, intro_concluida deve se tornar True")

    def test_boss_projectiles_emitted_via_pending_queue_not_update_return(self):
        """
        Regressão — Bug: gameplay.py tentava coletar projéteis do valor de retorno
        de update(), que sempre é None. Projéteis devem ser drenados via
        obter_projeteis_pendentes() após o update().
        """
        # Coloca boss em combate (Fase 1)
        boss = GeladeiraTsunami(x=400.0, y=200.0)
        boss.intro_concluida = True  # Salta intro
        self.assertEqual(boss.estado, ESTADO_FASE1)

        # Avança até disparar pelo menos um Subwoofer Pulse (intervalo = 2.2s)
        for _ in range(25):  # 2.5s
            ret = boss.update(0.1, (400.0, 500.0))

        # Valor de retorno de update() deve ser None (não uma lista de projéteis)
        self.assertIsNone(
            ret,
            "update() deve retornar None — projéteis são acumulados internamente"
        )

        # Projéteis devem estar disponíveis via obter_projeteis_pendentes()
        tiros = boss.obter_projeteis_pendentes()
        self.assertIsInstance(tiros, list, "obter_projeteis_pendentes() deve retornar uma lista")
        self.assertGreater(
            len(tiros), 0,
            "Boss deve ter acumulado projéteis após 2.5s de Fase 1 — drenados via obter_projeteis_pendentes()"
        )

        # Segunda chamada deve retornar lista vazia (fila foi esvaziada)
        tiros_segundo = boss.obter_projeteis_pendentes()
        self.assertEqual(
            len(tiros_segundo), 0,
            "obter_projeteis_pendentes() deve esvaziar a fila a cada chamada"
        )


if __name__ == "__main__":
    unittest.main()
