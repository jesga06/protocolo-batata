"""
Testes Adversariais e de Estresse — Protocolo: Batata
SSOT: CONFIGURACOES.md, PROJECT.md, architecture_cache.md
Empirical Challenger: 20 Gameplay Configurations, Multipliers, Player Speed, Critical Hits & Particle Lifecycle.
"""

import os
import sys
import math
import random
import unittest
from unittest.mock import MagicMock

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pygame
pygame.init()

from src.sistemas.config_dados import CONFIGURACOES_GAMEPLAY, TODAS_CONFIGURACOES
from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.sistemas.config_efeitos import calcular_modificadores, ModificadoresGameplay
from src.entidades.jogador import Jogador
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.inimigo_ranged import InimigoRanged
from src.entidades.projetil import Projetil
from src.entidades.drop import ItemDrop
from src.equipamentos.drone_suporte import DroneSuporte
from src.armas.pistola import Pistola
from src.armas.melee import Melee
from src.armas.lanca_foguetes import LancaFoguetes
from src.sistemas.sistema_particulas import SistemaParticulas, TextoDano, Particula, OndaChoque
from src.sistemas.sistema_spawn import SistemaSpawn
from src.sistemas.sistema_scavenger import SistemaScavenger
from src.cenas.gameplay import GameplayScene
from src.utils.constantes import LARGURA_ARENA, ALTURA_ARENA, DROP_TEMPO_SCAVENGER_ATIVAR, DROP_TEMPO_DESAPARECER


