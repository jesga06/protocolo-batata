"""
Testes Unitários — Milestone 1: Neutral Default State & Save/Fallback Enforcement (R1)
SSOT: CONFIGURACOES.md, PROJECT.md, architecture_cache.md
Valida:
1. Todas as 20 configurações de gameplay em config_dados.py possuem modificadores vazios em seu valor padrão.
2. GerenciadorConfiguracoes inicializado no estado padrão produz ModificadoresGameplay neutros (multiplicadores 1.0, booleans False).
3. ModalLevelUp ao desbloquear um card de configuração NÃO altera o valor padrão neutro para outra opção ativa.
4. O arquivo data/save.json inicia em estado limpo e neutro (desbloqueadas: []).
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.sistemas.config_dados import CONFIGURACOES_GAMEPLAY, CONFIGURACOES_SISTEMA
from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.entidades.jogador import Jogador
from src.ui.modal_level_up import ModalLevelUp


class TestNeutralDefaultStateAndSave(unittest.TestCase):
    """Testa se o estado neutro das 20 configurações é rigorosamente respeitado."""

    def setUp(self):
        self.save_path = os.path.join(PROJECT_ROOT, "data", "save.json")
        self._tmpdir = tempfile.TemporaryDirectory()
        self.temp_save_path = os.path.join(self._tmpdir.name, "save.json")
        self._patcher_const = patch("src.utils.constantes.SAVE_FILE_PATH", self.temp_save_path)
        self._patcher_modal = patch("src.ui.modal_level_up.SAVE_FILE_PATH", self.temp_save_path)
        self._patcher_const.start()
        self._patcher_modal.start()

    def tearDown(self):
        self._patcher_modal.stop()
        self._patcher_const.stop()
        self._tmpdir.cleanup()

    def test_all_20_gameplay_configs_have_empty_neutral_modifiers(self):
        """Verifica que cada uma das 29 configs possui modificadores vazios ({}) no valor padrão."""
        self.assertEqual(len(CONFIGURACOES_GAMEPLAY), 29, "Devem existir exatamente 29 configurações de gameplay.")

        for cid, cdef in CONFIGURACOES_GAMEPLAY.items():
            val_padrao = str(cdef.valor_padrao)
            self.assertIn(
                val_padrao,
                cdef.opcoes,
                f"Config '{cid}' deve conter seu valor_padrao '{val_padrao}' no dicionário de opções."
            )
            mods_padrao = cdef.opcoes[val_padrao].modificadores
            self.assertEqual(
                mods_padrao,
                {},
                f"Config '{cid}' no valor padrão '{val_padrao}' DEVE ter modificadores vazios {{}}, obtido: {mods_padrao}"
            )

    def test_gerenciador_default_modifiers_are_strictly_neutral(self):
        """Verifica que o GerenciadorConfiguracoes inicial gera ModificadoresGameplay neutros."""
        mgr = GerenciadorConfiguracoes()
        mods = mgr.obter_modificadores()

        # Multiplicadores de jogador / combate
        self.assertEqual(mods.vel_jogador_mult, 1.0)
        self.assertEqual(mods.dano_armas_mult, 1.0)
        self.assertEqual(mods.dano_explosivos_mult, 1.0)
        self.assertEqual(mods.hitbox_projeteis_mult, 1.0)
        self.assertEqual(mods.critico_chance, 0.0)
        self.assertEqual(mods.critico_mult, 1.0)

        # Multiplicadores de inimigos
        self.assertEqual(mods.hp_inimigos_mult, 1.0)
        self.assertEqual(mods.vel_inimigos_mult, 1.0)
        self.assertEqual(mods.dano_inimigos_mult, 1.0)
        self.assertEqual(mods.dano_fora_visao_mult, 1.0)

        # Multiplicadores de progressão e drops
        self.assertEqual(mods.xp_ganho_mult, 1.0)
        self.assertEqual(mods.drops_valor_mult, 1.0)
        self.assertEqual(mods.drop_chance_bonus, 0.0)
        self.assertEqual(mods.drop_chance_mult, 1.0)

        # Booleans e mecânicas
        self.assertFalse(mods.auto_dano)
        self.assertFalse(mods.loot_enriquecido)

    def test_save_json_initial_state_compliance(self):
        """Verifica se o save.json do jogo está presente e inicializado com estado limpo e neutro."""
        self.assertTrue(os.path.exists(self.save_path), "Arquivo data/save.json deve existir.")

        with open(self.save_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("desbloqueadas", data)
        self.assertEqual(data["desbloqueadas"], [], "save.json inicial deve ter 'desbloqueadas': [].")

        self.assertIn("ativas", data)
        for cid, cdef in CONFIGURACOES_GAMEPLAY.items():
            self.assertIn(cid, data["ativas"], f"save.json deve mapear a config '{cid}'.")
            val_salvo = str(data["ativas"][cid])
            self.assertEqual(
                val_salvo,
                str(cdef.valor_padrao),
                f"save.json para '{cid}' deve ter o valor neutro '{cdef.valor_padrao}', encontrado '{val_salvo}'."
            )

    def test_modal_unlock_keeps_neutral_option_selected(self):
        """Desbloquear uma configuração no ModalLevelUp NÃO deve forçar uma opção ativa não-neutra."""
        mgr = GerenciadorConfiguracoes()
        jogador = Jogador(x=100, y=100)
        modal = ModalLevelUp(mgr, jogador)

        cid = "damage_numbers"
        cdef = CONFIGURACOES_GAMEPLAY[cid]
        padrao = str(cdef.valor_padrao)

        self.assertFalse(mgr.is_desbloqueada(cid))
        self.assertEqual(mgr.obter_valor(cid), padrao)

        card_config = {
            "tipo": "config",
            "config_id": cid,
            "nome": cdef.nome,
            "categoria": "Configuração",
            "icone_asset": "icon_damage_numbers",
            "buffs": ["+15% Chance Crítica (2x dano)"],
            "nerfs": ["Poluição visual"],
            "flavor_text": "Números flutuantes de dano"
        }
        modal.cards_sorteados = [card_config]
        modal.ativo = True
        modal.fila_level_ups = 1

        # Seleciona o card da configuração
        modal.selecionar_card(0)

        # A configuração agora está desbloqueada, mas seu valor ativo DEVE continuar sendo o neutro
        self.assertTrue(mgr.is_desbloqueada(cid))
        self.assertEqual(
            mgr.obter_valor(cid),
            padrao,
            f"Ao desbloquear '{cid}', seu valor deve permanecer no neutro '{padrao}', não forçar opção ativa."
        )
        # Os modificadores continuam neutros
        mods = mgr.obter_modificadores()
        self.assertEqual(mods.critico_chance, 0.0)


if __name__ == "__main__":
    unittest.main()
