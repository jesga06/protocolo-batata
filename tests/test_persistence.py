"""
Testes Unitários — Persistência de Metaprogressão e Estatísticas Globais
Valida o esquema de dados de estatísticas, serialização JSON, atualização de recordes
e garantia de não-sobrescrita de dados históricos.
"""

import os
import tempfile
import unittest
from src.sistemas.config_sistema import GerenciadorConfiguracoes


class TestPersistence(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        self.caminho_save = self.temp_file.name

    def tearDown(self):
        if os.path.exists(self.caminho_save):
            os.remove(self.caminho_save)

    def test_inicializacao_padrao_estatisticas(self):
        """Verifica se o gerenciador inicializa o dicionário de estatísticas com valores zerados."""
        gerente = GerenciadorConfiguracoes()
        est = gerente.obter_estatisticas()

        self.assertIsInstance(est, dict)
        self.assertEqual(est["high_score"], 0)
        self.assertEqual(est["melhor_tempo"], 0.0)
        self.assertEqual(est["total_abates"], 0)
        self.assertEqual(est["partidas_jogadas"], 0)
        self.assertEqual(est["vitorias"], 0)
        self.assertEqual(est["historico"], [])

    def test_compatibilidade_save_legado_sem_estatisticas(self):
        """Garante que carregar um save antigo sem a chave 'estatisticas' não quebra o sistema."""
        dados_legados = {
            "desbloqueadas": ["fps_cap"],
            "ativas": {"fps_cap": "30"},
            "sistema_configs": {"volume_master": 80}
        }
        gerente = GerenciadorConfiguracoes()
        gerente.from_dict(dados_legados)

        est = gerente.obter_estatisticas()
        self.assertEqual(est["high_score"], 0)
        self.assertEqual(est["melhor_tempo"], 0.0)
        self.assertTrue(gerente.is_desbloqueada("fps_cap"))

    def test_registro_partida_derrota_e_recordes(self):
        """Testa o registro de uma partida regular com atualização de recordes de pontuação e tempo."""
        gerente = GerenciadorConfiguracoes()

        resultado = gerente.registrar_partida(
            tempo=185.5,
            abates=42,
            pontos=5200,
            vitoria=False,
            dano_causado=1200
        )

        self.assertTrue(resultado["novo_recorde_pontos"])
        self.assertTrue(resultado["novo_recorde_tempo"])

        est = gerente.obter_estatisticas()
        self.assertEqual(est["high_score"], 5200)
        self.assertEqual(est["melhor_tempo"], 185.5)
        self.assertEqual(est["total_abates"], 42)
        self.assertEqual(est["partidas_jogadas"], 1)
        self.assertEqual(est["vitorias"], 0)
        self.assertEqual(len(est["historico"]), 1)
        self.assertEqual(est["historico"][0]["pontos"], 5200)
        self.assertEqual(est["historico"][0]["vitoria"], False)

    def test_registro_partida_vitoria(self):
        """Testa o registro de vitória aos 10 minutos."""
        gerente = GerenciadorConfiguracoes()

        gerente.registrar_partida(tempo=300.0, abates=50, pontos=10000, vitoria=False)
        resultado2 = gerente.registrar_partida(tempo=600.0, abates=120, pontos=25000, vitoria=True)

        self.assertTrue(resultado2["novo_recorde_pontos"])
        self.assertTrue(resultado2["novo_recorde_tempo"])

        est = gerente.obter_estatisticas()
        self.assertEqual(est["vitorias"], 1)
        self.assertEqual(est["partidas_jogadas"], 2)
        self.assertEqual(est["total_abates"], 170)
        self.assertEqual(est["high_score"], 25000)
        self.assertEqual(est["melhor_tempo"], 600.0)

    def test_preservacao_estatisticas_ao_salvar_configuracoes(self):
        """Garante que alterar configurações e salvar o arquivo preserva integralmente as estatísticas."""
        gerente1 = GerenciadorConfiguracoes()
        gerente1.desbloquear_config("fps_cap")
        gerente1.definir_valor("fps_cap", "45")
        gerente1.registrar_partida(tempo=450.0, abates=85, pontos=18000, vitoria=False)
        gerente1.salvar_arquivo(self.caminho_save)

        # Simula carregamento em nova instância do jogo
        gerente2 = GerenciadorConfiguracoes()
        carregou = gerente2.carregar_arquivo(self.caminho_save)
        self.assertTrue(carregou)

        est2 = gerente2.obter_estatisticas()
        self.assertEqual(est2["high_score"], 18000)
        self.assertEqual(est2["melhor_tempo"], 450.0)
        self.assertEqual(est2["total_abates"], 85)
        self.assertEqual(gerente2.obter_valor("fps_cap"), "45")

        # Modifica outra config de sistema e salva novamente
        gerente2.definir_valor("volume_master", 50)
        gerente2.salvar_arquivo(self.caminho_save)

        # Recarrega em gerente3 e confirma que estatísticas permanecem intactas
        gerente3 = GerenciadorConfiguracoes()
        gerente3.carregar_arquivo(self.caminho_save)
        est3 = gerente3.obter_estatisticas()
        self.assertEqual(est3["high_score"], 18000)
        self.assertEqual(est3["total_abates"], 85)
        self.assertEqual(gerente3.obter_valor("volume_master"), 50)

    def test_historico_limite_20_partidas(self):
        """Verifica se o histórico mantém no máximo as últimas 20 partidas registradas."""
        gerente = GerenciadorConfiguracoes()
        for i in range(25):
            gerente.registrar_partida(tempo=float(i + 1), abates=i, pontos=i * 100)

        est = gerente.obter_estatisticas()
        self.assertEqual(len(est["historico"]), 20)
        self.assertEqual(est["historico"][-1]["pontos"], 2400)


if __name__ == "__main__":
    unittest.main()