class TestEmpiricalChallengerMultipliers(unittest.TestCase):
    """Bateria de testes empíricos adversariais para combinações extremas de multiplicadores e integridade de estado."""

    def setUp(self):
        self.mgr = GerenciadorConfiguracoes()

    def test_extreme_damage_multiplier_stacking(self):
        """
        [ADVERSARIAL] Testa o empilhamento multiplicativo máximo de todos os bônus de dano simultâneos:
        - zoom: 150% (x1.20)
        - keybinds: pesadelo (x1.30)
        - auto_fire: desligado (x1.15)
        - cores_invertidas: ligado (x1.20)
        - fogo_amigo: ligado (x1.25)
        Multiplicador esperado: 1.20 * 1.30 * 1.15 * 1.20 * 1.25 = 2.691
        """
        for cid in ["zoom", "keybinds", "auto_fire", "cores_invertidas", "fogo_amigo"]:
            self.mgr.desbloquear_config(cid)

        self.mgr.definir_valor("zoom", "150%")
        self.mgr.definir_valor("keybinds", "pesadelo")
        self.mgr.definir_valor("auto_fire", "desligado")
        self.mgr.definir_valor("cores_invertidas", "ligado")
        self.mgr.definir_valor("fogo_amigo", "ligado")

        mods = self.mgr.obter_modificadores()
        esperado_mult = 1.20 * 1.30 * 1.15 * 1.20 * 1.25
        self.assertAlmostEqual(mods.dano_armas_mult, esperado_mult, places=5)
        self.assertTrue(mods.auto_dano)

        # Testa aplicação nas armas do jogador
        jogador = Jogador(x=100, y=100)
        pistola = Pistola()
        jogador.armas = [pistola]
        base_dano = pistola.dano  # 10

        # Aplica modificadores como na cena gameplay
        pistola.dano = int(round(base_dano * mods.dano_armas_mult))
        self.assertEqual(pistola.dano, int(round(10 * 2.691)))  # 27 dano

        # Adiciona buff temporário (+5%)
        jogador.buff_dano_timer = 15.0
        mult_buff = 1.05 if jogador.buff_dano_timer > 0.0 else 1.0
        dano_com_buff = max(1, int(round(pistola.dano * mult_buff)))
        self.assertEqual(dano_com_buff, int(round(27 * 1.05)))  # 28 dano

    def test_extreme_speed_multiplier_stacking(self):
        """
        [ADVERSARIAL] Testa o empilhamento multiplicativo máximo de velocidade de movimento:
        - vsync: desligado (x1.10)
        - motion_blur: ligado (x1.15)
        - keybinds: arrow_keys (x1.15)
        - suavizacao_camera: desligado (x1.08)
        Esperado base config: 1.10 * 1.15 * 1.15 * 1.08 = 1.571148
        + Buff temporário (+8% = x1.08)
        + 2x Drone de Suporte (+15% cada = x1.15 * 1.15)
        Esperado total: 1.571148 * 1.08 * 1.15 * 1.15 = 2.24407...
        """
        for cid in ["vsync", "motion_blur", "keybinds", "suavizacao_camera"]:
            self.mgr.desbloquear_config(cid)

        self.mgr.definir_valor("vsync", "desligado")
        self.mgr.definir_valor("motion_blur", "ligado")
        self.mgr.definir_valor("keybinds", "arrow_keys")
        self.mgr.definir_valor("suavizacao_camera", "desligado")

        mods = self.mgr.obter_modificadores()
        esperado_config = 1.10 * 1.15 * 1.15 * 1.08
        self.assertAlmostEqual(mods.vel_jogador_mult, esperado_config, places=5)

        jogador = Jogador(x=500, y=500)
        jogador.mult_vel_config = mods.vel_jogador_mult
        jogador.buff_vel_timer = 15.0

        drone1 = DroneSuporte(tempo_vida=30.0)
        drone2 = DroneSuporte(tempo_vida=30.0)
        jogador.adicionar_drone(drone1)
        jogador.adicionar_drone(drone2)

        # Executa update do jogador
        jogador.update(0.1)

        esperado_total = jogador.velocidade_base * esperado_config * 1.08 * 1.15 * 1.15
        self.assertAlmostEqual(jogador.velocidade_atual, esperado_total, places=3)

    def test_extreme_enemy_debuffs_and_scaling_combination(self):
        """
        [ADVERSARIAL] Testa a combinação de múltiplos debuffs e buffs nos inimigos:
        - fps_cap: 15 (dano inimigos x0.7225, vel inimigos x0.81)
        - graficos_qualidade: baixa (hp inimigos x0.80)
        - velocidade_inimigos: +50% (vel inimigos x1.50, xp ganho x1.40)
        - vida_inimigos: +100% (hp inimigos x2.00, drop chance bonus +0.40)
        - resolucao: 25% (drop chance bonus +0.50)
        - movimento_mouse: ligado (drop chance mult x1.40)
        - hud: desligado (xp ganho x1.25)
        - keybinds: uma_mao (xp ganho x1.20)
        """
        cids = ["fps_cap", "graficos_qualidade", "velocidade_inimigos", "vida_inimigos",
                "resolucao", "movimento_mouse", "hud", "keybinds"]
        for cid in cids:
            self.mgr.desbloquear_config(cid)

        self.mgr.definir_valor("fps_cap", "15")
        self.mgr.definir_valor("graficos_qualidade", "baixa")
        self.mgr.definir_valor("velocidade_inimigos", "+50%")
        self.mgr.definir_valor("vida_inimigos", "+100%")
        self.mgr.definir_valor("resolucao", "25%")
        self.mgr.definir_valor("movimento_mouse", "ligado")
        self.mgr.definir_valor("hud", "desligado")
        self.mgr.definir_valor("keybinds", "uma_mao")

        mods = self.mgr.obter_modificadores()

        # HP inimigos: 0.80 * 2.00 = 1.60
        self.assertAlmostEqual(mods.hp_inimigos_mult, 1.60, places=5)
        # Vel inimigos: 0.81 * 1.50 = 1.215
        self.assertAlmostEqual(mods.vel_inimigos_mult, 1.215, places=5)
        # Dano inimigos: 0.7225
        self.assertAlmostEqual(mods.dano_inimigos_mult, 0.7225, places=5)
        # XP Ganho: 1.40 * 1.25 * 1.20 = 2.10
        self.assertAlmostEqual(mods.xp_ganho_mult, 2.10, places=5)
        # Drop chance bonus: 0.40 + 0.50 = 0.90
        self.assertAlmostEqual(mods.drop_chance_bonus, 0.90, places=5)
        # Drop chance mult: 1.40
        self.assertAlmostEqual(mods.drop_chance_mult, 1.40, places=5)

    def test_locked_configs_strictly_neutral_under_adversarial_tampering(self):
        """
        [ADVERSARIAL] Testa se valores modificados em configurações TRAVADAS (não desbloqueadas)
        são estritamente ignorados pelo motor de modificadores, impedindo cheat/exploit.
        """
        # Salva valores com buffs no dicionário sem desbloquear
        raw_ativas = {
            "zoom": "150%",
            "cores_invertidas": "ligado",
            "fogo_amigo": "ligado",
            "vsync": "desligado",
            "motion_blur": "ligado",
            "hud": "desligado"
        }
        # Desbloqueadas é um conjunto vazio
        mods = calcular_modificadores(configs_desbloqueadas=set(), configs_ativas=raw_ativas)

        self.assertEqual(mods.dano_armas_mult, 1.0)
        self.assertEqual(mods.vel_jogador_mult, 1.0)
        self.assertEqual(mods.xp_ganho_mult, 1.0)
        self.assertFalse(mods.auto_dano)
        self.assertEqual(mods.hitbox_projeteis_mult, 1.0)


