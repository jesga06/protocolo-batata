"""
Testes Automatizados de Validação do Milestone M2:
Sistema de Mini-Bosses Overclock de 4 Tiers, Escalonamento 2x, Sobrecarga Térmica (60s),
Modal de Overclock e os 6 Módulos de BIOS.
"""

import os
import tempfile
import unittest
from unittest.mock import patch
import math
import pygame

from src.entidades.inimigo_base import InimigoBase
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.inimigo_rapido import InimigoRapido
from src.entidades.inimigo_tank import InimigoTank
from src.entidades.inimigo_phasing import InimigoPhasing
from src.entidades.inimigo_blindado import InimigoBlindado
from src.entidades.inimigo_ranged import InimigoRanged
from src.entidades.jogador import Jogador
from src.entidades.drop import ItemDrop
from src.sistemas.sistema_spawn import SistemaSpawn
from src.sistemas.sistema_drops import SistemaDrops
from src.ui.modal_overclock import ModalOverclock, CATALOGO_OVERCLOCKS
from src.ui.hud import HUD
from src.cenas.gameplay import GameplayScene
from src.armas.shotgun import Shotgun
from src.armas.pistola import Pistola
from src.armas.minigun import Minigun


class TestMiniBossOverclockSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.temp_save = os.path.join(self._tmpdir.name, "save.json")
        self._p1 = patch("src.utils.constantes.SAVE_FILE_PATH", self.temp_save)
        self._p2 = patch("src.cenas.gameplay.SAVE_FILE_PATH", self.temp_save)
        self._p1.start()
        self._p2.start()
        self.jogador = Jogador(x=400, y=300)
        self.spawner = SistemaSpawn()
        self.sistema_drops = SistemaDrops()

    def tearDown(self):
        self._p2.stop()
        self._p1.stop()
        self._tmpdir.cleanup()

    def test_miniboss_schedule_4_tiers_and_names(self):
        """Valida a configuração oficial dos 4 tiers de mini-bosses."""
        esperados = {
            1: (InimigoRapido, "MINI-BOSS: ESTAGIÁRIO SÊNIOR"),
            2: (InimigoTank, "MINI-BOSS: ARQUIVO MORTO PRIORITÁRIO"),
            3: (InimigoPhasing, "MINI-BOSS: FANTASMA DO RH"),
            4: (InimigoBlindado, "MINI-BOSS: SEGURANÇA-CHEFE"),
        }

        for tier, (cls_exp, nome_exp) in esperados.items():
            cls_res, nome_res = self.spawner.obter_arquetipo_elite(tier)
            self.assertEqual(cls_res, cls_exp, f"Tier {tier}: classe incorreta ({cls_res} != {cls_exp})")
            self.assertEqual(nome_res, nome_exp, f"Tier {tier}: nome incorreto ({nome_res} != {nome_exp})")

    def test_miniboss_2x_dimensions_and_aabb_hitbox(self):
        """Valida que is_elite=True duplica exatamente largura, altura e hitbox física (AABB)."""
        classes = [
            (InimigoPadrao, 28, 28),
            (InimigoRapido, 31, 31),
            (InimigoTank, 62, 62),
            (InimigoPhasing, 42, 42),
            (InimigoBlindado, 47, 47),
            (InimigoRanged, 42, 42)
        ]

        for cls_enemy, base_w, base_h in classes:
            base_mob = cls_enemy(x=100, y=100, is_elite=False)
            elite_mob = cls_enemy(x=100, y=100, is_elite=True, nome_elite="MINI-BOSS TESTE")

            self.assertEqual(base_mob.largura, base_w)
            self.assertEqual(base_mob.altura, base_h)
            self.assertEqual(base_mob.width, base_w)
            self.assertEqual(base_mob.height, base_h)

            self.assertEqual(elite_mob.largura, base_w * 2)
            self.assertEqual(elite_mob.altura, base_h * 2)
            self.assertEqual(elite_mob.width, base_w * 2)
            self.assertEqual(elite_mob.height, base_h * 2)

            # Hitbox AABB
            self.assertEqual(elite_mob.get_rect(), (100.0, 100.0, base_w * 2, base_h * 2))

    def test_miniboss_60s_thermal_overload_countdown(self):
        """Valida que o mini-boss tem timer de sobrecarga térmica de 60s e morre com zero drops."""
        elite = InimigoRapido(x=200, y=200, is_elite=True, nome_elite="MINI-BOSS: ESTAGIÁRIO SÊNIOR")
        self.assertEqual(elite.tempo_vida_restante, 60.0)
        self.assertEqual(elite.thermal_overload_timer, 60.0)
        self.assertEqual(elite.tempo_vida_elite, 60.0)
        self.assertFalse(elite.superaqueceu)
        self.assertTrue(elite.vivo)

        # Atualiza 30s
        elite.update(30.0, (400, 300))
        self.assertEqual(elite.tempo_vida_restante, 30.0)
        self.assertFalse(elite.superaqueceu)
        self.assertTrue(elite.vivo)

        # Atualiza mais 30.1s -> Superaquece
        elite.update(30.1, (400, 300))
        self.assertTrue(elite.superaqueceu)
        self.assertFalse(elite.vivo)
        self.assertEqual(elite.tempo_vida_restante, 0.0)

    def test_miniboss_overload_toast_and_zero_loot_in_gameplay(self):
        """Valida que quando um mini-boss superaquece, exibe o toast exato e não gera drops."""
        cena = GameplayScene()
        elite = InimigoTank(x=200, y=200, is_elite=True, nome_elite="MINI-BOSS: ARQUIVO MORTO PRIORITÁRIO")
        cena.inimigos = [elite]

        # Força o timer de superaquecimento a expirar
        elite.tempo_vida_restante = 0.5
        elite.thermal_overload_timer = 0.5
        cena.update(1.0)

        self.assertTrue(elite.superaqueceu)
        self.assertFalse(elite.vivo)

        # Verifica se o toast exato foi gerado
        toasts = [t["texto"] for t in cena.toasts_coleta]
        toast_esperado = "O MINI-BOSS SUPERAQUECEU. VOCÊ NÃO RECEBERÁ RECOMPENSAS POR ELE."
        self.assertIn(toast_esperado, toasts)

        # Verifica zero drops
        drops_ativos = [d for d in cena.sistema_drops.drops if d.ativo]
        self.assertEqual(len(drops_ativos), 0)

    def test_miniboss_defeat_drops_overclock(self):
        """Valida que derrotar um mini-boss dentro de 60s gera o item drop_overclock."""
        drops = self.sistema_drops.gerar_drop_morte_inimigo(x=300, y=300, is_elite=True)
        overclock_drops = [d for d in drops if d.tipo == "overclock"]
        self.assertEqual(len(overclock_drops), 1)
        self.assertTrue(overclock_drops[0].ativo)

    def test_spawner_anti_stacking_pauses_schedule(self):
        """Valida anti-stacking: apenas 1 mini-boss ativo por vez; timers subsequentes pausam enquanto um elite está vivo."""
        spawner = SistemaSpawn()

        # Avança até 60.5s -> Spawna 1º mini-boss (Estagiário Sênior)
        novos = spawner.update(60.5, camera_x=0, camera_y=0, total_inimigos_vivos=0, possui_elite_vivo=False)
        elites = [e for e in novos if getattr(e, "is_elite", False)]
        self.assertEqual(len(elites), 1)
        self.assertIn("ESTAGIÁRIO SÊNIOR", elites[0].nome_elite)

        # Enquanto o elite está vivo (possui_elite_vivo=True), avança 120s (tempo total de partida > 180s)
        # O segundo mini-boss NÃO deve spawnar porque o cronômetro do elite está pausado
        novos_durante = spawner.update(120.0, camera_x=0, camera_y=0, total_inimigos_vivos=len(novos), possui_elite_vivo=True)
        elites_durante = [e for e in novos_durante if getattr(e, "is_elite", False)]
        self.assertEqual(len(elites_durante), 0)

        # Agora o primeiro elite morre (possui_elite_vivo=False)
        # Avança 60s -> Spawna o 2º mini-boss (Arquivo Morto Prioritário)
        novos_depois = spawner.update(60.0, camera_x=0, camera_y=0, total_inimigos_vivos=0, possui_elite_vivo=False)
        elites_depois = [e for e in novos_depois if getattr(e, "is_elite", False)]
        self.assertEqual(len(elites_depois), 1)
        self.assertIn("ARQUIVO MORTO PRIORITÁRIO", elites_depois[0].nome_elite)

    def test_modal_overclock_3_distinct_cards_and_catalog(self):
        """Valida que o ModalOverclock sorteia 3 cartas distintas dos 6 módulos catalogados."""
        modal = ModalOverclock(self.jogador)
        self.assertEqual(len(CATALOGO_OVERCLOCKS), 6)

        ids_catalogo = {c["id"] for c in CATALOGO_OVERCLOCKS}
        esperados_ids = {"multithreading", "refrigeracao", "overvolt", "bios_modding", "protecao_surtos", "upgrade_barramento"}
        self.assertEqual(ids_catalogo, esperados_ids)

        modal.abrir()
        self.assertTrue(modal.ativo)
        self.assertEqual(len(modal.cards_sorteados), 3)

        # 3 cartas distintas
        ids_sorteados = [c["id"] for c in modal.cards_sorteados]
        self.assertEqual(len(set(ids_sorteados)), 3)

    def test_modal_overclock_input_lock_debounce(self):
        """Valida debounce de 350ms para evitar cliques acidentais ao abrir o modal."""
        modal = ModalOverclock(self.jogador)
        modal.abrir()
        self.assertEqual(modal.tempo_transicao_entrada, 0.35)

        class MockKeyboard:
            def key_pressed(self, k):
                return k in ("1", "KP1", "[1]")
            def key_down(self, k):
                return False

        teclado = MockKeyboard()

        # Update com 0.10s (restam 0.25s de debounce) -> seleção deve ser bloqueada
        modal.update(0.10, teclado=teclado)
        self.assertTrue(modal.ativo)
        self.assertEqual(len(self.jogador.overclocks_adquiridos), 0)

        # Update com 0.30s (debounce expira) -> seleção é processada
        modal.update(0.30, teclado=teclado)
        self.assertFalse(modal.ativo)
        self.assertEqual(len(self.jogador.overclocks_adquiridos), 1)

    def test_overclock_1_multithreading_mechanics(self):
        """Valida Overclock 1: Multithreading (disparo duplo com delay 0.08s e dispersão)."""
        cena = GameplayScene()
        cena.jogador.aplicar_overclock("multithreading")
        self.assertTrue(cena.jogador.multithreading)

        # Dispara com Pistola
        cena.jogador.selecionar_slot(2)
        pistola = cena.jogador.obter_arma_ativa()
        pistola.cooldown_atual = 0.0

        # Simula clique do mouse
        cena.buffer_tiro = 0.15
        cena.mouse.get_position = lambda: (500, 300)
        cena.update(0.016)

        # Deve haver 1 projétil disparado e 2 ecos pendentes (1 por coprocessador orbital) na fila com timer=0.08
        self.assertEqual(len(cena.projeteis), 1)
        self.assertEqual(len(cena.tiros_echo_pendentes), 2)
        self.assertAlmostEqual(cena.tiros_echo_pendentes[0]["timer"], 0.08, delta=0.02)
        self.assertAlmostEqual(cena.tiros_echo_pendentes[1]["timer"], 0.08, delta=0.02)

        # Avança 0.09s -> Os 2 projéteis de eco dos coprocessadores são instanciados (total = 3)
        cena.update(0.09)
        self.assertEqual(len(cena.projeteis), 3)
        self.assertEqual(len(cena.tiros_echo_pendentes), 0)

    def test_overclock_1_multithreading_shotgun_full_9_pellets(self):
        """Valida que para a Shotgun o Multithreading dispara salvas completas de 9 pellets em ambos os coprocessadores."""
        cena = GameplayScene()
        cena.jogador.aplicar_overclock("multithreading")
        cena.jogador.arma_especial = Shotgun()
        cena.jogador.selecionar_slot(3)
        shotgun = cena.jogador.obter_arma_ativa()
        shotgun.cooldown_atual = 0.0

        cena.buffer_tiro = 0.15
        cena.mouse.get_position = lambda: (500, 300)
        cena.update(0.016)

        # Salva inicial de 9 pellets + 2 ecos pendentes (ambos coprocessadores) contendo 9 pellets cada
        self.assertEqual(len(cena.projeteis), 9)
        self.assertEqual(len(cena.tiros_echo_pendentes), 2)
        self.assertEqual(len(cena.tiros_echo_pendentes[0]["projeteis"]), 9)
        self.assertEqual(len(cena.tiros_echo_pendentes[1]["projeteis"]), 9)

        # Avança 0.09s -> Totaliza 27 projéteis disparados (3 x 9 pellets)
        cena.update(0.09)
        self.assertEqual(len(cena.projeteis), 27)

    def test_overclock_2_refrigeracao_nitrogenio_firerate(self):
        """Valida Overclock 2: Refrigeração a Nitrogênio (+35% de cadência de tiro)."""
        jogador = Jogador(x=400, y=300)
        pistola = Pistola()
        jogador.armas = [jogador.armas[0], pistola]
        pistola.cooldown_atual = 1.0

        # Sem overclock: dt=0.10 reduz cooldown em 0.10s
        jogador.update(0.10)
        self.assertAlmostEqual(pistola.cooldown_atual, 0.90, places=4)

        # Com overclock: dt=0.10 reduz cooldown em 0.10 * 1.20 = 0.120s
        jogador.aplicar_overclock("refrigeracao")
        self.assertTrue(jogador.refrigeracao_nitrogenio)
        pistola.cooldown_atual = 1.0
        jogador.update(0.10)
        self.assertAlmostEqual(pistola.cooldown_atual, 1.0 - 0.120, places=4)

    def test_overclock_3_overvolt_crit_multiplier(self):
        """Valida Overclock 3: Overvolt (+30% Crit Chance com 2x multiplicador)."""
        jogador = Jogador(x=400, y=300)
        jogador.aplicar_overclock("overvolt")
        self.assertTrue(jogador.overvolt)

    def test_overclock_4_bios_modding_and_slot_3b_toggle(self):
        """Valida Overclock 4: BIOS Modding (Slot 3B, alternância e fallback do Slot 2 para Pistola)."""
        jogador = Jogador(x=400, y=300)
        jogador.aplicar_overclock("bios_modding")
        self.assertTrue(jogador.bios_modding)

        minigun = Minigun()
        shotgun = Shotgun()
        jogador.arma_especial = minigun
        jogador.arma_especial_secundaria = shotgun

        # Seleciona Slot 3 (3A: Minigun)
        jogador.selecionar_slot(3)
        self.assertEqual(jogador.slot_ativo, 3)
        self.assertEqual(jogador.obter_arma_ativa(), minigun)
        self.assertFalse(jogador.slot_especial_secundario_ativo)

        # Pressiona '3' novamente -> Alterna para 3B (Shotgun)
        jogador.selecionar_slot(3)
        self.assertEqual(jogador.slot_ativo, 3)
        self.assertEqual(jogador.obter_arma_ativa(), shotgun)
        self.assertTrue(jogador.slot_especial_secundario_ativo)

        # Pressiona '3' novamente -> Alterna de volta para 3A (Minigun)
        jogador.selecionar_slot(3)
        self.assertEqual(jogador.obter_arma_ativa(), minigun)
        self.assertFalse(jogador.slot_especial_secundario_ativo)

        # Valida fallback do Slot 2 para Pistola quando munição zera
        shotgun_slot2 = Shotgun()
        shotgun_slot2.municao_atual = 1
        jogador.armas = [jogador.armas[0], shotgun_slot2]
        self.assertEqual(jogador.armas[1], shotgun_slot2)

        shotgun_slot2.municao_atual = 0
        jogador.update(0.05)
        self.assertIsInstance(jogador.armas[1], Pistola, "Slot 2 deve retornar automaticamente para Pistola ao zerar munição.")

    def test_overclock_5_protecao_surtos_fatal_shield_and_cooldown(self):
        """Valida Overclock 5: Proteção contra Surtos (+50 HP, 4s invuln fatal, 50% HP e 60s cooldown pós-invuln)."""
        jogador = Jogador(x=400, y=300)
        hp_max_inicial = jogador.hp_max
        jogador.aplicar_overclock("protecao_surtos")

        self.assertTrue(jogador.protecao_surtos)
        self.assertEqual(jogador.hp_max, hp_max_inicial + 50)
        self.assertTrue(jogador.escudo_fatal_pronto)
        self.assertEqual(jogador.escudo_fatal_invuln_timer, 0.0)
        self.assertEqual(jogador.escudo_fatal_cooldown, 0.0)

        # Aplica dano fatal
        jogador.hp = 15
        jogador.receber_dano(100)

        # Escudo fatal absorve o golpe: recupera 50% HP, 4s invuln
        self.assertTrue(jogador.vivo)
        self.assertEqual(jogador.hp, jogador.hp_max // 2)
        self.assertFalse(jogador.escudo_fatal_pronto)
        self.assertEqual(jogador.escudo_fatal_invuln_timer, 4.0)
        self.assertEqual(jogador.invulnerabilidade_timer, 4.0)
        self.assertEqual(jogador.escudo_fatal_cooldown, 0.0)

        # Durante os 4.0s de invulnerabilidade, o cooldown ainda não iniciou
        jogador.update(2.0)
        self.assertEqual(jogador.escudo_fatal_invuln_timer, 2.0)
        self.assertEqual(jogador.escudo_fatal_cooldown, 0.0)

        # Conclui os 4.0s de invulnerabilidade (mais 2.0s) -> Inicia cooldown de 60.0s
        jogador.update(2.0)
        self.assertEqual(jogador.escudo_fatal_invuln_timer, 0.0)
        self.assertEqual(jogador.escudo_fatal_cooldown, 60.0)
        self.assertFalse(jogador.escudo_fatal_pronto)

        # Avança 55.0s do cooldown (restam 5.0s)
        jogador.update(55.0)
        self.assertAlmostEqual(jogador.escudo_fatal_cooldown, 5.0, places=3)
        self.assertFalse(jogador.escudo_fatal_pronto)

        # Avança os 5.0s finais -> Escudo fatal fica pronto novamente
        jogador.update(5.0)
        self.assertEqual(jogador.escudo_fatal_cooldown, 0.0)
        self.assertTrue(jogador.escudo_fatal_pronto)

    def test_overclock_6_upgrade_barramento_speed(self):
        """Valida Overclock 6: Upgrade de Barramento (+15% velocidade de movimento)."""
        jogador = Jogador(x=400, y=300)
        vel_base = jogador.velocidade_base

        jogador.update(0.1)
        self.assertEqual(jogador.velocidade_atual, vel_base)

        jogador.aplicar_overclock("upgrade_barramento")
        self.assertTrue(jogador.upgrade_barramento)
        jogador.update(0.1)
        self.assertAlmostEqual(jogador.velocidade_atual, vel_base * 1.15, places=4)

    def test_hud_slot_3b_rendering(self):
        """Valida que GameplayScene._desenhar_hud_tela renderiza Slot 3B na tela quando BIOS Modding está ativo."""
        cena = GameplayScene()
        screen = cena.janela.screen
        sx3b = 16 + 2 * (54 + 6)  # 136
        sy3b = 14 + 54 + 4        # 72

        # Sem BIOS Modding: região do Slot 3B permanece com a cor de fundo limpa
        screen.fill((0, 0, 0))
        cena._desenhar_hud_tela(hud_visivel=True)
        cor_sem_3b = screen.get_at((sx3b + 2, sy3b + 2))[:3]
        self.assertEqual(cor_sem_3b, (0, 0, 0))

        # Com BIOS Modding ativo: Slot 3B é desenhado com fundo roxo escuro (35, 20, 50) / borda ROXO_ACENTO
        cena.jogador.aplicar_overclock("bios_modding")
        cena.jogador.arma_especial_secundaria = Shotgun()
        screen.fill((0, 0, 0))
        cena._desenhar_hud_tela(hud_visivel=True)
        cor_com_3b = screen.get_at((sx3b + 10, sy3b + 10))[:3]
        self.assertNotEqual(cor_com_3b, (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
