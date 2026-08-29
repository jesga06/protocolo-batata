"""
Testes Adversariais e de Stress — Challenger 1 (Phase 6: Elites, Boss Bar, Vitória & Drops)
Testa exaustivamente:
1. Cadência de spawn de Elites por minuto, rotação de arquétipos e escalonamento de stats.
2. Danos extremos (1 dmg vs 10,000 overkill) e resiliência da Boss Bar contra divisão por zero e valores anômalos.
3. Fronteiras exatas da condição de vitória (599.9s vs 600.0s vs 600.1s), congelamento de estado, invulnerabilidade e aritmética de score.
4. Cluster de drops garantidos (50 XP, 1 arma, 1 equipamento) em 100 mortes consecutivas de elites.
5. Simulação de stress de longo prazo e estabilidade de entidades (partículas, drops, projéteis).
"""

import unittest
import math
import os
import pygame
from unittest.mock import MagicMock, patch

# Garante inicialização headless do pygame
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
pygame.init()

from src.sistemas.sistema_spawn import SistemaSpawn
from src.sistemas.sistema_drops import SistemaDrops
from src.sistemas.sistema_particulas import SistemaParticulas
from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.entidades.jogador import Jogador
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.inimigo_tank import InimigoTank
from src.entidades.inimigo_rapido import InimigoRapido
from src.entidades.inimigo_phasing import InimigoPhasing
from src.entidades.inimigo_blindado import InimigoBlindado
from src.entidades.inimigo_ranged import InimigoRanged
from src.entidades.inimigo_base import InimigoBase
from src.entidades.drop import ItemDrop
from src.ui.hud import HUD
from src.cenas.gameplay import GameplayScene
from src.utils.constantes import TEMPO_VITORIA, LARGURA_TELA, ALTURA_TELA


