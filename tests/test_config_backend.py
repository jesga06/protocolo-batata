"""
Testes Unitários do Backend de Configurações (R3) — Protocolo: Batata
SSOT: CONFIGURACOES.md
Valida o catálogo de 20 configs de gameplay + 5 configs de sistema,
a regra fundamental de neutralidade antes do desbloqueio,
o empilhamento multiplicativo puro de atributos e a persistência.
"""

import os
import sys
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.sistemas.config_dados import (
    CONFIGURACOES_GAMEPLAY, CONFIGURACOES_SISTEMA, TODAS_CONFIGURACOES
)
from src.sistemas.config_efeitos import calcular_modificadores, ModificadoresGameplay
from src.sistemas.config_sistema import GerenciadorConfiguracoes


class TestConfigCatalogAndStructure(unittest.TestCase):
    """Testa a integridade do catálogo e definições de configurações."""

    def test_all_25_configs_cataloged(self):
        """Verifica a presença exata de 30 configs de gameplay e 3 sistêmicas de áudio (33 total)."""
        self.assertEqual(len(CONFIGURACOES_GAMEPLAY), 30)
        self.assertEqual(len(CONFIGURACOES_SISTEMA), 3)
        self.assertEqual(len(TODAS_CONFIGURACOES), 33)

        # Verifica configs de sistema de áudio e ausência de stubs S4/S5
        self.assertIn("volume_master", CONFIGURACOES_SISTEMA)
        self.assertIn("volume_musica", CONFIGURACOES_SISTEMA)
        self.assertIn("volume_sfx", CONFIGURACOES_SISTEMA)
        self.assertFalse(CONFIGURACOES_SISTEMA["volume_master"].is_gameplay)
        self.assertNotIn("filtro_daltonico", CONFIGURACOES_SISTEMA)
        self.assertNotIn("escala_global", CONFIGURACOES_SISTEMA)

        # Verifica presença das 20 de gameplay
        chaves_gameplay_esperadas = [
            "fps_cap", "graficos_qualidade", "resolucao", "vsync", "screen_shake",
            "motion_blur", "hud", "damage_numbers", "zoom", "movimento_mouse",
            "keybinds", "suavizacao_camera", "auto_fire", "inimigos_ranged",
            "coleta_inimiga", "velocidade_inimigos", "vida_inimigos",
            "iluminacao", "cores_invertidas", "fogo_amigo",
            "precisao_parry", "efeito_parry", "controles_tanque"
        ]
        for chave in chaves_gameplay_esperadas:
            self.assertIn(chave, CONFIGURACOES_GAMEPLAY, f"Config {chave} ausente no catálogo!")


