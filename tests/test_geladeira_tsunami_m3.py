"""
Testes Unitários — Milestone M3: Geladeira Tsunami Boss Entity & Assets
"""

import unittest
import os
import pygame

from src.utils.constantes import (
    ASSET_PATHS, obter_caminho_asset,
    GELADEIRA_TSUNAMI_LARGURA, GELADEIRA_TSUNAMI_ALTURA,
    GELADEIRA_TSUNAMI_HP, GELADEIRA_TSUNAMI_DANO,
    GELADEIRA_TSUNAMI_VELOCIDADE, GELADEIRA_TSUNAMI_NOME,
    GELADEIRA_TSUNAMI_FLAVOR, BOSS_GELADEIRA_LARGURA,
    BOSS_GELADEIRA_ALTURA, BOSS_GELADEIRA_HP_BASE
)
from src.entidades.inimigos.geladeira_tsunami import (
    GeladeiraTsunami, ESTADO_INTRO, ESTADO_FASE1,
    ESTADO_FASE2, ESTADO_FASE3, ESTADO_MORTE
)
from src.entidades.inimigos import GeladeiraTsunami as ExportedBoss
from src.entidades import GeladeiraTsunami as EntidadesBoss


class TestGeladeiraTsunamiMilestone3(unittest.TestCase):
    """Testes de conformidade do Milestone M3 para Geladeira Tsunami."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.font.init()

    def test_asset_registration_and_constants(self):
        """Verifica se os assets e constantes de Geladeira Tsunami estão registrados."""
        self.assertIn("musica_boss", ASSET_PATHS)
        self.assertEqual(ASSET_PATHS["musica_boss"], "audio/musica/geladeira tsunami.wav")
        self.assertIn("boss_geladeira_tsunami", ASSET_PATHS)
        self.assertEqual(ASSET_PATHS["boss_geladeira_tsunami"], "sprites/inimigos/geladeira_tsunami.png")

        # Verifica resolução de caminhos absolutos
        caminho_audio = obter_caminho_asset("musica_boss")
        self.assertTrue(caminho_audio.endswith("geladeira tsunami.wav"))
        caminho_sprite = obter_caminho_asset("boss_geladeira_tsunami")
        self.assertTrue(caminho_sprite.endswith("geladeira_tsunami.png"))

        # Verifica constantes e aliases
        self.assertEqual(GELADEIRA_TSUNAMI_LARGURA, 112)
        self.assertEqual(GELADEIRA_TSUNAMI_ALTURA, 156)
        self.assertEqual(BOSS_GELADEIRA_LARGURA, 112)
        self.assertEqual(BOSS_GELADEIRA_ALTURA, 156)
        self.assertEqual(GELADEIRA_TSUNAMI_HP, 2500)
        self.assertEqual(GELADEIRA_TSUNAMI_NOME, "GELADEIRA TSUNAMI")
        self.assertEqual(GELADEIRA_TSUNAMI_FLAVOR, "The Perfect Sound™")

    def test_module_exports(self):
        """Verifica se a classe GeladeiraTsunami está exportada corretamente nos módulos."""
        self.assertIs(ExportedBoss, GeladeiraTsunami)
        self.assertIs(EntidadesBoss, GeladeiraTsunami)

    def test_boss_dimensions_and_hitbox(self):
        """Verifica se as dimensões visuais e a hitbox física são estritamente 112 x 156 px."""
        boss = GeladeiraTsunami(x=300, y=200)
        self.assertEqual(boss.largura, 112)
        self.assertEqual(boss.altura, 156)
        self.assertEqual(boss.width, 112)
        self.assertEqual(boss.height, 156)

        rect = boss.get_rect()
        self.assertEqual(rect, (300.0, 200.0 + 250.0, 112, 156))  # x, y_intro, w, h
        self.assertEqual(boss.rect.width, 112)
        self.assertEqual(boss.rect.height, 156)

    def test_speech_balloon_text_and_intro(self):
        """Verifica o balão de fala e o texto exato da fala do Boss."""
        boss = GeladeiraTsunami(x=300, y=200)
        self.assertEqual(boss.estado, ESTADO_INTRO)
        self.assertTrue(boss.mostrar_balao_fala)
        texto_esperado = "Você já passou da validade.\nSente a pressão, neném."
        self.assertEqual(boss.balao_fala_texto, texto_esperado)

        # Teste de renderização do balão de fala
        surface = pygame.Surface((800, 600))
        boss.desenhar_balao_fala(surface, draw_x=300, draw_y=200)

    def test_fsm_intro_transition(self):
        """Verifica se a fase de intro ascende e transiciona para Fase 1 após 3.5s."""
        boss = GeladeiraTsunami(x=400, y=300)
        self.assertEqual(boss.estado, ESTADO_INTRO)
        self.assertEqual(boss.timer_intro, 3.5)

        # Avança 2.0s
        boss.update(2.0, (400, 300))
        self.assertEqual(boss.estado, ESTADO_INTRO)
        self.assertTrue(boss.mostrar_balao_fala)

        # Avança mais 1.6s (total 3.6s > 3.5s)
        boss.update(1.6, (400, 300))
        self.assertEqual(boss.estado, ESTADO_FASE1)
        self.assertFalse(boss.mostrar_balao_fala)
        self.assertEqual(boss.y, 300.0)

    def test_fsm_phases_based_on_hp(self):
        """Verifica a transição de fases (Fase 1 >66%, Fase 2 33-66%, Fase 3 <=33%, Morte 0%)."""
        boss = GeladeiraTsunami(x=400, y=300, hp=2500)
        # Pula intro
        boss.update(3.6, (400, 300))
        self.assertEqual(boss.estado, ESTADO_FASE1)

        # HP = 2000 (80% > 66%) -> Permanece Fase 1
        boss.receber_dano(500)
        self.assertEqual(boss.hp, 2000)
        self.assertEqual(boss.estado, ESTADO_FASE1)

        # HP = 1500 (60% <= 66%) -> Fase 2
        boss.receber_dano(500)
        self.assertEqual(boss.hp, 1500)
        self.assertEqual(boss.estado, ESTADO_FASE2)

        # HP = 750 (30% <= 33%) -> Fase 3
        boss.receber_dano(750)
        self.assertEqual(boss.hp, 750)
        self.assertEqual(boss.estado, ESTADO_FASE3)

        # HP = 0 -> Estado Morte (1.5s cascade)
        boss.receber_dano(800)
        self.assertEqual(boss.hp, 0)
        self.assertEqual(boss.estado, ESTADO_MORTE)
        self.assertTrue(boss.vivo)
        self.assertFalse(boss.morreu)

        # Avança 1.0s de morte
        boss.update(1.0, (400, 300))
        self.assertEqual(boss.estado, ESTADO_MORTE)
        self.assertTrue(boss.vivo)

        # Avança mais 0.6s (total 1.6s > 1.5s)
        boss.update(0.6, (400, 300))
        self.assertFalse(boss.vivo)
        self.assertTrue(boss.morreu)
        self.assertTrue(boss.derrotado)
        self.assertTrue(boss.gerar_drop_vitoria)

    def test_phase1_subwoofer_pulse(self):
        """Verifica geração de anéis sônicos concêntricos com brechas de esquiva na Fase 1."""
        boss = GeladeiraTsunami(x=400, y=300)
        boss.update(3.6, (500, 300))  # Pula intro
        self.assertEqual(boss.estado, ESTADO_FASE1)

        # Limpa projéteis iniciais
        boss.obter_projeteis_pendentes()

        # Avança o tempo até disparar pulso
        boss.update(2.5, (500, 300))
        projeteis = boss.obter_projeteis_pendentes()
        self.assertGreaterEqual(len(projeteis), 10)
        for p in projeteis:
            self.assertEqual(p.dono, "inimigo")

    def test_phase2_telegraphed_bass_rush(self):
        """Verifica telegrafo, dash de 420 px/s, tremor e estilhaços na colisão da Fase 2."""
        boss = GeladeiraTsunami(x=400, y=300, hp=2500)
        boss.hp = 1500  # 60% HP -> Fase 2
        boss.update(3.6, (500, 300))
        self.assertEqual(boss.estado, ESTADO_FASE2)

        # Avança até entrar em telegraph
        boss.update(3.6, (500, 300))
        self.assertEqual(boss.subestado_fase2, "telegraph")

        # Avança duração do telegraph (0.8s) -> entra em dash
        boss.update(0.9, (500, 300))
        self.assertEqual(boss.subestado_fase2, "dash")
        self.assertEqual(boss.dash_velocidade, 420.0)

        # Limpa projéteis acumulados na fase de stalk
        boss.obter_projeteis_pendentes()

        # Força colisão com parede da arena
        boss.x = -10.0
        boss.update(0.1, (500, 300))
        self.assertTrue(boss.shake_screen or boss.shake_intensidade > 0)
        shards = boss.obter_projeteis_pendentes()
        self.assertEqual(len(shards), 4)


    def test_phase3_center_anchor_and_helix(self):
        """Verifica ancoragem no centro e feixes helicoidais da Fase 3."""
        boss = GeladeiraTsunami(x=200, y=200, hp=2500)
        boss.hp = 600  # 24% HP -> Fase 3
        boss.update(3.6, (500, 300))
        self.assertEqual(boss.estado, ESTADO_FASE3)


        # Avança tempo para disparar feixes helix
        boss.obter_projeteis_pendentes()
        boss.update(0.2, (500, 300))
        helix_projs = boss.obter_projeteis_pendentes()
        self.assertGreaterEqual(len(helix_projs), 2)

    def test_rendering_and_fallback_surface(self):
        """Verifica se o método desenhar funciona com Surface sem erros."""
        boss = GeladeiraTsunami(x=100, y=100)
        screen = pygame.Surface((800, 600))
        # Desenha em intro
        boss.desenhar(screen)

        # Desenha com camera offset
        boss.desenhar(screen, camera=(50, 50))

        # Transiciona e desenha em Fase 1
        boss.update(4.0, (200, 200))
        boss.desenhar(screen)

    def test_contact_damage_and_thermal_overload_immunity(self):
        """Verifica que o Boss causa dano de contato e é imune a sobreaquecimento térmico."""
        boss = GeladeiraTsunami(x=100, y=100)
        self.assertIsNone(boss.tempo_vida_restante)
        self.assertFalse(boss.superaqueceu)

        # Atualiza 100 segundos e verifica que não superaquece
        boss.update(100.0, (100, 100))
        self.assertFalse(boss.superaqueceu)
        self.assertTrue(boss.vivo)

        # Mock de jogador simples para colisão
        class MockJogador:
            def __init__(self):
                self.x = 100
                self.y = 100
                self.largura = 32
                self.altura = 32
                self.hp = 150
                self.vivo = True

            def receber_dano(self, qtd):
                self.hp -= qtd

        jogador = MockJogador()
        causou = boss.tentar_causar_dano_contato(jogador)
        self.assertTrue(causou)
        self.assertEqual(jogador.hp, 150 - GELADEIRA_TSUNAMI_DANO)

    def test_shake_consumption(self):
        """Verifica o consumo de tremor de tela pendente."""
        boss = GeladeiraTsunami(x=100, y=100)
        boss.shake_screen = True
        boss.shake_intensidade = 15.0
        shake = boss.obter_shake_pendente()
        self.assertEqual(shake, 15.0)
        # Segunda chamada deve retornar 0.0
        self.assertEqual(boss.obter_shake_pendente(), 0.0)


if __name__ == "__main__":
    unittest.main()