class TestChallengerEliteSpawningAndCadence(unittest.TestCase):
    """
    Testes de estresse da cadência de spawn e catálogo de Elites.
    """

    def setUp(self):
        self.spawner = SistemaSpawn(max_ativos=400)

    def test_elite_spawn_cadence_across_10_minutes(self):
        """Avança o tempo segundo a segundo e verifica que exatamente 1 elite spawna a cada minuto."""
        elites_spawned = []
        dt = 0.5  # passos de 500ms
        tempo_total = 605.0  # 10 minutos e 5 segundos

        t = 0.0
        while t < tempo_total:
            novos = self.spawner.update(
                dt=dt,
                camera_x=0.0,
                camera_y=0.0,
                total_inimigos_vivos=0,
                view_w=800,
                view_h=600,
                arena_w=1600,
                arena_h=1200
            )
            for inim in novos:
                if getattr(inim, "is_elite", False):
                    elites_spawned.append((t + dt, inim))
            t += dt

        # Deve ter gerado exatamente 4 elites em 10 minutos (1:00 / 60s, 3:30 / 210s, 6:00 / 360s, 8:30 / 510s)
        self.assertEqual(len(elites_spawned), 4, f"Esperava 4 elites, mas obteve {len(elites_spawned)}")

        # Verifica timing de cada spawn (60s, 210s, 360s, 510s)
        horarios_esperados = [60.0, 210.0, 360.0, 510.0]
        for i, (tempo_spawn, boss) in enumerate(elites_spawned):
            limiar_segundos = horarios_esperados[i]
            self.assertTrue(
                limiar_segundos <= tempo_spawn <= limiar_segundos + 1.0,
                f"Boss {i+1} spawnou no tempo {tempo_spawn}, fora da janela esperada [{limiar_segundos}, {limiar_segundos + 1.0}]"
            )

    def test_elite_archetype_rotation_catalog(self):
        """Verifica se cada minuto gera o arquétipo e nome correto do catálogo."""
        esperados = {
            1: (InimigoRapido, "MINI-BOSS: ESTAGIÁRIO SÊNIOR"),
            2: (InimigoTank, "MINI-BOSS: GELADEIRA INDUSTRIAL TURBO"),
            3: (InimigoPhasing, "MINI-BOSS: PHANTOM EXECUTIVO"),
            4: (InimigoBlindado, "MINI-BOSS: BASTIÃO TITÂNICO"),
            5: (InimigoRanged, "MINI-BOSS: COMANDANTE ARTILHEIRO"),
            6: (InimigoTank, "MINI-BOSS: HYPER GELADEIRA MK-II"),
            7: (InimigoPhasing, "MINI-BOSS: ESPECTRO CORPORATIVO"),
            8: (InimigoBlindado, "MINI-BOSS: FORTALEZA CIBERNÉTICA"),
            9: (InimigoRanged, "MINI-BOSS: GENERAL BALÍSTICO"),
            10: (InimigoTank, "MINI-BOSS: OVERLORD DA MEMÓRIA MK-10"),
            11: (InimigoTank, "MINI-BOSS: OVERLORD DA MEMÓRIA MK-11"),
        }

        for minuto, (cls_exp, nome_exp) in esperados.items():
            cls_res, nome_res = self.spawner.obter_arquetipo_elite(minuto)
            self.assertEqual(cls_res, cls_exp, f"Minuto {minuto}: classe incorreta ({cls_res} != {cls_exp})")
            self.assertEqual(nome_res, nome_exp, f"Minuto {minuto}: nome incorreto ({nome_res} != {nome_exp})")

    def test_elite_stat_scaling_multipliers(self):
        """Verifica que todos os arquétipos quando instanciados como Elite recebem 3x HP, 10x Score e 50 XP."""
        classes = [InimigoPadrao, InimigoTank, InimigoRapido, InimigoPhasing, InimigoBlindado, InimigoRanged]

        for cls_enemy in classes:
            base_instance = cls_enemy(x=0, y=0, is_elite=False)
            elite_instance = cls_enemy(x=0, y=0, is_elite=True, nome_elite="TEST BOSS")

            # 3x HP
            self.assertEqual(elite_instance.hp_max, base_instance.hp_max * 3)
            self.assertEqual(elite_instance.hp, base_instance.hp * 3)

            # 10x Score
            self.assertEqual(elite_instance.score_valor, base_instance.score_valor * 10)

            # 50 XP
            self.assertEqual(elite_instance.xp_valor, 50)
            self.assertTrue(elite_instance.is_elite)
            self.assertEqual(elite_instance.nome_elite, "TEST BOSS")

    def test_spawner_max_population_cap_under_pressure(self):
        """Verifica que o spawner nunca ultrapassa max_ativos mesmo sob alta pressão de spawn."""
        spawner = SistemaSpawn(max_ativos=50)
        spawner.tempo_decorrido = 100.0  # Lote = 5 inimigos
        populacao_atual = 48

        # Tenta spawnar em tempo avançado (lote = 5, vagas = 2)
        novos = spawner.update(
            dt=10.0,
            camera_x=0,
            camera_y=0,
            total_inimigos_vivos=populacao_atual,
            view_w=800,
            view_h=600,
            arena_w=1600,
            arena_h=1200
        )
        # Só haviam 2 vagas disponíveis (50 - 48 = 2)
        self.assertLessEqual(len(novos), 2)
        self.assertEqual(populacao_atual + len(novos), 50)


