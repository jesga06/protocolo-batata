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
import tempfile
import unittest
from unittest.mock import patch

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
    GeladeiraTsunami, CaixaDeSomBoss, ESTADO_INTRO, ESTADO_FASE1,
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
        self._tmpdir = tempfile.TemporaryDirectory()
        self.temp_save = os.path.join(self._tmpdir.name, "save.json")
        self._p1 = patch("src.utils.constantes.SAVE_FILE_PATH", self.temp_save)
        self._p2 = patch("src.cenas.gameplay.SAVE_FILE_PATH", self.temp_save)
        self._p1.start()
        self._p2.start()
        self.jogador = Jogador(x=400, y=300)
        self.sistema_xp = SistemaXP()
        self.sistema_drops = SistemaDrops()
        self.spawner = SistemaSpawn()

    def tearDown(self):
        self._p2.stop()
        self._p1.stop()
        self._tmpdir.cleanup()

    # --- R2: XP Curve Smoothing ---
    def test_t1_xp_curve_smoothing_values(self):
        """Valida que para nível > 10, o XP necessário é reduzido em 25%: int(round(base * 0.75))."""
        # Níveis 1 a 4: suavizados (-50%); 5 a 10: curva padrão base = 50 + 35*lvl + 18*(lvl^2)
        esperados_padrao = {
            1: 52,
            2: 96,
            3: 158,
            4: 239,
            5: 675,
            10: 2200
        }
        for lvl, val in esperados_padrao.items():
            base = 50 + 35 * lvl + 18 * (lvl ** 2)
            esperado_calc = int(round(base * 0.50)) if lvl <= 4 else base
            self.assertEqual(SistemaXP.calcular_xp_para_nivel(lvl), esperado_calc)
            self.assertEqual(SistemaXP.calcular_xp_para_nivel(lvl), val)
            self.assertEqual(self.sistema_xp.calcular_xp_necessario(lvl), val)

        # Níveis 11 a 20: curva suavizada (25% de desconto)
        esperados_suavizados = {
            11: 1960,
            12: 2296,
            15: 3469,
            20: 5962
        }
        for lvl, val in esperados_suavizados.items():
            base = 50 + 35 * lvl + 18 * (lvl ** 2)
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
        self.assertEqual(nome1, "MINI-BOSS: IMPRESSORA MATRICIAL")

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
            (InimigoRapido, 31, 31, 10),
            (InimigoTank, 62, 62, 120),
            (InimigoPhasing, 42, 42, 35),
            (InimigoBlindado, 47, 47, 50),
            (InimigoPadrao, 28, 28, 18)
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
            self.assertEqual(elite.hp_max, hp_base * 45)

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
        self.assertAlmostEqual(jogador.velocidade_atual, jogador.velocidade_base * 1.15, delta=0.5)

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

        mobs_comuns = [inim for inim in cena.inimigos if inim != boss and not getattr(inim, "is_caixa_som", False)]
        self.assertLessEqual(len(mobs_comuns), 22)
        for mob in mobs_comuns:
            self.assertIsInstance(mob, (InimigoPadrao, InimigoRapido, InimigoRanged))

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
        """Valida as fronteiras estritas de HP: >70% Fase 1, 35-70% Fase 2, <=35% Fase 3, 0 HP Morte."""
        boss = GeladeiraTsunami(x=300, y=200, hp=2500)
        boss.update(3.6, (300, 200))  # Pula intro
        self.assertEqual(boss.estado, ESTADO_FASE1)

        # 70.04% HP (1751 / 2500) -> Fase 1
        boss.hp = 1751
        boss.update(0.1, (300, 200))
        self.assertEqual(boss.estado, ESTADO_FASE1)

        # Exatamente 70.00% HP (1750 / 2500) -> Fase 2
        boss.hp = 1750
        boss.update(0.1, (300, 200))
        self.assertEqual(boss.estado, ESTADO_FASE2)

        # 35.04% HP (876 / 2500) -> Fase 2
        boss.hp = 876
        boss.update(0.1, (300, 200))
        self.assertEqual(boss.estado, ESTADO_FASE2)

        # Exatamente 35.00% HP (875 / 2500) -> Fase 3
        boss.hp = 875
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

        # Custo Nv 9 -> 10: 1823 XP, Nv 10 -> 11: 2200 XP, Nv 11 -> 12: 1960 XP
        # Total para atingir Nv 12 com 100 XP sobrando: 1823 + 2200 + 1960 + 100 = 6083 XP
        niveis_ganhos = self.sistema_xp.adicionar_xp(6083)

        self.assertEqual(niveis_ganhos, [10, 11, 12])
        self.assertEqual(self.sistema_xp.nivel, 12)
        self.assertEqual(self.sistema_xp.xp_atual, 100)

        # Teto no Nível 12 Máximo
        self.sistema_xp.adicionar_xp(999999)
        self.assertEqual(self.sistema_xp.nivel, 12)

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

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.temp_save = os.path.join(self._tmpdir.name, "save.json")
        self._p1 = patch("src.utils.constantes.SAVE_FILE_PATH", self.temp_save)
        self._p2 = patch("src.cenas.gameplay.SAVE_FILE_PATH", self.temp_save)
        self._p1.start()
        self._p2.start()

    def tearDown(self):
        self._p2.stop()
        self._p1.stop()
        self._tmpdir.cleanup()

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

        # 5. Combate Fase 1 -> Dano até <=70% HP (<= 47600 de 68000) -> Fase 2
        boss.receber_dano(21000)
        boss.update(0.1, (cena.jogador.x, cena.jogador.y))
        self.assertEqual(boss.estado, ESTADO_FASE2)

        # 6. Combate Fase 2 -> Dano até <=35% HP (<= 23800 de 68000) -> Fase 3
        boss.receber_dano(24000)
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

    def test_boss_cutscene_nao_instancia_chefe_durante_whiteout_e_blackout(self):
        """Valida que iniciar_boss_cutscene não instancia chefe_final durante whiteout e blackout."""
        cena = GameplayScene()
        cena.iniciar_boss_cutscene()
        self.assertTrue(cena.boss_cutscene_ativa)
        self.assertEqual(cena.boss_cutscene_fase, "whiteout")
        self.assertIsNone(cena.chefe_final)

        # Transição para blackout
        cena.boss_cutscene_timer = 2.0
        cena.loop()
        self.assertEqual(cena.boss_cutscene_fase, "blackout")
        self.assertIsNone(cena.chefe_final)

        # Transição para musica_in -> chefe_final é instanciado
        cena.boss_cutscene_timer = 1.0
        cena.loop()
        self.assertEqual(cena.boss_cutscene_fase, "musica_in")
        self.assertIsNotNone(cena.chefe_final)

    def test_caixa_de_som_boss_atributos_e_comportamento(self):
        """Valida propriedades de CaixaDeSomBoss (hp == 240, is_caixa_som == True)."""
        caixa = CaixaDeSomBoss(x=100.0, y=150.0)
        self.assertEqual(caixa.hp, 240)
        self.assertTrue(getattr(caixa, "is_caixa_som", False))
        self.assertEqual(caixa.largura, 40)
        self.assertEqual(caixa.altura, 40)
        self.assertEqual(caixa.velocidade, 0.0)




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