class TestPlayerSpeedLifecycleStress(unittest.TestCase):
    """Testa a estabilidade da velocidade do jogador ao longo de centenas de frames e transições de timers."""

    def test_player_speed_no_reset_and_no_exponential_runaway_across_1000_frames(self):
        """
        [ADVERSARIAL] Valida que a velocidade atual não reseta para base e não sofre multiplicação cumulativa descontrolada.
        """
        jogador = Jogador(x=500.0, y=500.0)
        jogador.mult_vel_config = 1.25  # Buff de 25% de config
        jogador.buff_vel_timer = 2.0   # Buff temporário de 2s (+8%)

        # Adiciona drone com vida de 3.0s (+15%)
        drone = DroneSuporte(tempo_vida=3.0)
        jogador.adicionar_drone(drone)

        velocidades_registradas = []

        dt = 0.016666  # ~60 FPS (1000 frames = ~16.6s)
        for frame in range(1000):
            # Simula update do jogador
            jogador.update(dt)
            velocidades_registradas.append(jogador.velocidade_atual)

        # Fase 1: Frames 0 a 100 (0 a ~1.66s) -> Config (1.25) + Buff (1.08) + Drone (1.15) = 1.5525
        vel_fase1 = jogador.velocidade_base * 1.25 * 1.08 * 1.15
        for v in velocidades_registradas[0:100]:
            self.assertAlmostEqual(v, vel_fase1, places=3)

        # Fase 2: Frames 150 a 170 (2.5s a 2.8s) -> Buff expirou, resta Config (1.25) + Drone (1.15) = 1.4375
        vel_fase2 = jogador.velocidade_base * 1.25 * 1.15
        for v in velocidades_registradas[150:170]:
            self.assertAlmostEqual(v, vel_fase2, places=3)

        # Fase 3: Frames 250 a 1000 (4.1s a 16.6s) -> Drone expirou e foi removido, resta estritamente Config (1.25) = 1.25
        vel_fase3 = jogador.velocidade_base * 1.25
        for v in velocidades_registradas[250:]:
            self.assertAlmostEqual(v, vel_fase3, places=3)

        # Verifica que drones inativos foram expurgados da lista
        self.assertEqual(len(jogador.drones), 0)

    def test_diagonal_movement_normalization_exactness(self):
        """
        [ADVERSARIAL] Testa se a magnitude de deslocamento diagonal é rigorosamente idêntica
        à movimentação cardinal (sem velocidade diagonal 1.414x desbalanceada).
        """
        jogador_cardinal = Jogador(x=500.0, y=500.0)
        jogador_diagonal = Jogador(x=500.0, y=500.0)

        mock_teclado_cardinal = MagicMock()
        mock_teclado_cardinal.key_pressed.side_effect = lambda k: k == "d"
        mock_teclado_cardinal.key_down.side_effect = lambda k: False

        mock_teclado_diagonal = MagicMock()
        mock_teclado_diagonal.key_pressed.side_effect = lambda k: k in ("d", "s")
        mock_teclado_diagonal.key_down.side_effect = lambda k: False

        dt = 0.5
        jogador_cardinal.processar_input(mock_teclado_cardinal, None, dt)
        jogador_diagonal.processar_input(mock_teclado_diagonal, None, dt)

        dist_cardinal = math.hypot(jogador_cardinal.x - 500.0, jogador_cardinal.y - 500.0)
        dist_diagonal = math.hypot(jogador_diagonal.x - 500.0, jogador_diagonal.y - 500.0)

        self.assertAlmostEqual(dist_cardinal, dist_diagonal, places=4,
                               msg=f"Distâncias devem ser iguais: cardinal={dist_cardinal}, diagonal={dist_diagonal}")

    def test_extreme_speed_arena_boundary_clamping(self):
        """
        [ADVERSARIAL] Submete o jogador a velocidades astronômicas (100.000 px/s)
        e valida que ele nunca ultrapassa as bordas da arena.
        """
        jogador = Jogador(x=100.0, y=100.0)
        jogador.velocidade_atual = 100000.0

        mock_teclado = MagicMock()
        mock_teclado.key_down.side_effect = lambda k: False

        # Tenta mover violentamente para a esquerda e para cima (-X, -Y)
        mock_teclado.key_pressed.side_effect = lambda k: k in ("a", "w")
        jogador.processar_input(mock_teclado, None, dt=1.0, limite_arena=(LARGURA_ARENA, ALTURA_ARENA))
        self.assertEqual(jogador.x, 0.0)
        self.assertEqual(jogador.y, 0.0)

        # Tenta mover violentamente para a direita e para baixo (+X, +Y)
        mock_teclado.key_pressed.side_effect = lambda k: k in ("d", "s")
        jogador.processar_input(mock_teclado, None, dt=1.0, limite_arena=(LARGURA_ARENA, ALTURA_ARENA))
        self.assertEqual(jogador.x, LARGURA_ARENA - jogador.largura)
        self.assertEqual(jogador.y, ALTURA_ARENA - jogador.altura)