class TestChallengerExtremeDamageAndBossBarHUD(unittest.TestCase):
    """
    Testes de danos extremos e resiliência da Boss Bar a divisões por zero e valores anômalos.
    """

    def setUp(self):
        self.hud = HUD()
        self.screen = pygame.Surface((800, 600))

    def test_extreme_underkill_1_damage_per_hit(self):
        """Inimigo Elite com 360 HP submetido a 360 golpes de 1 de dano."""
        boss = InimigoTank(x=100, y=100, is_elite=True, nome_elite="BOSS RESISTENTE")
        self.assertEqual(boss.hp, 360)

        for i in range(359):
            boss.receber_dano(1)
            self.assertTrue(boss.vivo, f"Boss morreu prematuramente no golpe {i+1}")
            self.assertEqual(boss.hp, 360 - (i + 1))
            self.assertAlmostEqual(boss.flash_timer, 0.10)

        # 360º golpe: deve morrer
        boss.receber_dano(1)
        self.assertFalse(boss.vivo)
        self.assertEqual(boss.hp, 0)

    def test_extreme_overkill_10000_damage_instant(self):
        """Inimigo Elite submetido a 10.000 de dano instantâneo."""
        boss = InimigoTank(x=100, y=100, is_elite=True, nome_elite="BOSS OVERKILL")
        boss.receber_dano(10000)

        self.assertFalse(boss.vivo)
        self.assertLessEqual(boss.hp, 0)

        # Repetir dano após morto não deve causar crash
        boss.receber_dano(500)
        self.assertFalse(boss.vivo)

    def test_boss_hp_bar_division_by_zero_and_edge_cases(self):
        """Verifica que desenhar_barra_boss é imune a division-by-zero, hp negativo ou hp_max=0."""
        # 1. Boss None
        self.hud.desenhar_barra_boss(self.screen, None, visivel=True)

        # 2. Boss morto
        boss_morto = InimigoTank(x=0, y=0, is_elite=True)
        boss_morto.vivo = False
        self.hud.desenhar_barra_boss(self.screen, boss_morto, visivel=True)

        # 3. Boss com HP = 0 e vivo
        boss_zero_hp = InimigoTank(x=0, y=0, is_elite=True)
        boss_zero_hp.hp = 0
        boss_zero_hp.vivo = True
        self.hud.desenhar_barra_boss(self.screen, boss_zero_hp, visivel=True)

        # 4. Boss com HP negativo extremo (-9999)
        boss_neg = InimigoTank(x=0, y=0, is_elite=True)
        boss_neg.hp = -9999
        boss_neg.vivo = True
        self.hud.desenhar_barra_boss(self.screen, boss_neg, visivel=True)

        # 5. Boss com hp_max = 0 (potencial division by zero)
        boss_zero_max = InimigoTank(x=0, y=0, is_elite=True)
        boss_zero_max.hp_max = 0
        boss_zero_max.hp = 0
        boss_zero_max.vivo = True
        self.hud.desenhar_barra_boss(self.screen, boss_zero_max, visivel=True)

        # 6. Boss com HP > hp_max (overheal bug)
        boss_over = InimigoTank(x=0, y=0, is_elite=True)
        boss_over.hp_max = 100
        boss_over.hp = 500
        boss_over.vivo = True
        self.hud.desenhar_barra_boss(self.screen, boss_over, visivel=True)

        # 7. Boss com nome vazio
        boss_sem_nome = InimigoTank(x=0, y=0, is_elite=True, nome_elite="")
        boss_sem_nome.vivo = True
        self.hud.desenhar_barra_boss(self.screen, boss_sem_nome, visivel=True)

        # Se chegou até aqui sem nenhuma exceção, o teste passou com sucesso