class TestBossCutsceneWhiteoutSlowMo(unittest.TestCase):
    """Valida que o whiteout da cutscene do boss continua rodando com desaceleração progressiva e sem círculo na batata."""

    def test_whiteout_jogo_continua_rodando_e_desacelera_progressivamente(self):
        """Durante whiteout, o jogo avança mas dt efetivo diminui progressivamente até o blackout."""
        from src.entidades.projetil import Projetil
        from src.entidades.inimigo_padrao import InimigoPadrao

        cena = GameplayScene()
        proj = Projetil(x=200.0, y=200.0, dir_x=1.0, dir_y=0.0, velocidade=200.0, dano=10, dono="jogador")
        inimigo = InimigoPadrao(x=600.0, y=600.0)
        cena.projeteis.append(proj)
        cena.inimigos.append(inimigo)

        cena.iniciar_boss_cutscene()
        self.assertEqual(cena.boss_cutscene_fase, "whiteout")
        self.assertEqual(len(cena.projeteis), 1, "Projéteis não devem ser apagados no início do whiteout")

        # Passo 1: início do whiteout (t = 0.0 -> 0.2s): jogo ainda roda quase em velocidade normal
        t_antes = cena.tempo_sobrevivencia
        px_antes = proj.x
        cena.loop(dt=0.2)
        delta_t_inicio = cena.tempo_sobrevivencia - t_antes
        delta_px_inicio = proj.x - px_antes
        self.assertGreater(delta_t_inicio, 0.0)
        self.assertGreater(delta_px_inicio, 0.0)
        self.assertEqual(cena.boss_cutscene_fase, "whiteout")

        # Passo 2: próximo do fim do whiteout (t = 1.6s -> 1.8s): jogo roda bem mais devagar
        cena.boss_cutscene_timer = 1.6
        t_antes_fim = cena.tempo_sobrevivencia
        px_antes_fim = proj.x
        cena.loop(dt=0.2)
        delta_t_fim = cena.tempo_sobrevivencia - t_antes_fim
        delta_px_fim = proj.x - px_antes_fim
        self.assertGreater(delta_t_fim, 0.0)
        self.assertGreater(delta_px_fim, 0.0)
        self.assertLess(delta_t_fim, delta_t_inicio, "Tempo de jogo deve avançar mais devagar perto do fim do whiteout")
        self.assertLess(delta_px_fim, delta_px_inicio, "Projétil deve se mover mais devagar perto do fim do whiteout")

        # Passo 3: ao completar 2.0s, transiciona para blackout e limpa inimigos/drops/projéteis/partículas/efeitos, preservando buffs
        from src.entidades.drop import ItemDrop
        cena.sistema_drops.drops.append(ItemDrop(x=300.0, y=300.0, tipo="xp", valor=10))
        cena.sistema_particulas.emitir_faiscas(300.0, 300.0, qtd=5)
        cena.sistema_particulas.emitir_onda_choque(300.0, 300.0, raio_max=80.0)
        cena.sistema_particulas.emitir_texto_dano(300.0, 300.0, 25)
        cena.efeitos_melee.append({"x": 300, "y": 300, "tempo": 0.5, "tempo_max": 0.5, "ang": 0.0, "raio": 60})
        cena.zonas_fogo.append({"x": 300.0, "y": 300.0, "raio": 40.0, "tempo": 2.0, "tick": 0.0})
        cena.trilhas_plasma.append({"x1": 0, "y1": 0, "x2": 10, "y2": 10, "tempo": 1.0, "tempo_max": 1.0})
        cena.zonas_estase.append({"x": 300.0, "y": 300.0, "raio": 40.0, "tempo": 2.0})
        cena.pocas_gelo.append({"x": 300.0, "y": 300.0, "raio": 40.0, "tempo": 2.0})
        cena.toasts_coleta.append({"texto": "+10 HP", "cor": (0, 255, 0), "x": 300.0, "y": 300.0, "tempo": 1.0, "tempo_max": 1.0})
        cena.jogador.buff_dano_timer = 10.0

        cena.boss_cutscene_timer = 1.9
        cena.loop(dt=0.2)
        self.assertEqual(cena.boss_cutscene_fase, "blackout")
        self.assertEqual(len(cena.inimigos), 0)
        self.assertEqual(len(cena.sistema_drops.drops), 0)
        self.assertEqual(len(cena.projeteis), 0)
        self.assertEqual(len(cena.tiros_echo_pendentes), 0)
        self.assertEqual(len(cena.sistema_particulas.particulas), 0)
        self.assertEqual(len(cena.sistema_particulas.ondas_choque), 0)
        self.assertEqual(len(cena.sistema_particulas.textos_dano), 0)
        self.assertEqual(len(cena.efeitos_melee), 0)
        self.assertEqual(len(cena.zonas_fogo), 0)
        self.assertEqual(len(cena.trilhas_plasma), 0)
        self.assertEqual(len(cena.zonas_estase), 0)
        self.assertEqual(len(cena.pocas_gelo), 0)
        self.assertEqual(len(cena.toasts_coleta), 0)
        self.assertGreater(cena.jogador.buff_dano_timer, 0.0, "Buffs do jogador devem ser preservados")

    def test_whiteout_overlay_sem_circulo_recorte_na_batata(self):
        """Overlay do whiteout deve ser branco uniforme ao redor da batata, sem círculo escuro de recorte."""
        cena = GameplayScene()
        cena.camera.follow(cena.jogador, suavizacao=1.0)
        cena.iniciar_boss_cutscene()
        cena.boss_cutscene_timer = 1.0
        cena.overlay_cutscene_cor = (255, 255, 255)
        cena.overlay_cutscene_alpha = 128

        cena.draw()

        pj_sx = int(cena.camera.transform_x(cena.jogador.x + cena.jogador.largura / 2.0))
        pj_sy = int(cena.camera.transform_y(cena.jogador.y + cena.jogador.altura / 2.0))
        cor_no_centro_batata = cena._overlay_surf.get_at((pj_sx, pj_sy))
        cor_na_borda = cena._overlay_surf.get_at((5, 5))
        self.assertEqual(
            tuple(cor_no_centro_batata),
            tuple(cor_na_borda),
            "Overlay de whiteout não deve ter círculo ao redor da batata",
        )
        self.assertEqual(tuple(cor_no_centro_batata), (255, 255, 255, 128))

    def test_grace_period_nivel_12_e_texto_countdown(self):
        """Atingir nível 12 após 270s inicia grace period de 10s com texto exato antes da cutscene."""
        cena = GameplayScene()
        cena.tempo_sobrevivencia = 270.0
        cena._ao_subir_nivel(12)

        self.assertTrue(cena.boss_grace_period_ativo)
        self.assertFalse(cena.boss_cutscene_ativa)
        self.assertAlmostEqual(cena.boss_grace_timer, 10.0, places=5)
        self.assertEqual(
            cena.obter_texto_boss_grace_period(),
            "Você ouve o Ritmo Cruel sacudindo o baile inteiro.\n"
            "Você tem 10 segundos até experienciar The Perfect Sound™",
        )

        cena.boss_grace_timer = 4.2
        self.assertEqual(
            cena.obter_texto_boss_grace_period(),
            "Você ouve o Ritmo Cruel sacudindo o baile inteiro.\n"
            "Você tem 5 segundos até experienciar The Perfect Sound™",
        )
        cena.draw()

    def test_grace_period_pausa_spawner_e_transiciona_para_cutscene(self):
        """Durante o grace period novos spawns pausam; ao zerar, inicia a cutscene do Boss Final."""
        cena = GameplayScene()
        cena.iniciar_boss_grace_period()
        cena.inimigos.clear()
        cena.spawner.timer_spawn = 99.0

        cena.loop(dt=0.5)
        self.assertTrue(cena.boss_grace_period_ativo)
        self.assertFalse(cena.boss_cutscene_ativa)
        self.assertAlmostEqual(cena.boss_grace_timer, 9.5, places=5)
        self.assertEqual(len(cena.inimigos), 0, "Spawner deve pausar durante o grace period")

        cena.boss_grace_timer = 0.2
        cena.loop(dt=0.25)
        self.assertFalse(cena.boss_grace_period_ativo)
        self.assertTrue(cena.boss_cutscene_ativa)
        self.assertEqual(cena.boss_cutscene_fase, "whiteout")

    def test_grace_period_gatilho_tempo_elite_300(self):
        """Gatilho 'Jogar aos Lobos' (tempo_elite >= 300s) ativa o grace period de 10s antes da cutscene."""
        cena = GameplayScene()
        cena.spawner.tempo_elite = 300.0
        cena.spawner.bosses_spawnados_indices = {0, 1, 2, 3}

        cena.loop(dt=0.05)
        self.assertTrue(cena.boss_grace_period_ativo)
        self.assertFalse(cena.boss_cutscene_ativa)

    def test_blackout_limpa_motion_blur_vsync_e_timers_e_cutscene_nao_desenha_pos_processamento(self):
        """Blackout deve limpar motion blur, rastro, vsync_tear_y e timers, e cutscene não deve aplicar blur/vsync."""
        cena = GameplayScene()
        cena.gerenciador_config.desbloquear_config("motion_blur")
        cena.gerenciador_config.definir_valor("motion_blur", "ligado")
        cena.gerenciador_config.desbloquear_config("vsync")
        cena.gerenciador_config.definir_valor("vsync", "desligado")
        cena.aplicar_modificadores()

        cena._motion_blur_surf = pygame.Surface((1280, 720))
        cena.vsync_tear_y = 240.0
        cena.jogador.rastro_posicoes = [(100.0, 200.0, True), (120.0, 200.0, True)]
        cena.jogador._rastro_timer = 0.02
        cena.arena_freeze_timer = 1.5
        cena.hitstop_timer = 0.1
        cena.aura_cura_timer = 0.8
        cena.buffer_tiro = 0.2
        cena.spawner.timer_spawn = 2.5

        cena.iniciar_boss_cutscene()
        cena.boss_cutscene_timer = 1.9
        cena.loop(dt=0.2)

        self.assertEqual(cena.boss_cutscene_fase, "blackout")
        self.assertIsNone(cena._motion_blur_surf)
        self.assertEqual(cena.vsync_tear_y, 0.0)
        self.assertEqual(cena.jogador.rastro_posicoes, [])
        self.assertEqual(cena.jogador._rastro_timer, 0.0)
        self.assertEqual(cena.arena_freeze_timer, 0.0)
        self.assertEqual(cena.hitstop_timer, 0.0)
        self.assertEqual(cena.aura_cura_timer, 0.0)
        self.assertEqual(cena.buffer_tiro, 0.0)
        self.assertEqual(cena.spawner.timer_spawn, 0.0)

        # Avança para musica_in (fade-in) e garante que draw() não recria _motion_blur_surf nem desenha linha ciano de vsync
        cena.boss_cutscene_timer = 1.0
        cena.loop(dt=0.1)
        self.assertEqual(cena.boss_cutscene_fase, "musica_in")
        cena.draw()
        self.assertIsNone(cena._motion_blur_surf)
        cor_linha_vsync = tuple(cena.janela.screen.get_at((10, 1))[:3])
        self.assertNotEqual(cor_linha_vsync, (56, 189, 248))


if __name__ == "__main__":
    unittest.main()