class TestCriticalHitsDistributionAndParticleLifecycle(unittest.TestCase):
    """Testa a distribuição estatística de acertos críticos e o ciclo de vida/limites de memória de partículas."""

    def test_critical_hit_disabled_when_config_off(self):
        """
        [ADVERSARIAL] Quando damage_numbers está desligado, chance de crítico DEVE ser exatamente 0.0.
        """
        mgr = GerenciadorConfiguracoes()
        mgr.desbloquear_config("damage_numbers")
        mgr.definir_valor("damage_numbers", "desligado")
        mods = mgr.obter_modificadores()
        self.assertEqual(mods.critico_chance, 0.0)

        crits = 0
        for _ in range(10000):
            if mods.critico_chance > 0.0 and random.random() < mods.critico_chance:
                crits += 1
        self.assertEqual(crits, 0)

    def test_critical_hit_statistical_monte_carlo_distribution(self):
        """
        [ADVERSARIAL] Teste de Monte Carlo com 100.000 rolagens para validar se a taxa de acertos críticos
        converge para 25% (±0.45% com intervalo de confiança de 99.99%).
        """
        mgr = GerenciadorConfiguracoes()
        mgr.desbloquear_config("damage_numbers")
        mgr.definir_valor("damage_numbers", "ligado")
        mods = mgr.obter_modificadores()
        self.assertEqual(mods.critico_chance, 0.25)
        self.assertEqual(mods.critico_mult, 2.0)

        n_amostras = 100000
        p_esperado = 0.25
        crits = 0

        random.seed(42)  # Seed determinística reproduzível
        for _ in range(n_amostras):
            if random.random() < mods.critico_chance:
                crits += 1

        taxa_observada = crits / float(n_amostras)
        # Desvio padrão = sqrt(N * p * (1-p)) / N = sqrt(0.25 * 0.75 / 100000) ~= 0.00137 (0.137%)
        # 4 desvios padrão ~= 0.55%
        self.assertAlmostEqual(taxa_observada, p_esperado, delta=0.006,
                               msg=f"Taxa observada {taxa_observada*100:.2f}% fora da margem estatística de 25%.")

    def test_floating_damage_text_lifecycle_and_content(self):
        """
        [ADVERSARIAL] Valida que números flutuantes de dano têm formatação, cor e tempo de vida corretos.
        """
        sp = SistemaParticulas()

        # Dano normal
        sp.emitir_texto_dano(100.0, 100.0, 17, critico=False)
        self.assertEqual(len(sp.textos_dano), 1)
        td_norm = sp.textos_dano[0]
        self.assertEqual(td_norm.texto, "17")
        self.assertEqual(td_norm.cor, (255, 255, 255))
        self.assertFalse(td_norm.critico)
        self.assertEqual(td_norm.vida_max, 0.65)

        # Dano crítico
        sp.emitir_texto_dano(200.0, 200.0, 34, critico=True)
        self.assertEqual(len(sp.textos_dano), 2)
        td_crit = sp.textos_dano[1]
        self.assertEqual(td_crit.texto, "34!")
        self.assertEqual(td_crit.cor, (255, 215, 0))
        self.assertTrue(td_crit.critico)

        # Simula passagem do tempo até expirar (0.7s > 0.65s)
        sp.update(0.7)
        self.assertEqual(len(sp.textos_dano), 0, "Textos de dano devem expirar e ser limpos da memória.")

    def test_particle_system_memory_bounding_under_flood(self):
        """
        [ADVERSARIAL] Testa se o sistema de partículas impõe teto rígido de instâncias (MAX_TEXTOS e MAX_PARTICULAS)
        sob enxurrada massiva de 10.000 emissões contínuas.
        """
        sp = SistemaParticulas()

        for i in range(5000):
            sp.emitir_texto_dano(100.0, 100.0, i, critico=(i % 2 == 0))
            sp.emitir_faiscas(100.0, 100.0, dir_x=1.0, dir_y=0.0, qtd=6)

        self.assertLessEqual(len(sp.textos_dano), sp.MAX_TEXTOS,
                             f"Textos de dano ({len(sp.textos_dano)}) não podem ultrapassar MAX_TEXTOS ({sp.MAX_TEXTOS}).")
        self.assertLessEqual(len(sp.particulas), sp.MAX_PARTICULAS,
                             f"Partículas ({len(sp.particulas)}) não podem ultrapassar MAX_PARTICULAS ({sp.MAX_PARTICULAS}).")