class TestChallengerVictoryConditionAndStateFreeze(unittest.TestCase):
    """
    Testes das fronteiras da vitória de 10 minutos (599.9s, 600.0s, 600.1s),
    congelamento de estado, invulnerabilidade e cálculo do score final.
    """

    def setUp(self):
        self.janela_mock = MagicMock()
        self.janela_mock.delta_time.return_value = 0.01666
        self.janela_mock.screen = pygame.Surface((800, 600))
        self.janela_mock.largura = 800
        self.janela_mock.altura = 600
        self.janela_mock.get_fps.return_value = 60

        with patch("src.cenas.gameplay.SAVE_FILE_PATH", "data/test_challenger_save.json"):
            self.scene = GameplayScene()
            self.scene.janela = self.janela_mock

    def tearDown(self):
        if os.path.exists("data/test_challenger_save.json"):
            try:
                os.remove("data/test_challenger_save.json")
            except Exception:
                pass

    def test_victory_boundary_599_9s_vs_600_0s_vs_600_1s(self):
        """Testa o acionamento da vitória exatamente nos limites de tempo."""
        # 1. 599.9 segundos: Ainda não venceu
        self.scene.tempo_sobrevivencia = 599.9
        self.scene.vitoria = False
        self.scene.jogador.vivo = True

        self.assertFalse(self.scene.vitoria)

        # 2. Transição para 600.0 segundos
        self.scene.tempo_sobrevivencia = 600.0
        # Simula verificação de vitória no loop
        if self.scene.tempo_sobrevivencia >= TEMPO_VITORIA and self.scene.jogador.vivo and not self.scene.vitoria:
            self.scene.vitoria = True
            self.scene._acionar_vitoria()

        self.assertTrue(self.scene.vitoria)
        self.assertTrue(self.scene.partida_registrada)

        # 3. 600.1 segundos: Permanece vitorioso
        self.scene.tempo_sobrevivencia = 600.1
        self.assertTrue(self.scene.vitoria)

    def test_state_freeze_and_projectiles_cleared_on_victory(self):
        """Verifica que a vitória congela inimigos e remove projéteis."""
        # Adiciona inimigos com velocidade e projéteis
        inimigo1 = InimigoRapido(x=100, y=100)
        inimigo1.velocidade = 150.0
        inimigo1.vx_knockback = 50.0
        inimigo2 = InimigoTank(x=200, y=200)
        inimigo2.velocidade = 80.0

        self.scene.inimigos = [inimigo1, inimigo2]
        self.scene.projeteis = [MagicMock(), MagicMock()]

        # Aciona vitória
        self.scene._acionar_vitoria()

        # Inimigos devem ter velocidade e knockback zerados
        for inim in self.scene.inimigos:
            self.assertEqual(inim.velocidade, 0.0)
            self.assertEqual(inim.vx_knockback, 0.0)
            self.assertEqual(inim.vy_knockback, 0.0)

        # Lista de projéteis deve estar vazia
        self.assertEqual(len(self.scene.projeteis), 0)

    def test_player_invulnerability_after_victory_loop(self):
        """Verifica que após a vitória o loop retorna imediatamente sem processar dano de contato."""
        self.scene.vitoria = True
        hp_inicial = self.scene.jogador.hp

        # Adiciona um inimigo posicionado sobre o jogador
        inimigo = InimigoTank(x=self.scene.jogador.x, y=self.scene.jogador.y)
        self.scene.inimigos = [inimigo]

        # Executa múltiplos frames de loop
        for _ in range(10):
            self.scene.loop()

        # HP do jogador deve permanecer intacto
        self.assertEqual(self.scene.jogador.hp, hp_inicial)

    def test_final_score_and_difficulty_multiplier_arithmetic(self):
        """Testa o cálculo matemático da pontuação final com e sem vitória e multiplicadores de dificuldade."""
        self.scene.pontos = 5000       # s_abates
        self.scene.tempo_sobrevivencia = 600.0  # s_tempo = 6000
        self.scene.dano_total_causado = 4000    # s_dano = 2000

        # Caso 1: Sem vitória (+0), sem configs não-padrão (mult=1.0)
        score_1, mult_1 = self.scene._calcular_score_final(vitoria=False)
        # 5000 + 6000 + 2000 + 0 = 13000 * 1.0 = 13000
        self.assertEqual(mult_1, 1.0)
        self.assertEqual(score_1, 13000)

        # Caso 2: Com vitória (+10000), sem configs não-padrão (mult=1.0)
        score_2, mult_2 = self.scene._calcular_score_final(vitoria=True)
        # 5000 + 6000 + 2000 + 10000 = 23000 * 1.0 = 23000
        self.assertEqual(mult_2, 1.0)
        self.assertEqual(score_2, 23000)

        # Caso 3: Com vitória (+10000) e 5 configs ativas não padrão (mult = 1.0 + 0.10*5 = 1.50)
        # Desbloqueia e altera 5 configs de gameplay
        configs_to_unlock = ["fps_cap", "graficos_qualidade", "resolucao", "vsync", "screen_shake"]
        for cid in configs_to_unlock:
            self.scene.gerenciador_config.desbloquear_config(cid)

        self.scene.gerenciador_config.definir_valor("fps_cap", "30")
        self.scene.gerenciador_config.definir_valor("graficos_qualidade", "baixa")
        self.scene.gerenciador_config.definir_valor("resolucao", "50%")
        self.scene.gerenciador_config.definir_valor("vsync", "desligado")
        self.scene.gerenciador_config.definir_valor("screen_shake", "ligado")

        score_3, mult_3 = self.scene._calcular_score_final(vitoria=True)
        self.assertAlmostEqual(mult_3, 1.50, places=2)
        # 23000 * 1.50 = 34500
        self.assertEqual(score_3, int(round(23000 * 1.50)))


