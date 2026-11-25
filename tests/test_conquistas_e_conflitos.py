import json
import os
import tempfile
import unittest
from unittest.mock import patch

from src.sistemas.config_dados import CONFIGURACOES_GAMEPLAY, CONFIGURACOES_SISTEMA
from src.sistemas.config_sistema import GerenciadorConfiguracoes, SCHEMA_VERSION_ATUAL
from src.sistemas.conquistas_dados import (
    CHIPS_FIRMWARE,
    CONQUISTAS_CONTINUAS,
    CONQUISTAS_UNICAS,
)


class TestConquistasEConflitos(unittest.TestCase):
    def test_catalogo_28_configs_e_regra_r1(self):
        self.assertEqual(len(CONFIGURACOES_GAMEPLAY), 29)
        self.assertEqual(len(CONFIGURACOES_SISTEMA), 3)
        self.assertEqual(len(CHIPS_FIRMWARE), 8)
        self.assertEqual(len(CONQUISTAS_CONTINUAS), 5)
        self.assertEqual(len(CONQUISTAS_UNICAS), 11)

        for cid, cdef in CONFIGURACOES_GAMEPLAY.items():
            opcao_padrao = cdef.opcoes[str(cdef.valor_padrao)]
            self.assertEqual(
                opcao_padrao.modificadores,
                {},
                f"Config {cid} violou Regra R1 no padrão {cdef.valor_padrao}",
            )

    def test_matriz_exclusividade_mutua_completa(self):
        cfg = GerenciadorConfiguracoes()
        for cid in (
            "modo_wireframe",
            "graficos_qualidade",
            "movimento_mouse",
            "controles_tanque",
            "keybinds",
        ):
            cfg.desbloquear_config(cid)

        # modo_wireframe:ligado <-> graficos_qualidade:baixa
        self.assertTrue(cfg.definir_valor("graficos_qualidade", "baixa"))
        ok, conflitos = cfg.definir_valor_com_conflitos("modo_wireframe", "ligado")
        self.assertTrue(ok)
        self.assertIn(("graficos_qualidade", "alta"), conflitos)
        self.assertEqual(cfg.obter_valor("graficos_qualidade"), "alta")

        ok, conflitos = cfg.definir_valor_com_conflitos("graficos_qualidade", "baixa")
        self.assertTrue(ok)
        self.assertIn(("modo_wireframe", "desligado"), conflitos)
        self.assertEqual(cfg.obter_valor("modo_wireframe"), "desligado")

        # movimento_mouse:ligado <-> controles_tanque:ligado, keybinds:uma_mao, keybinds:pesadelo
        cfg.definir_valor("controles_tanque", "ligado")
        ok, conflitos = cfg.definir_valor_com_conflitos("movimento_mouse", "ligado")
        self.assertTrue(ok)
        self.assertIn(("controles_tanque", "desligado"), conflitos)
        self.assertEqual(cfg.obter_valor("controles_tanque"), "desligado")

        cfg.definir_valor("movimento_mouse", "desligado")
        cfg.definir_valor("keybinds", "uma_mao")
        ok, conflitos = cfg.definir_valor_com_conflitos("movimento_mouse", "ligado")
        self.assertTrue(ok)
        self.assertIn(("keybinds", "padrao"), conflitos)

        cfg.definir_valor("movimento_mouse", "desligado")
        cfg.definir_valor("keybinds", "pesadelo")
        ok, conflitos = cfg.definir_valor_com_conflitos("movimento_mouse", "ligado")
        self.assertTrue(ok)
        self.assertIn(("keybinds", "padrao"), conflitos)

        # controles_tanque:ligado <-> keybinds:uma_mao
        cfg.definir_valor("movimento_mouse", "desligado")
        cfg.definir_valor("keybinds", "uma_mao")
        ok, conflitos = cfg.definir_valor_com_conflitos("controles_tanque", "ligado")
        self.assertTrue(ok)
        self.assertIn(("keybinds", "padrao"), conflitos)

        ok, conflitos = cfg.definir_valor_com_conflitos("keybinds", "uma_mao")
        self.assertTrue(ok)
        self.assertIn(("controles_tanque", "desligado"), conflitos)

    def test_decisao_1_desbloqueio_conjunto_dash_e_smg_com_zero_io_intermediario(self):
        cfg = GerenciadorConfiguracoes()

        # Antes de 15 parries: dash_protocolo e dash_rastro fora do pool, smg_compacta travada
        ids_bloq_antes = {c.id for c in cfg.obter_bloqueadas()}
        self.assertNotIn("dash_protocolo", ids_bloq_antes)
        self.assertNotIn("dash_rastro", ids_bloq_antes)
        self.assertFalse(cfg.definir_loadout("slot2", "smg_compacta"))

        with patch.object(cfg, "salvar_arquivo", return_value=True) as mock_save:
            for i in range(14):
                total, desb = cfg.registrar_parry()
                self.assertEqual(total, i + 1)
                self.assertFalse(desb)
            mock_save.assert_not_called()

            total, desb = cfg.registrar_parry()
            self.assertEqual(total, 15)
            self.assertTrue(desb)
            mock_save.assert_called_once()

        self.assertTrue(cfg.sistema_conquistas.possui_recompensa("habilidade", "dash"))
        self.assertTrue(cfg.sistema_conquistas.possui_recompensa("arma", "smg_compacta"))
        self.assertTrue(cfg.estatisticas["dash_desbloqueado"])

        ids_bloq_depois = {c.id for c in cfg.obter_bloqueadas()}
        self.assertIn("dash_protocolo", ids_bloq_depois)
        self.assertIn("dash_rastro", ids_bloq_depois)
        self.assertTrue(cfg.definir_loadout("slot2", "smg_compacta"))
        self.assertEqual(cfg.loadout["slot2"], "smg_compacta")

    def test_decisao_7_exclusividade_conquista_level_up_e_opcoes_travadas(self):
        cfg = GerenciadorConfiguracoes()

        self.assertTrue(CONFIGURACOES_GAMEPLAY["latencia_ping"].exclusiva_conquista)
        self.assertNotIn("latencia_ping", {c.id for c in cfg.obter_configs_bloqueadas_level_up()})
        self.assertNotIn("latencia_ping", {c.id for c in cfg.obter_bloqueadas()})
        self.assertFalse(cfg.desbloquear_config("latencia_ping"))
        self.assertFalse(cfg.is_desbloqueada("latencia_ping"))

        cfg_via = GerenciadorConfiguracoes()
        self.assertTrue(cfg_via.desbloquear_config("latencia_ping", via_conquista=True))
        self.assertTrue(cfg_via.is_desbloqueada("latencia_ping"))

        # 4 opções avançadas travadas por conquista antes de qualquer conquista
        cfg.desbloquear_config("precisao_parry")
        cfg.desbloquear_config("dash_protocolo")
        cfg.desbloquear_config("dash_rastro")

        self.assertFalse(cfg.definir_valor("precisao_parry", "postura_riposte"))
        self.assertFalse(cfg.definir_valor("dash_protocolo", "sombra_espelho"))
        self.assertFalse(cfg.definir_valor("dash_protocolo", "rollback_estado"))
        self.assertFalse(cfg.definir_valor("dash_rastro", "thread_fantasma"))

        # Concluir conquistas
        cfg.sistema_conquistas.registrar_evento("vitoria_boss", 7)
        cfg.sincronizar_recompensas_conquistas()
        self.assertTrue(cfg.is_desbloqueada("latencia_ping"))
        self.assertTrue(cfg.definir_valor("latencia_ping", "ligado"))
        self.assertTrue(cfg.obter_modificadores().latencia_ping)

        cfg.sistema_conquistas.registrar_evento("parry", 120)
        cfg.sistema_conquistas.registrar_evento("just_dodge", 350)

        self.assertTrue(cfg.definir_valor("precisao_parry", "postura_riposte"))
        self.assertTrue(cfg.definir_valor("dash_protocolo", "sombra_espelho"))
        self.assertTrue(cfg.definir_valor("dash_protocolo", "rollback_estado"))
        self.assertTrue(cfg.definir_valor("dash_rastro", "thread_fantasma"))

    def test_decisao_4_save_v2_limpo_sobrescreve_legado_e_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, "save.json")
            # Grava save legado v1 (sem schema_version == 2)
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "desbloqueadas": ["zoom"],
                        "ativas": {"zoom": "75%"},
                        "estatisticas": {"high_score": 99999},
                    },
                    f,
                )

            cfg = GerenciadorConfiguracoes()
            self.assertTrue(cfg.carregar_arquivo(save_path))
            # Deve ter descartado legado e sobrescrito limpo em schema v2
            self.assertEqual(cfg.desbloqueadas, set())
            self.assertEqual(cfg.estatisticas["high_score"], 0)
            with open(save_path, "r", encoding="utf-8") as f:
                salvo = json.load(f)
            self.assertEqual(salvo["schema_version"], SCHEMA_VERSION_ATUAL)

            # Agora progride e faz round-trip v2
            cfg.sistema_conquistas.registrar_evento("parry", 50)
            cfg.sistema_conquistas.registrar_evento("abate", 1500)
            cfg.sistema_conquistas.registrar_evento("miniboss_rapido", 1, {"configs_nao_neutras": 2})
            cfg.sincronizar_recompensas_conquistas()
            self.assertEqual(cfg.sistema_conquistas.slots_firmware_max, 2)
            self.assertTrue(cfg.sistema_conquistas.equipar_firmware("gatilho_duplo"))
            self.assertTrue(cfg.definir_loadout("slot2", "smg_compacta"))
            self.assertTrue(cfg.sistema_conquistas.alternar_fixada("depurador_escritorio"))
            self.assertTrue(cfg.salvar_arquivo(save_path))

            cfg2 = GerenciadorConfiguracoes()
            self.assertTrue(cfg2.carregar_arquivo(save_path))
            self.assertEqual(cfg2.loadout["slot2"], "smg_compacta")
            self.assertEqual(cfg2.sistema_conquistas.slots_firmware_max, 2)
            self.assertEqual(cfg2.sistema_conquistas.modificadores_equipados, ["gatilho_duplo"])
            self.assertLessEqual(len(cfg2.sistema_conquistas.fixadas), 3)
            self.assertIn("depurador_escritorio", cfg2.sistema_conquistas.fixadas)
            self.assertTrue(len(cfg2.sistema_conquistas.obter_resumo_fixadas()) >= 1)


if __name__ == "__main__":
    unittest.main()