class TestModifierCalculations(unittest.TestCase):
    """Testa a lógica matemática e o isolamento de neutralidade de modificadores."""

    def test_locked_baseline_neutrality(self):
        """
        Regra Fundamental: Antes de desbloquear, nenhuma configuração pode conceder bônus.
        Mesmo se configs_ativas tiver valores alterados, se desbloqueadas for vazio,
        o resultado deve ser estritamente o baseline neutro (1.0x em todos os multiplicadores).
        """
        ativas_alteradas = {
            "fps_cap": "15",
            "auto_fire": "desligado",
            "fogo_amigo": "ligado",
            "cores_invertidas": "ligado",
            "hud": "desligado",
            "coleta_inimiga": "ligado"
        }

        # Desbloqueadas vazio -> Baseline Neutro
        mods = calcular_modificadores(configs_desbloqueadas=set(), configs_ativas=ativas_alteradas)

        self.assertAlmostEqual(mods.dano_armas_mult, 1.0)
        self.assertAlmostEqual(mods.vel_jogador_mult, 1.0)
        self.assertAlmostEqual(mods.xp_ganho_mult, 1.0)
        self.assertAlmostEqual(mods.drop_chance_bonus, 0.0)
        self.assertAlmostEqual(mods.drop_chance_mult, 1.0)
        self.assertAlmostEqual(mods.drops_valor_mult, 1.0)
        self.assertAlmostEqual(mods.hp_inimigos_mult, 1.0)
        self.assertAlmostEqual(mods.vel_inimigos_mult, 1.0)
        self.assertAlmostEqual(mods.dano_inimigos_mult, 1.0)
        self.assertFalse(mods.auto_dano)
        self.assertFalse(mods.loot_enriquecido)

    def test_multiplicative_stacking_damage(self):
        """
        Testa o empilhamento multiplicativo máximo de dano de armas:
        - auto_fire ("desligado") -> 1.15
        - keybinds ("pesadelo") -> 1.30
        - cores_invertidas ("ligado") -> 1.20
        - fogo_amigo ("ligado") -> 1.25
        - zoom ("150%") -> 1.20
        Total: 1.15 * 1.30 * 1.20 * 1.25 * 1.20 = 2.691x
        """
        desbloqueadas = {"auto_fire", "keybinds", "cores_invertidas", "fogo_amigo", "zoom"}
        ativas = {
            "auto_fire": "desligado",
            "keybinds": "pesadelo",
            "cores_invertidas": "ligado",
            "fogo_amigo": "ligado",
            "zoom": "150%"
        }

        mods = calcular_modificadores(desbloqueadas, ativas)
        # v2.0: auto_fire(1.15) * keybinds(1.30) * fogo_amigo(1.25) = 1.86875
        esperado_dano = 1.15 * 1.30 * 1.25
        self.assertAlmostEqual(mods.dano_armas_mult, esperado_dano, places=5)
        self.assertTrue(mods.auto_dano)
        self.assertTrue(mods.polaridade_invertida)

    def test_multiplicative_stacking_speed_and_xp(self):
        """
        Testa velocidade do jogador e ganho de XP (v2.0 SSOT).
        """
        # Teste Velocidade: motion_blur ("ligado", 1.15) * keybinds ("arrow_keys", 1.15) = 1.3225
        desbloqueadas_vel = {"vsync", "motion_blur", "suavizacao_camera", "keybinds"}
        ativas_vel = {
            "vsync": "desligado",
            "motion_blur": "ligado",
            "suavizacao_camera": "desligado",
            "keybinds": "arrow_keys"
        }
        mods_vel = calcular_modificadores(desbloqueadas_vel, ativas_vel)
        esperado_vel = 1.15 * 1.15
        self.assertAlmostEqual(mods_vel.vel_jogador_mult, esperado_vel, places=5)

        # Teste XP: hud ("desligado", 1.25) * keybinds ("uma_mao", 1.20) * velocidade_inimigos ("+50%", 1.30) = 1.95
        desbloqueadas_xp = {"hud", "keybinds", "velocidade_inimigos"}
        ativas_xp = {
            "hud": "desligado",
            "keybinds": "uma_mao",
            "velocidade_inimigos": "+50%"
        }
        mods_xp = calcular_modificadores(desbloqueadas_xp, ativas_xp)
        esperado_xp = 1.25 * 1.20 * 1.30
        self.assertAlmostEqual(mods_xp.xp_ganho_mult, esperado_xp, places=5)


class TestConfigManager(unittest.TestCase):
    """Testa a máquina de estados, desbloqueios e persistência do GerenciadorConfiguracoes."""

    def test_unlock_and_state_persistence(self):
        manager = GerenciadorConfiguracoes()

        # Inicialmente tudo está bloqueado
        self.assertFalse(manager.is_desbloqueada("fps_cap"))
        self.assertEqual(len(manager.obter_desbloqueadas()), 0)
        self.assertEqual(len(manager.obter_bloqueadas()), 27)

        # Tentativa de alterar config bloqueada falha
        self.assertFalse(manager.definir_valor("fps_cap", "15"))
        self.assertEqual(manager.obter_valor("fps_cap"), "ilimitado")

        # Desbloqueia fps_cap e altera valor
        self.assertTrue(manager.desbloquear_config("fps_cap"))
        self.assertTrue(manager.is_desbloqueada("fps_cap"))
        self.assertTrue(manager.definir_valor("fps_cap", "15"))
        self.assertEqual(manager.obter_valor("fps_cap"), "15")

        # Modificadores refletem o valor 15 FPS (dano inimigos 0.7225, vel inimigos 0.81)
        mods = manager.obter_modificadores()
        self.assertAlmostEqual(mods.dano_inimigos_mult, 0.7225)
        self.assertAlmostEqual(mods.vel_inimigos_mult, 0.81)

        # Serializa e restaura
        dados = manager.to_dict()
        novo_manager = GerenciadorConfiguracoes()
        novo_manager.from_dict(dados)

        self.assertTrue(novo_manager.is_desbloqueada("fps_cap"))
        self.assertEqual(novo_manager.obter_valor("fps_cap"), "15")
        mods_restaurados = novo_manager.obter_modificadores()
        self.assertAlmostEqual(mods_restaurados.dano_inimigos_mult, 0.7225)


if __name__ == "__main__":
    unittest.main()