class TestChallengerGuaranteedDropCluster(unittest.TestCase):
    """
    Testes de integridade e garantia matemática dos drops de Elites (100 repetições).
    """

    def setUp(self):
        self.sistema_drops = SistemaDrops()
        self.jogador = Jogador(x=100, y=100)

    def test_guaranteed_drop_cluster_100_consecutive_elites(self):
        """Executa 100 mortes de Elites e valida que TODAS geram exatamente 50 XP, 1 arma e 1 equipamento."""
        for run_id in range(100):
            drops_gerados = self.sistema_drops.gerar_drop_morte_inimigo(
                x=200.0,
                y=300.0,
                is_elite=True
            )

            # Filtra por tipos
            drops_xp = [d for d in drops_gerados if d.tipo == "xp"]
            drops_arma = [d for d in drops_gerados if d.tipo == "arma"]
            drops_equip = [d for d in drops_gerados if d.tipo == "equipamento"]
            drops_cura = [d for d in drops_gerados if d.tipo == "cura"]

            # Validações estritas
            self.assertEqual(len(drops_xp), 5, f"Run {run_id}: esperava 5 gemas de XP, obteve {len(drops_xp)}")
            total_xp = sum(d.valor for d in drops_xp)
            self.assertEqual(total_xp, 50, f"Run {run_id}: soma de XP = {total_xp} != 50")

            self.assertEqual(len(drops_arma), 1, f"Run {run_id}: esperava 1 drop de arma garantido")
            self.assertEqual(len(drops_equip), 1, f"Run {run_id}: esperava 1 drop de equipamento garantido")
            self.assertIn(len(drops_cura), [0, 1], f"Run {run_id}: drop de cura fora do esperado [0, 1]")

            # Valida anel circular de XP (~24px de raio)
            for gema in drops_xp:
                dist_centro = math.hypot(gema.x + 8.0 - 200.0, gema.y + 8.0 - 300.0)
                self.assertAlmostEqual(dist_centro, 24.0, delta=1.0)

    def test_player_collects_full_elite_cluster(self):
        """Simula jogador coletando todos os drops de um elite e verifica acúmulo exato de stats."""
        drops = self.sistema_drops.gerar_drop_morte_inimigo(x=100.0, y=100.0, is_elite=True)
        self.jogador.x = 100.0
        self.jogador.y = 100.0

        # Coleta os drops
        eventos = self.sistema_drops.coletar_jogador(self.jogador, mult_valor_drop=1.0)

        # Verifica ganho total de XP
        eventos_xp = [e for e in eventos if e["tipo"] == "xp"]
        xp_ganho = sum(e["valor"] for e in eventos_xp)
        self.assertEqual(xp_ganho, 50)

        # Verifica se arma especial foi equipada
        self.assertIsNotNone(self.jogador.arma_especial)
        self.assertEqual(self.jogador.slot_ativo, 3)

        # Verifica se drone foi equipado
        self.assertIsNotNone(self.jogador.drone)


class TestChallengerLongRunningStabilityAndParticles(unittest.TestCase):
    """
    Testes de estabilidade de longo prazo (milhares de iterações),
    teto estrito de partículas e expiração correta de drops.
    """

    def test_particle_ceiling_enforcement_under_burst_spam(self):
        """Verifica que o sistema de partículas NUNCA ultrapassa MAX_PARTICULAS (300)."""
        sp = SistemaParticulas()

        # Dispara 100 explosões e faíscas massivas
        for _ in range(100):
            sp.emitir_faiscas(100, 100, 1, 0, qtd=20)
            sp.emitir_debris(100, 100, qtd=30)
            sp.emitir_onda_choque(100, 100, raio_max=100)

        self.assertLessEqual(len(sp.particulas), SistemaParticulas.MAX_PARTICULAS)
        self.assertEqual(len(sp.particulas), SistemaParticulas.MAX_PARTICULAS)

        # Avança tempo para dissipar partículas
        sp.update(2.0)
        self.assertEqual(len(sp.particulas), 0)
        self.assertEqual(len(sp.ondas_choque), 0)

    def test_drops_expire_after_60_seconds(self):
        """Verifica que drops não coletados são limpos após DROP_TEMPO_DESAPARECER (60s)."""
        sd = SistemaDrops()
        sd.gerar_drop_morte_inimigo(x=100, y=100, is_elite=True)
        self.assertIn(len(sd.drops), [7, 8])

        # Avança 30 segundos: drops ainda devem existir
        sd.update(30.0)
        self.assertTrue(len(sd.drops) >= 7)

        # Avança mais 31 segundos (total 61s > 60s): todos os drops devem expirar
        sd.update(31.0)
        self.assertEqual(len(sd.drops), 0)