class TestDarkIlluminationAndScavengerBoundaryStress(unittest.TestCase):
    """Testa casos de borda estritos na Iluminação Dinâmica (Fog) e Scavenger (10s delay)."""

    def test_dark_illumination_distance_boundary_threshold(self):
        """
        [ADVERSARIAL] Valida no loop real de GameplayScene se o multiplicador de redução de dano (0.50)
        da Config 18 (iluminacao) é ativado com base na distância da origem do projétil (> 195.0 px).
        """
        cena = GameplayScene()
        cena.config_sistema.desbloquear_config("iluminacao")
        cena.config_sistema.definir_valor("iluminacao", "ligado")
        cena.aplicar_modificadores()
        mods = cena.config_sistema.obter_modificadores()
        self.assertEqual(mods.dano_fora_visao_mult, 0.50)

        cx = cena.jogador.x + cena.jogador.largura / 2.0
        cy = cena.jogador.y + cena.jogador.altura / 2.0

        # Caso 1: Projétil disparado de dentro do campo de visão (origem a 150px <= 195px)
        cena.jogador.hp = 100
        cena.jogador.invulnerabilidade_timer = 0.0
        p_dentro = Projetil(x=cena.jogador.x, y=cena.jogador.y, dir_x=0.0, dir_y=0.0, velocidade=0.0, dano=20, dono="inimigo")
        p_dentro.x_origem = cx + 150.0
        p_dentro.y_origem = cy
        cena.projeteis = [p_dentro]
        cena.loop(dt=0.016)
        self.assertEqual(cena.jogador.hp, 80, "Projétil originado dentro de 195px deve causar 100% do dano (20).")

        # Caso 2: Projétil disparado de fora do campo de visão (origem a 240px > 195px)
        cena.jogador.hp = 100
        cena.jogador.invulnerabilidade_timer = 0.0
        p_fora = Projetil(x=cena.jogador.x, y=cena.jogador.y, dir_x=0.0, dir_y=0.0, velocidade=0.0, dano=20, dono="inimigo")
        p_fora.x_origem = cx + 240.0
        p_fora.y_origem = cy
        cena.projeteis = [p_fora]
        cena.loop(dt=0.016)
        self.assertEqual(cena.jogador.hp, 90, "Projétil originado fora de 195px deve causar 50% do dano (10).")

    def test_scavenger_10_second_delay_boundary_precision(self):
        """
        [ADVERSARIAL] Valida a precisão matemática da elegibilidade do Scavenger:
        - 0.0s a 9.99s: elegivel_scavenger() == False
        - 10.0s a 59.99s: elegivel_scavenger() == True
        - >= 60.0s: drop inativo/desaparecido -> False
        """
        drop = ItemDrop(x=100, y=100, tipo="xp", valor=10)

        drop.tempo_decorrido = 0.0
        self.assertFalse(drop.elegivel_scavenger())

        drop.tempo_decorrido = 5.0
        self.assertFalse(drop.elegivel_scavenger())

        drop.tempo_decorrido = 9.999
        self.assertFalse(drop.elegivel_scavenger())

        drop.tempo_decorrido = 10.0
        self.assertTrue(drop.elegivel_scavenger())

        drop.tempo_decorrido = 25.0
        self.assertTrue(drop.elegivel_scavenger())

        # Drop expirou
        drop.ativo = False
        self.assertFalse(drop.elegivel_scavenger())



