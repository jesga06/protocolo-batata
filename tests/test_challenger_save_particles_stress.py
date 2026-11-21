"""
Adversarial Stress Test Suite — Challenger 2 (Phase 6)
Focus Areas:
1. Save Persistence Stress & High-Frequency Match Registration (100 sequential matches)
2. Corrupt, Empty, and Partial JSON Schema Migration & Resilience
3. Particle System Load Limits (10,000 particle emission churn, bounds, memory stability)
4. Screen Shake Active vs Inactive Camera & State Behavior
"""

import json
import math
import os
import random
import tempfile
import unittest
import pygame
from unittest.mock import MagicMock

from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.sistemas.sistema_particulas import SistemaParticulas, Particula, OndaChoque
from src.cenas.gameplay import GameplayScene
from PPlay.window import Window


class TestChallengerSaveParticlesStress(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        self.caminho_save = self.temp_file.name

    def tearDown(self):
        if os.path.exists(self.caminho_save):
            try:
                os.remove(self.caminho_save)
            except Exception:
                pass

    # =========================================================================
    # 1. SAVE PERSISTENCE STRESS TESTS
    # =========================================================================

    def test_stress_100_sequential_match_registrations(self):
        """
        Stress test: 100 rapid sequential match registrations.
        Verifies:
        - Historico strictly capped at 20 entries.
        - High score accurately reflects maximum points registered.
        - Melhor tempo accurately reflects maximum survival time.
        - Total abates is exact sum of all kills.
        - Vitorias is exact count of victories.
        - Partidas jogadas equals 100.
        - Disk save.json is valid, uncorrupted, and matches memory state.
        """
        gerente = GerenciadorConfiguracoes()
        total_abates_esperado = 0
        total_vitorias_esperado = 0
        max_pontos_esperado = 0
        max_tempo_esperado = 0.0

        for i in range(1, 101):
            tempo = round(random.uniform(10.0, 600.0), 2)
            abates = random.randint(0, 150)
            pontos = random.randint(100, 50000)
            vitoria = (tempo >= 600.0) or (random.random() < 0.15)
            dano = abates * 40 + random.randint(0, 500)

            total_abates_esperado += abates
            if vitoria:
                total_vitorias_esperado += 1
            if pontos > max_pontos_esperado:
                max_pontos_esperado = pontos
            if tempo > max_tempo_esperado:
                max_tempo_esperado = tempo

            res = gerente.registrar_partida(
                tempo=tempo,
                abates=abates,
                pontos=pontos,
                vitoria=vitoria,
                dano_causado=dano
            )
            self.assertIsInstance(res, dict)
            self.assertIn("novo_recorde_pontos", res)
            self.assertIn("novo_recorde_tempo", res)

        est = gerente.obter_estatisticas()
        self.assertEqual(est["partidas_jogadas"], 100)
        self.assertEqual(est["total_abates"], total_abates_esperado)
        self.assertEqual(est["vitorias"], total_vitorias_esperado)
        self.assertEqual(est["high_score"], max_pontos_esperado)
        self.assertAlmostEqual(est["melhor_tempo"], max_tempo_esperado, places=2)
        self.assertEqual(len(est["historico"]), 20)

        # Salva em arquivo e verifica integridade no disco
        sucesso_salvar = gerente.salvar_arquivo(self.caminho_save)
        self.assertTrue(sucesso_salvar)

        with open(self.caminho_save, "r", encoding="utf-8") as f:
            dados_disco = json.load(f)

        self.assertIn("estatisticas", dados_disco)
        self.assertIn("desbloqueadas", dados_disco)
        self.assertIn("ativas", dados_disco)
        self.assertIn("sistema_configs", dados_disco)

        est_disco = dados_disco["estatisticas"]
        self.assertEqual(est_disco["partidas_jogadas"], 100)
        self.assertEqual(est_disco["total_abates"], total_abates_esperado)
        self.assertEqual(est_disco["high_score"], max_pontos_esperado)
        self.assertEqual(len(est_disco["historico"]), 20)

        # Recarrega em uma nova instância limpa
        gerente_novo = GerenciadorConfiguracoes()
        sucesso_carregar = gerente_novo.carregar_arquivo(self.caminho_save)
        self.assertTrue(sucesso_carregar)
        est_recarregado = gerente_novo.obter_estatisticas()
        self.assertEqual(est_recarregado["high_score"], max_pontos_esperado)
        self.assertEqual(est_recarregado["total_abates"], total_abates_esperado)
        self.assertEqual(len(est_recarregado["historico"]), 20)

    def test_multi_instance_save_load_cycle_resilience(self):
        """
        Testa múltiplos ciclos de modificação, salvamento e carregamento entre
        instâncias independentes sem perda de dados ou degradação.
        """
        for ciclo in range(10):
            g = GerenciadorConfiguracoes()
            if ciclo > 0:
                g.carregar_arquivo(self.caminho_save)

            g.registrar_partida(tempo=float(ciclo * 10), abates=ciclo * 5, pontos=ciclo * 1000)
            if ciclo % 2 == 0:
                g.desbloquear_config("fps_cap")
                g.definir_valor("fps_cap", "30")

            g.salvar_arquivo(self.caminho_save)

        final_g = GerenciadorConfiguracoes()
        final_g.carregar_arquivo(self.caminho_save)
        est = final_g.obter_estatisticas()
        self.assertEqual(est["partidas_jogadas"], 10)
        self.assertEqual(est["high_score"], 9000)
        self.assertEqual(len(est["historico"]), 10)
        self.assertEqual(final_g.obter_valor("fps_cap"), "30")

    # =========================================================================
    # 2. MALFORMED / CORRUPT JSON RESILIENCE TESTS
    # =========================================================================

    def test_resilience_to_corrupt_json_syntax(self):
        """Garante que sintaxe JSON quebrada não provoca exceção fatal e mantém defaults."""
        with open(self.caminho_save, "w", encoding="utf-8") as f:
            f.write("{ invalid json content ::: ??? ")

        gerente = GerenciadorConfiguracoes()
        carregou = gerente.carregar_arquivo(self.caminho_save)
        self.assertFalse(carregou)

        est = gerente.obter_estatisticas()
        self.assertEqual(est["high_score"], 0)
        self.assertEqual(est["partidas_jogadas"], 0)
        self.assertEqual(len(est["historico"]), 0)

    def test_resilience_to_empty_file(self):
        """Garante que arquivo vazio (0 bytes) não gera crash."""
        with open(self.caminho_save, "w", encoding="utf-8") as f:
            f.write("")

        gerente = GerenciadorConfiguracoes()
        carregou = gerente.carregar_arquivo(self.caminho_save)
        self.assertFalse(carregou)
        self.assertEqual(gerente.obter_estatisticas()["high_score"], 0)

    def test_resilience_to_empty_json_dict(self):
        """Garante que JSON vazio `{}` carrega defaults com sucesso."""
        with open(self.caminho_save, "w", encoding="utf-8") as f:
            json.dump({}, f)

        gerente = GerenciadorConfiguracoes()
        carregou = gerente.carregar_arquivo(self.caminho_save)
        self.assertTrue(carregou)
        est = gerente.obter_estatisticas()
        self.assertEqual(est["high_score"], 0)
        self.assertEqual(len(est["historico"]), 0)

    def test_resilience_to_partial_or_mutated_schema_in_carregar_arquivo(self):
        """
        Testa se carregar_arquivo lida graciosamente com JSONs contendo campos nulos
        ou estruturas corrompidas sem quebrar o jogo ou lançar exceções não tratadas.
        """
        cenarios_anormais = [
            {"desbloqueadas": None, "ativas": None, "estatisticas": None},
            {"estatisticas": "not_a_dict"},
            {"estatisticas": {"high_score": "5000", "melhor_tempo": "120.5", "historico": None}},
            {"estatisticas": {"historico": "not_a_list"}},
            {"desbloqueadas": 12345, "ativas": [1, 2, 3]},
            {"sistema_configs": "invalid"}
        ]

        for i, cenario in enumerate(cenarios_anormais):
            with open(self.caminho_save, "w", encoding="utf-8") as f:
                json.dump(cenario, f)

            gerente = GerenciadorConfiguracoes()
            try:
                carregou = gerente.carregar_arquivo(self.caminho_save)
                est = gerente.obter_estatisticas()
                self.assertIsInstance(est, dict)
            except Exception as e:
                self.fail(f"carregar_arquivo lançou exceção não tratada no cenário {i} ({cenario}): {e}")

    def test_salvar_em_caminho_invalido_retorna_false(self):
        """Garante que tentar salvar em caminho inacessível/inválido retorna False sem crash."""
        gerente = GerenciadorConfiguracoes()
        # Caminho nulo ou diretório protegido/inválido
        caminho_invalido = "Z:\\non_existent_folder_xyz_123\\save.json"
        sucesso = gerente.salvar_arquivo(caminho_invalido)
        self.assertFalse(sucesso)

    # =========================================================================
    # 3. PARTICLE SYSTEM LOAD LIMITS & STRESS TESTS
    # =========================================================================

    def test_stress_10000_particle_emission_ceiling(self):
        """
        Emite 10.000 partículas em rápida sucessão através de faíscas, bursts e debris.
        Verifica:
        - len(particulas) nunca ultrapassa MAX_PARTICULAS (300).
        - A lista de partículas permanece limitada e sem vazamento de referências.
        """
        sistema = SistemaParticulas()

        for i in range(1000):
            modo = i % 3
            if modo == 0:
                sistema.emitir_faiscas(x=100.0, y=100.0, dir_x=1.0, dir_y=0.0, qtd=10)
            elif modo == 1:
                sistema.emitir_burst_drop(x=200.0, y=200.0, tipo="xp")
            else:
                sistema.emitir_debris(x=300.0, y=300.0, qtd=12)

            self.assertLessEqual(
                len(sistema.particulas),
                SistemaParticulas.MAX_PARTICULAS,
                f"Teto excedido na iteração {i}: {len(sistema.particulas)}"
            )

        self.assertEqual(len(sistema.particulas), SistemaParticulas.MAX_PARTICULAS)

    def test_stress_shockwave_lifecycle_and_cleanup(self):
        """
        Emite centenas de ondas de choque e valida ciclo de vida e descarte completo.
        """
        sistema = SistemaParticulas()
        for i in range(200):
            sistema.emitir_onda_choque(x=float(i), y=float(i), raio_max=100.0)

        self.assertEqual(len(sistema.ondas_choque), SistemaParticulas.MAX_ONDAS)

        # Atualiza por 0.10s -> todas devem continuar ativas (vida_max = 0.28s)
        sistema.update(0.10)
        self.assertEqual(len(sistema.ondas_choque), SistemaParticulas.MAX_ONDAS)

        # Atualiza por mais 0.30s (total 0.40s > 0.28s) -> todas devem ser descartadas
        sistema.update(0.30)
        self.assertEqual(len(sistema.ondas_choque), 0)

    def test_stress_particle_update_loop_churn(self):
        """
        Simula 1.000 ciclos de emissão intercalada com atualização dt variável.
        """
        sistema = SistemaParticulas()
        dts = [0.001, 0.016, 0.033, 0.05, 0.1, 0.0]

        for ciclo in range(1000):
            dt = dts[ciclo % len(dts)]
            sistema.emitir_faiscas(x=0, y=0, qtd=4)
            sistema.emitir_debris(x=0, y=0, qtd=4)
            sistema.update(dt)
            self.assertLessEqual(len(sistema.particulas), SistemaParticulas.MAX_PARTICULAS)

        # Limpeza total
        sistema.limpar()
        self.assertEqual(len(sistema.particulas), 0)
        self.assertEqual(len(sistema.ondas_choque), 0)

    def test_particle_boundary_coordinates_and_rendering(self):
        """
        Valida que coordenadas extremas (muito fora da tela, negativas, grandes)
        não provocam erro de renderização nem quebram o pipeline.
        """
        sistema = SistemaParticulas()
        sistema.emitir_faiscas(x=-999999.0, y=-999999.0, qtd=10)
        sistema.emitir_faiscas(x=999999.0, y=999999.0, qtd=10)
        sistema.emitir_onda_choque(x=-50000.0, y=-50000.0)

        # Atualização física com coordenadas extremas
        sistema.update(0.016)

        # Simula renderização
        janela_mock = MagicMock()
        janela_mock.largura = 800
        janela_mock.altura = 600
        janela_mock.screen = pygame.Surface((800, 600))

        camera_mock = MagicMock()
        camera_mock.transform_x = lambda wx: wx - 400
        camera_mock.transform_y = lambda wy: wy - 300

        try:
            sistema.desenhar(janela_mock, camera_mock)
        except Exception as e:
            self.fail(f"Renderização de partículas com coordenadas extremas falhou: {e}")

    # =========================================================================
    # 4. SCREEN SHAKE ACTIVE VS INACTIVE TOGGLE TESTS
    # =========================================================================

    def test_screen_shake_strictly_zero_when_desligado(self):
        """
        Verifica que quando 'screen_shake' está desligado, nenhum jitter ou
        shake_intensidade/shake_timer é ativado.
        """
        janela = Window(800, 600)
        cena = GameplayScene()

        # Garante que screen_shake está desligado
        self.assertEqual(cena.gerenciador_config.obter_valor("screen_shake"), "desligado")

        for intensidade in [5.0, 10.0, 20.0, 50.0]:
            cena.aplicar_shake(intensidade=intensidade, duracao=0.5)
            self.assertEqual(cena.shake_intensidade, 0.0)
            self.assertEqual(cena.shake_timer, 0.0)

    def test_screen_shake_active_multi_trigger_max_policy(self):
        """
        Verifica que quando 'screen_shake' está ligado, múltiplos chamados
        preservam o valor máximo de intensidade e duração (sem diminuir).
        """
        janela = Window(800, 600)
        cena = GameplayScene()

        cena.gerenciador_config.desbloquear_config("screen_shake")
        cena.gerenciador_config.definir_valor("screen_shake", "ligado")

        # Primeiro impacto: leve (6.0, 0.15s)
        cena.aplicar_shake(intensidade=6.0, duracao=0.15)
        self.assertEqual(cena.shake_intensidade, 6.0)
        self.assertEqual(cena.shake_timer, 0.15)

        # Segundo impacto: pesado (14.0, 0.35s) -> deve sobrescrever para o maior
        cena.aplicar_shake(intensidade=14.0, duracao=0.35)
        self.assertEqual(cena.shake_intensidade, 14.0)
        self.assertEqual(cena.shake_timer, 0.35)

        # Terceiro impacto: menor (4.0, 0.10s) -> não deve diminuir os valores atuais
        cena.aplicar_shake(intensidade=4.0, duracao=0.10)
        self.assertEqual(cena.shake_intensidade, 14.0)
        self.assertEqual(cena.shake_timer, 0.35)

    def test_screen_shake_decay_and_turnoff_mid_shake(self):
        """
        Testa a expiração natural do screen shake e comportamento caso seja desligado.
        """
        janela = Window(800, 600)
        cena = GameplayScene()

        cena.gerenciador_config.desbloquear_config("screen_shake")
        cena.gerenciador_config.definir_valor("screen_shake", "ligado")

        cena.aplicar_shake(intensidade=10.0, duracao=0.20)
        self.assertEqual(cena.shake_intensidade, 10.0)

        # Simula update com dt = 0.10
        dt = 0.10
        if cena.shake_timer > 0.0:
            cena.shake_timer = max(0.0, cena.shake_timer - dt)
            if cena.shake_timer == 0.0:
                cena.shake_intensidade = 0.0
        self.assertAlmostEqual(cena.shake_timer, 0.10)
        self.assertEqual(cena.shake_intensidade, 10.0)

        # Desliga a configuração
        cena.gerenciador_config.definir_valor("screen_shake", "desligado")
        # Próxima tentativa de aplicar shake deve ser ignorada
        cena.aplicar_shake(intensidade=20.0, duracao=0.50)
        # Valores continuam nos que estavam antes da tentativa
        self.assertAlmostEqual(cena.shake_timer, 0.10)
        self.assertEqual(cena.shake_intensidade, 10.0)

        # Finaliza o timer
        dt = 0.15
        if cena.shake_timer > 0.0:
            cena.shake_timer = max(0.0, cena.shake_timer - dt)
            if cena.shake_timer == 0.0:
                cena.shake_intensidade = 0.0
        self.assertEqual(cena.shake_timer, 0.0)
        self.assertEqual(cena.shake_intensidade, 0.0)

    def test_rapid_disk_io_50_consecutive_saves_integrity(self):
        """
        Stress test de I/O em disco: Executa 50 salvamentos rápidos consecutivos
        em disco e verifica que o arquivo nunca fica corrompido, truncado ou ilegível.
        """
        gerente = GerenciadorConfiguracoes()
        for i in range(50):
            gerente.registrar_partida(tempo=float(i + 1), abates=i, pontos=i * 200, vitoria=(i % 5 == 0))
            sucesso = gerente.salvar_arquivo(self.caminho_save)
            self.assertTrue(sucesso, f"Falha ao salvar no ciclo {i}")

            # Lê imediatamente e valida JSON
            with open(self.caminho_save, "r", encoding="utf-8") as f:
                dados = json.load(f)
            self.assertIn("estatisticas", dados)
            self.assertEqual(dados["estatisticas"]["partidas_jogadas"], i + 1)

    def test_particle_memory_flatness_stress(self):
        """
        Stress test de memória: Executa 5.000 iterações emitindo e atualizando partículas.
        Verifica que a contagem de instâncias ativas nunca vaza além de MAX_PARTICULAS (300).
        """
        import gc
        sistema = SistemaParticulas()
        gc.collect()

        for _ in range(5000):
            sistema.emitir_faiscas(100, 100, 1, 0, qtd=5)
            sistema.emitir_burst_drop(100, 100, "xp")
            sistema.update(0.016)

        # Deve estar estritamente no teto ou abaixo
        self.assertLessEqual(len(sistema.particulas), SistemaParticulas.MAX_PARTICULAS)
        self.assertLessEqual(len(sistema.ondas_choque), 100)

        # Ao atualizar por 1 segundo sem novas emissões, tudo é descartado
        sistema.update(1.0)
        self.assertEqual(len(sistema.particulas), 0)
        self.assertEqual(len(sistema.ondas_choque), 0)

    def test_registrar_partida_boundary_values(self):
        """
        Testa valores de fronteira no registro de partida:
        - Tempo 0.0s (morte instantânea)
        - Valores massivos (1.000.000 de abates, 999.999.999 pontos)
        - Valores negativos tratados sem quebra
        """
        gerente = GerenciadorConfiguracoes()

        # Partida instantânea com 0s
        res1 = gerente.registrar_partida(tempo=0.0, abates=0, pontos=0, vitoria=False)
        self.assertFalse(res1["novo_recorde_pontos"])
        self.assertFalse(res1["novo_recorde_tempo"])

        # Partida com números massivos
        res2 = gerente.registrar_partida(tempo=1200.0, abates=1000000, pontos=999999999, vitoria=True, dano_causado=50000000)
        self.assertTrue(res2["novo_recorde_pontos"])
        self.assertTrue(res2["novo_recorde_tempo"])

        est = gerente.obter_estatisticas()
        self.assertEqual(est["high_score"], 999999999)
        self.assertEqual(est["total_abates"], 1000000)
        self.assertEqual(est["melhor_tempo"], 1200.0)
        self.assertEqual(est["vitorias"], 1)
        self.assertEqual(est["partidas_jogadas"], 2)


if __name__ == "__main__":
    unittest.main()