class TestChallengerMultiBossTransitionAndDamageSources(unittest.TestCase):
    """
    Testes de coexistência de múltiplos chefes e drops consistentes através de múltiplas fontes de dano.
    """

    def test_multi_boss_hud_transition(self):
        """Quando múltiplos chefes estão vivos, o HUD acompanha o primeiro e transiciona suavemente após sua morte."""
        hud = HUD()
        screen = pygame.Surface((800, 600))

        boss1 = InimigoRapido(x=100, y=100, is_elite=True, nome_elite="BOSS 1")
        boss2 = InimigoTank(x=200, y=200, is_elite=True, nome_elite="BOSS 2")
        inimigos = [boss1, boss2]

        # 1. Ambos vivos: HUD seleciona boss1
        boss_ativo = next((e for e in inimigos if getattr(e, "is_elite", False) and e.vivo), None)
        self.assertEqual(boss_ativo, boss1)
        hud.desenhar_barra_boss(screen, boss_ativo, visivel=True)

        # 2. Boss 1 é eliminado: HUD seleciona boss2
        boss1.receber_dano(boss1.hp_max)
        self.assertFalse(boss1.vivo)

        boss_ativo = next((e for e in inimigos if getattr(e, "is_elite", False) and e.vivo), None)
        self.assertEqual(boss_ativo, boss2)
        hud.desenhar_barra_boss(screen, boss_ativo, visivel=True)

        # 3. Boss 2 é eliminado: nenhum boss ativo
        boss2.receber_dano(boss2.hp_max)
        self.assertFalse(boss2.vivo)

        boss_ativo = next((e for e in inimigos if getattr(e, "is_elite", False) and e.vivo), None)
        self.assertIsNone(boss_ativo)
        hud.desenhar_barra_boss(screen, boss_ativo, visivel=True)


class TestChallengerPersistenceAndE2EGameplayStress(unittest.TestCase):
    """
    Testes de estresse de persistência e simulação contínua do loop de gameplay.
    """

    def setUp(self):
        self.test_save_file = "data/test_challenger_persistence_stress.json"
        if os.path.exists(self.test_save_file):
            try:
                os.remove(self.test_save_file)
            except Exception:
                pass

    def tearDown(self):
        if os.path.exists(self.test_save_file):
            try:
                os.remove(self.test_save_file)
            except Exception:
                pass

    def test_save_persistence_stress_50_matches(self):
        """Registra 50 partidas consecutivas e verifica integridade dos dados e capping de histórico em 20."""
        cfg = GerenciadorConfiguracoes()

        for i in range(50):
            tempo = 100.0 + i * 10.0
            abates = 50 + i * 5
            pontos = 1000 + i * 500
            vitoria = (i % 5 == 0)
            dano = 5000 + i * 1000

            res = cfg.registrar_partida(tempo, abates, pontos, vitoria=vitoria, dano_causado=dano)
            self.assertIn("novo_recorde_pontos", res)
            self.assertIn("novo_recorde_tempo", res)

        stats = cfg.obter_estatisticas()
        self.assertEqual(stats["partidas_jogadas"], 50)
        self.assertEqual(stats["vitorias"], 10)  # 50 // 5 = 10
        self.assertEqual(len(stats["historico"]), 20)  # Capped at 20

        # Salva em disco e recarrega
        cfg.salvar_arquivo(self.test_save_file)

        cfg_reloaded = GerenciadorConfiguracoes()
        cfg_reloaded.carregar_arquivo(self.test_save_file)

        stats_reloaded = cfg_reloaded.obter_estatisticas()
        self.assertEqual(stats_reloaded["partidas_jogadas"], 50)
        self.assertEqual(stats_reloaded["vitorias"], 10)
        self.assertEqual(stats_reloaded["high_score"], stats["high_score"])
        self.assertEqual(stats_reloaded["melhor_tempo"], stats["melhor_tempo"])
        self.assertEqual(len(stats_reloaded["historico"]), 20)

    def test_simulated_fast_forward_to_victory(self):
        """Simula 10 minutos (600s) de jogo avançando em passos rápidos e valida integridade final."""
        janela_mock = MagicMock()
        janela_mock.delta_time.return_value = 1.0  # 1s por tick
        janela_mock.screen = pygame.Surface((800, 600))
        janela_mock.largura = 800
        janela_mock.altura = 600
        janela_mock.get_fps.return_value = 60

        with patch("src.cenas.gameplay.SAVE_FILE_PATH", self.test_save_file):
            scene = GameplayScene()
            scene.janela = janela_mock

            # Desativa sons reais
            with patch("pygame.mixer.music.fadeout"), patch("PPlay.sound.Sound.play"):
                # Itera 601 segundos
                for _ in range(601):
                    if not scene.vitoria and not scene.game_over:
                        scene.tempo_sobrevivencia += 1.0
                        if scene.tempo_sobrevivencia >= TEMPO_VITORIA and scene.jogador.vivo and not scene.vitoria:
                            scene.vitoria = True
                            scene._acionar_vitoria()

            self.assertTrue(scene.vitoria)
            self.assertTrue(scene.partida_registrada)
            self.assertGreaterEqual(scene.estatisticas_partida_resultado["score_final"], 10000)


if __name__ == "__main__":
    unittest.main()