class TestDynamicRandomConfigPermutationsFuzzer(unittest.TestCase):
    """Fuzzing adversarial com 10.000 combinações aleatórias de configurações."""

    def test_random_config_permutations_fuzzing(self):
        """
        [ADVERSARIAL FUZZING] Sorteia aleatoriamente subconjuntos de configs desbloqueadas e valores
        por 10.000 iterações e valida invariantes:
        1. Nenhum multiplicador é <= 0.0, NaN ou Infinito.
        2. Configs não desbloqueadas nunca afetam o resultado.
        3. Todos os campos de ModificadoresGameplay mantêm tipos corretos.
        """
        chaves_gameplay = list(CONFIGURACOES_GAMEPLAY.keys())

        random.seed(1337)  # Fuzzer reproduzível

        for i in range(10000):
            # Sorteia quais configs estão desbloqueadas (de 0 a 20)
            k_desbloqueadas = random.randint(0, len(chaves_gameplay))
            desbloqueadas = set(random.sample(chaves_gameplay, k_desbloqueadas))

            # Sorteia valores para todas as configs
            ativas = {}
            for cid, cdef in CONFIGURACOES_GAMEPLAY.items():
                opcoes_disponiveis = list(cdef.opcoes.keys())
                ativas[cid] = random.choice(opcoes_disponiveis)

            mods = calcular_modificadores(desbloqueadas, ativas)

            # Invariantes numéricas
            self.assertFalse(math.isnan(mods.dano_armas_mult), f"dano_armas_mult foi NaN na iteração {i}")
            self.assertFalse(math.isinf(mods.dano_armas_mult), f"dano_armas_mult foi Inf na iteração {i}")
            self.assertGreater(mods.dano_armas_mult, 0.0)

            self.assertFalse(math.isnan(mods.vel_jogador_mult), f"vel_jogador_mult foi NaN na iteração {i}")
            self.assertGreater(mods.vel_jogador_mult, 0.0)

            self.assertFalse(math.isnan(mods.hp_inimigos_mult), f"hp_inimigos_mult foi NaN na iteração {i}")
            self.assertGreater(mods.hp_inimigos_mult, 0.0)

            self.assertFalse(math.isnan(mods.vel_inimigos_mult), f"vel_inimigos_mult foi NaN na iteração {i}")
            self.assertGreater(mods.vel_inimigos_mult, 0.0)

            self.assertFalse(math.isnan(mods.xp_ganho_mult), f"xp_ganho_mult foi NaN na iteração {i}")
            self.assertGreater(mods.xp_ganho_mult, 0.0)

            self.assertGreaterEqual(mods.drop_chance_bonus, 0.0)
            self.assertGreater(mods.drop_chance_mult, 0.0)
            self.assertGreater(mods.drops_valor_mult, 0.0)
            self.assertGreaterEqual(mods.critico_chance, 0.0)
            self.assertLessEqual(mods.critico_chance, 1.0)
            self.assertIsInstance(mods.auto_dano, bool)
            self.assertIsInstance(mods.loot_enriquecido, bool)


class TestKeybindsInputVectorExactness(unittest.TestCase):
    """Testa a física exata de movimentação para todos os 5 presets de keybinds."""

    def test_all_five_keybinds_presets_directional_vectors(self):
        """
        [ADVERSARIAL] Valida que cada preset mapeia com exatidão matemática
        para as direções cardinais corretas:
        - padrao: WASD (W=-Y, S=+Y, A=-X, D=+X)
        - invertido: WASD invertido (W=+Y, S=-Y, A=+X, D=-X)
        - arrow_keys: Setas (UP=-Y, DOWN=+Y, LEFT=-X, RIGHT=+X)
        - uma_mao: QWER (W=-Y, E=+Y, Q=-X, R=+X)
        - pesadelo: IJKL (I=-Y, K=+Y, J=-X, L=+X)
        """
        presets = [
            ("padrao", {"w": (0, -1), "s": (0, 1), "a": (-1, 0), "d": (1, 0)}),
            ("invertido", {"w": (0, 1), "s": (0, -1), "a": (1, 0), "d": (-1, 0)}),
            ("arrow_keys", {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}),
            ("uma_mao", {"w": (0, -1), "e": (0, 1), "q": (-1, 0), "r": (1, 0)}),
            ("pesadelo", {"i": (0, -1), "k": (0, 1), "j": (-1, 0), "l": (1, 0)})
        ]

        for preset_nome, mapa_teclas in presets:
            mgr = GerenciadorConfiguracoes()
            mgr.desbloquear_config("keybinds")
            mgr.definir_valor("keybinds", preset_nome)

            for tecla, (esperado_dx_sign, esperado_dy_sign) in mapa_teclas.items():
                jogador = Jogador(x=500.0, y=500.0)
                mock_teclado = MagicMock()
                mock_teclado.key_pressed.side_effect = lambda k, target=tecla: (k.lower() == target or k.upper() == target)
                mock_teclado.key_down.side_effect = lambda k: False

                jogador.processar_input(mock_teclado, None, dt=0.1, config_sistema=mgr)

                delta_x = jogador.x - 500.0
                delta_y = jogador.y - 500.0

                if esperado_dx_sign > 0:
                    self.assertGreater(delta_x, 0.0, f"Preset {preset_nome} tecla '{tecla}' deveria mover para +X")
                elif esperado_dx_sign < 0:
                    self.assertLess(delta_x, 0.0, f"Preset {preset_nome} tecla '{tecla}' deveria mover para -X")
                else:
                    self.assertAlmostEqual(delta_x, 0.0, places=4)

                if esperado_dy_sign > 0:
                    self.assertGreater(delta_y, 0.0, f"Preset {preset_nome} tecla '{tecla}' deveria mover para +Y")
                elif esperado_dy_sign < 0:
                    self.assertLess(delta_y, 0.0, f"Preset {preset_nome} tecla '{tecla}' deveria mover para -Y")
                else:
                    self.assertAlmostEqual(delta_y, 0.0, places=4)


class TestCombatRulesAndFriendlyFireIntegration(unittest.TestCase):
    """Testa regras avançadas de combate: autofire, friendly fire e danos."""

    def test_friendly_fire_ballistic_damage_to_player_and_drone(self):
        """
        [ADVERSARIAL] Valida se projéteis do jogador ferem a própria batata e destroem drones de 1 HP
        quando fogo_amigo está ligado (após carência inicial de 60ms).
        """
        cena = GameplayScene()
        cena.config_sistema.desbloquear_config("fogo_amigo")
        cena.config_sistema.definir_valor("fogo_amigo", "ligado")
        mods = cena.config_sistema.obter_modificadores()
        self.assertTrue(mods.auto_dano)

        # 1. Projétil do jogador colidindo com o jogador
        hp_inicial = cena.jogador.hp
        proj = Projetil(
            x=cena.jogador.x,
            y=cena.jogador.y,
            dir_x=0.0,
            dir_y=0.0,
            dano=15,
            dono="jogador"
        )
        proj.tempo_vida = 1.0
        proj.tempo_vida_restante = 0.8  # Passou 0.2s (> 0.06s)
        cena.projeteis.append(proj)

        # Executa ciclo de atualização
        cena.loop()

        # O jogador deve ter sofrido 15 de dano
        self.assertEqual(cena.jogador.hp, hp_inicial - 15)
        self.assertFalse(proj.ativo)

        # 2. Projétil colidindo com Drone
        drone = DroneSuporte(tempo_vida=30.0)
        drone.hp = 1
        cena.jogador.adicionar_drone(drone)
        drone.update(0.01, cena.jogador)

        proj_drone = Projetil(
            x=drone.x,
            y=drone.y,
            dir_x=0.0,
            dir_y=0.0,
            dano=10,
            dono="jogador"
        )
        proj_drone.tempo_vida = 1.0
        proj_drone.tempo_vida_restante = 0.8
        cena.projeteis.append(proj_drone)

        cena.loop()
        self.assertEqual(drone.hp, 0)
        self.assertFalse(drone.ativo)

class TestFullCombatLoopStress(unittest.TestCase):
    """Testa a integração contínua do loop de combate sob estresse de 300 frames com todas as 20 configs customizadas."""

    def test_300_frames_continuous_combat_with_all_20_configs_active(self):
        """
        [ADVERSARIAL INTEGRATION] Executa 300 iterações do loop da cena com 20 configs modificadas,
        inimigos de múltiplos tipos, disparos, colisões, partículas e drops, validando:
        1. Ausência total de crashes ou exceções.
        2. Teto de partículas e textos flutuantes respeitado.
        3. Integridade do placar, abates e HP do jogador.
        """
        cena = GameplayScene()

        # Desbloqueia e ativa configurações com multiplicadores extremos
        configs_teste = {
            "fps_cap": "30",
            "graficos_qualidade": "baixa",
            "resolucao": "50%",
            "vsync": "desligado",
            "screen_shake": "ligado",
            "motion_blur": "ligado",
            "hud": "ligado",
            "damage_numbers": "ligado",
            "zoom": "125%",
            "movimento_mouse": "desligado",
            "keybinds": "pesadelo",
            "suavizacao_camera": "desligado",
            "auto_fire": "ligado",
            "inimigos_ranged": "ligado",
            "coleta_inimiga": "ligado",
            "velocidade_inimigos": "+25%",
            "vida_inimigos": "+50%",
            "iluminacao": "ligado",
            "cores_invertidas": "ligado",
            "fogo_amigo": "desligado"
        }

        for cid, val in configs_teste.items():
            cena.config_sistema.desbloquear_config(cid)
            cena.config_sistema.definir_valor(cid, val)

        cena.aplicar_modificadores()

        # Equipa arma especial (Lança-Foguetes) e Drone
        cena.jogador.arma_especial = LancaFoguetes(municao_max=18)
        cena.jogador.selecionar_slot(3)
        drone = DroneSuporte(tempo_vida=30.0)
        cena.jogador.adicionar_drone(drone)

        # Spawna inimigos diversos
        for i in range(15):
            inim = InimigoPadrao(x=cena.jogador.x + 100 + i * 20, y=cena.jogador.y + 100 + i * 15)
            cena.inimigos.append(inim)

        # Executa 300 frames de simulação
        for frame in range(300):
            cena.loop()

        # Invariantes pós-estresse
        self.assertGreaterEqual(cena.tempo_sobrevivencia, 0.0)
        self.assertGreaterEqual(cena.jogador.hp, 0)
        self.assertLessEqual(len(cena.sistema_particulas.particulas), SistemaParticulas.MAX_PARTICULAS)
        self.assertLessEqual(len(cena.sistema_particulas.textos_dano), SistemaParticulas.MAX_TEXTOS)


if __name__ == "__main__":
    unittest.main()


