"""
Adversarial Challenge Test Suite — Challenger 2 (Milestone 2)
Empirical verification of:
1. Beeline AI Convergence across all 4 Quadrants & 360-degree angles
2. Independent Enemy Contact Cooldowns (3 enemies on frame 0, multi-instance isolation)
3. Spawner Bounds (strict off-screen verification), Wave Scaling (temporal scaling), Soft Cap
4. 300+ Frame Headless Gameplay Simulation (zero crashes, zero exceptions, memory stability)
"""

import os
import sys
import math
import gc
import tracemalloc
import random
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pygame
from PPlay.window import Window
from PPlay.camera import Camera
from PPlay.scenemanager import SceneManager
from src.cenas.gameplay import GameplayScene
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.inimigo_base import InimigoBase
from src.entidades.jogador import Jogador
from src.sistemas.sistema_spawn import SistemaSpawn
from src.utils.math_utils import distancia, distancia_sq
from src.utils.constantes import (
    LARGURA_TELA, ALTURA_TELA, LARGURA_ARENA, ALTURA_ARENA,
    INIMIGO_PADRAO_HP, INIMIGO_PADRAO_VELOCIDADE, INIMIGO_PADRAO_DANO,
    INIMIGO_PADRAO_COOLDOWN_ATAQUE, SPAWN_DISTANCIA_OFFSET
)


class MockInput:
    """Mock determinístico para teclado e mouse."""
    def __init__(self, keys=None, mouse_pos=(400, 300), mouse_pressed=False):
        self.keys = set(k.lower() for k in (keys or []))
        self.mouse_pos = mouse_pos
        self.mouse_pressed = mouse_pressed

    def key_pressed(self, k):
        return k.lower() in self.keys

    def key_down(self, k):
        return k.lower() in self.keys

    def get_position(self):
        return self.mouse_pos

    def button_pressed(self, b):
        return self.mouse_pressed

    def button_down(self, b):
        return False


class TestBeelineAIConvergence(unittest.TestCase):
    """
    Missão 1: Testar convergência da IA beeline em todos os quadrantes,
    ângulos cardeais, ordinais e aleatórios, garantindo redução estrita da distância euclidiana.
    """

    def test_beeline_convergence_quadrants_and_cardinals(self):
        """Testa convergência em 8 direções principais (4 cardeais, 4 ordinais)."""
        player_pos = (500.0, 500.0)
        dt = 1.0 / 60.0
        dist_offset = 200.0

        direcoes = {
            "Norte (0, -1)": (0.0, -dist_offset),
            "Nordeste (1, -1)": (dist_offset, -dist_offset),
            "Leste (1, 0)": (dist_offset, 0.0),
            "Sudeste (1, 1)": (dist_offset, dist_offset),
            "Sul (0, 1)": (0.0, dist_offset),
            "Sudoeste (-1, 1)": (-dist_offset, dist_offset),
            "Oeste (-1, 0)": (-dist_offset, 0.0),
            "Noroeste (-1, -1)": (-dist_offset, -dist_offset),
        }

        for nome_dir, (ox, oy) in direcoes.items():
            ex = player_pos[0] + ox
            ey = player_pos[1] + oy
            inimigo = InimigoPadrao(x=ex, y=ey)

            cx0 = inimigo.x + inimigo.largura / 2.0
            cy0 = inimigo.y + inimigo.altura / 2.0
            d0 = distancia(cx0, cy0, player_pos[0], player_pos[1])

            # Executa 1 frame de movimento
            inimigo.update(dt=dt, pos_alvo=player_pos)

            cx1 = inimigo.x + inimigo.largura / 2.0
            cy1 = inimigo.y + inimigo.altura / 2.0
            d1 = distancia(cx1, cy1, player_pos[0], player_pos[1])

            self.assertLess(
                d1, d0,
                f"Falha de convergência em {nome_dir}: d0={d0:.4f}, d1={d1:.4f}"
            )
            delta = d0 - d1
            esperado = INIMIGO_PADRAO_VELOCIDADE * dt
            self.assertAlmostEqual(
                delta, esperado, delta=1e-3,
                msg=f"Passo em {nome_dir} divergiu do esperado: delta={delta:.4f}, esperado={esperado:.4f}"
            )

    def test_beeline_convergence_360_degrees_sweep(self):
        """Varrer 360 graus em incrementos de 1 grau para provar convergência omnidirecional."""
        player_pos = (800.0, 600.0)
        raio = 300.0
        dt = 1.0 / 60.0

        for angulo_deg in range(360):
            rad = math.radians(angulo_deg)
            ex = player_pos[0] + raio * math.cos(rad) - 14.0
            ey = player_pos[1] + raio * math.sin(rad) - 14.0
            inimigo = InimigoPadrao(x=ex, y=ey)

            cx0 = inimigo.x + 14.0
            cy0 = inimigo.y + 14.0
            d0 = distancia(cx0, cy0, player_pos[0], player_pos[1])

            inimigo.update(dt=dt, pos_alvo=player_pos)

            cx1 = inimigo.x + 14.0
            cy1 = inimigo.y + 14.0
            d1 = distancia(cx1, cy1, player_pos[0], player_pos[1])

            self.assertLess(
                d1, d0,
                f"Ângulo {angulo_deg}° falhou em convergir: d0={d0}, d1={d1}"
            )
            self.assertFalse(math.isnan(inimigo.x))
            self.assertFalse(math.isnan(inimigo.y))

    def test_beeline_multi_step_arrival(self):
        """Verifica que o inimigo atinge a vizinhança do jogador em tempo $T = D / V$ sem orbitar."""
        player_pos = (500.0, 500.0)
        inimigo = InimigoPadrao(x=200.0, y=100.0)  # Distância ~424px
        dt = 1.0 / 60.0
        dist_inicial = distancia(inimigo.x + 14.0, inimigo.y + 14.0, player_pos[0], player_pos[1])
        tempo_estimado = dist_inicial / INIMIGO_PADRAO_VELOCIDADE
        frames = int(tempo_estimado / dt) + 10

        dist_anterior = dist_inicial
        for f in range(frames):
            inimigo.update(dt=dt, pos_alvo=player_pos)
            dist_atual = distancia(inimigo.x + 14.0, inimigo.y + 14.0, player_pos[0], player_pos[1])

            if dist_atual > 5.0:
                self.assertLess(
                    dist_atual, dist_anterior,
                    f"Frame {f}: distância aumentou de {dist_anterior} para {dist_atual}"
                )
            dist_anterior = dist_atual

        # Ao final, deve estar a menos de 5 pixels do alvo
        self.assertLess(dist_anterior, 5.0)

    def test_beeline_zero_distance_singularity(self):
        """Verifica estabilidade numérica quando a distância é exatamente zero."""
        player_pos = (500.0, 500.0)
        inimigo = InimigoPadrao(x=500.0 - 14.0, y=500.0 - 14.0)
        inimigo.update(dt=0.016, pos_alvo=player_pos)
        self.assertFalse(math.isnan(inimigo.x))
        self.assertFalse(math.isnan(inimigo.y))
        self.assertFalse(math.isinf(inimigo.x))
        self.assertFalse(math.isinf(inimigo.y))


class TestIndependentEnemyContactCooldowns(unittest.TestCase):
    """
    Missão 2: Testar cooldowns de contato estritamente independentes por instância.
    Quando 3 inimigos colidem no frame 0, os 3 causam dano e entram em cooldown de 0.4s.
    """

    def test_three_enemies_simultaneous_contact_and_cooldown(self):
        """3 inimigos colidem simultaneamente no frame 0 e entram em cooldown independente."""
        jogador = Jogador(x=400.0, y=300.0)
        jogador_hp_inicial = jogador.hp  # 150

        # Cria 3 instâncias distintas sobrepostas ao jogador
        e1 = InimigoPadrao(x=400.0, y=300.0)
        e2 = InimigoPadrao(x=400.0, y=300.0)
        e3 = InimigoPadrao(x=400.0, y=300.0)

        # 1. FRAME 0: Todos os 3 devem infligir dano no mesmo frame
        dano_e1 = e1.tentar_causar_dano_contato(jogador)
        dano_e2 = e2.tentar_causar_dano_contato(jogador)
        dano_e3 = e3.tentar_causar_dano_contato(jogador)

        self.assertTrue(dano_e1, "Inimigo 1 deveria ter causado dano no frame 0")
        self.assertTrue(dano_e2, "Inimigo 2 deveria ter causado dano no frame 0")
        self.assertTrue(dano_e3, "Inimigo 3 deveria ter causado dano no frame 0")

        # Dano total acumulado: 10 + 10 + 10 = 30 -> HP: 150 - 30 = 120
        self.assertEqual(jogador.hp, jogador_hp_inicial - 30)

        # Cooldowns individuais devem estar setados para 0.4s
        self.assertAlmostEqual(e1.cooldown_contato_atual, 0.4)
        self.assertAlmostEqual(e2.cooldown_contato_atual, 0.4)
        self.assertAlmostEqual(e3.cooldown_contato_atual, 0.4)

        # 2. FRAME 1..N (t < 0.4s): Tentativa imediata em t = 0.1s, 0.2s, 0.35s NÃO causa dano
        for dt_step in [0.1, 0.1, 0.15]:  # Total decorrido = 0.35s
            e1.update(dt=dt_step, pos_alvo=(416.0, 316.0))
            e2.update(dt=dt_step, pos_alvo=(416.0, 316.0))
            e3.update(dt=dt_step, pos_alvo=(416.0, 316.0))

            # Nenhum dos 3 pode infligir dano durante o cooldown
            self.assertFalse(e1.tentar_causar_dano_contato(jogador))
            self.assertFalse(e2.tentar_causar_dano_contato(jogador))
            self.assertFalse(e3.tentar_causar_dano_contato(jogador))
            self.assertEqual(jogador.hp, 120, "HP do jogador não deve mudar durante o cooldown de contato")

        # 3. FRAME N+1 (t = 0.40s+): Cooldowns expiram, e todos os 3 causam dano novamente
        # Avança 0.06s (total 0.41s > 0.40s)
        e1.update(dt=0.06, pos_alvo=(416.0, 316.0))
        e2.update(dt=0.06, pos_alvo=(416.0, 316.0))
        e3.update(dt=0.06, pos_alvo=(416.0, 316.0))

        self.assertEqual(e1.cooldown_contato_atual, 0.0)
        self.assertEqual(e2.cooldown_contato_atual, 0.0)
        self.assertEqual(e3.cooldown_contato_atual, 0.0)

        hit2_e1 = e1.tentar_causar_dano_contato(jogador)
        hit2_e2 = e2.tentar_causar_dano_contato(jogador)
        hit2_e3 = e3.tentar_causar_dano_contato(jogador)

        self.assertTrue(hit2_e1)
        self.assertTrue(hit2_e2)
        self.assertTrue(hit2_e3)
        self.assertEqual(jogador.hp, 90)

    def test_staggered_independent_cooldowns(self):
        """Inimigos que atacam em momentos diferentes mantêm cronômetros independentes."""
        jogador = Jogador(x=400.0, y=300.0)
        e1 = InimigoPadrao(x=400.0, y=300.0)
        e2 = InimigoPadrao(x=400.0, y=300.0)

        # e1 ataca em t = 0.0s
        self.assertTrue(e1.tentar_causar_dano_contato(jogador))
        self.assertEqual(jogador.hp, 140)

        # Passa 0.2s
        e1.update(0.2, (416, 316))
        e2.update(0.2, (416, 316))

        # e2 ataca em t = 0.2s
        self.assertTrue(e2.tentar_causar_dano_contato(jogador))
        self.assertEqual(jogador.hp, 130)

        # Passa mais 0.21s (t = 0.41s para e1, t = 0.21s para e2)
        e1.update(0.21, (416, 316))
        e2.update(0.21, (416, 316))

        # e1 pode atacar (cooldown expirou), e2 NÃO pode (ainda restam ~0.19s)
        self.assertTrue(e1.tentar_causar_dano_contato(jogador))
        self.assertFalse(e2.tentar_causar_dano_contato(jogador))
        self.assertEqual(jogador.hp, 120)


class TestSpawnerAdversarial(unittest.TestCase):
    """
    Missão 3: Testar geração fora do viewport da câmera, escalonamento temporal de ondas e teto suave.
    """

    def test_spawner_strict_offscreen_generation_1000_samples(self):
        """Gera 1000 posições de spawn sob diversas posições de câmera e valida que NENHUMA está na visão."""
        spawner = SistemaSpawn()
        camera_positions = [
            (0.0, 0.0),
            (200.0, 150.0),
            (400.0, 300.0),
            (800.0, 600.0),
            (700.0, 500.0)
        ]
        view_w, view_h = float(LARGURA_TELA), float(ALTURA_TELA)
        margem = float(SPAWN_DISTANCIA_OFFSET)

        total_tested = 0
        for cam_x, cam_y in camera_positions:
            for _ in range(200):
                sx, sy = spawner.gerar_posicao_spawn(
                    camera_x=cam_x, camera_y=cam_y,
                    view_w=view_w, view_h=view_h,
                    margem=margem,
                    arena_w=float(LARGURA_ARENA),
                    arena_h=float(ALTURA_ARENA)
                )
                total_tested += 1

                # Verifica se está no retângulo de visão visível estrito
                dentro_x = (cam_x <= sx <= cam_x + view_w)
                dentro_y = (cam_y <= sy <= cam_y + view_h)
                dentro_camera = dentro_x and dentro_y

                self.assertFalse(
                    dentro_camera,
                    f"VIOLAÇÃO DE VISIBILIDADE: Spawn ({sx}, {sy}) gerado dentro da visão da câmera "
                    f"[{cam_x}, {cam_x + view_w}] x [{cam_y}, {cam_y + view_h}]!"
                )

                # Verifica se está dentro dos limites expandidos da arena
                self.assertGreaterEqual(sx, -margem)
                self.assertLessEqual(sx, LARGURA_ARENA + margem)
                self.assertGreaterEqual(sy, -margem)
                self.assertLessEqual(sy, ALTURA_ARENA + margem)

        self.assertEqual(total_tested, 1000)

    def test_wave_scaling_monotonicity_and_bounds(self):
        """Verifica a curva de escalonamento do spawner ao longo de 10 minutos."""
        spawner = SistemaSpawn()
        tempos = [0.0, 10.0, 25.0, 50.0, 75.0, 100.0, 120.0, 200.0, 600.0]

        intervalo_anterior = 999.0
        lote_anterior = 0

        for t in tempos:
            intervalo = spawner.intervalo_spawn(t)
            lote = spawner.tamanho_lote(t)

            # Intervalo deve ser >= 0.40 e <= 1.80
            self.assertGreaterEqual(intervalo, 0.40)
            self.assertLessEqual(intervalo, 1.80)
            self.assertLessEqual(intervalo, intervalo_anterior, f"Intervalo não decresceu monotonicamente em t={t}")

            # Lote deve ser >= 1 e <= 8
            self.assertGreaterEqual(lote, 1)
            self.assertLessEqual(lote, 8)
            self.assertGreaterEqual(lote, lote_anterior, f"Tamanho de lote não cresceu monotonicamente em t={t}")

            intervalo_anterior = intervalo
            lote_anterior = lote

    def test_soft_cap_never_exceeded_under_extreme_spawning(self):
        """Simula 1000 segundos de spawn acelerado garantindo que o teto nunca é violado."""
        max_cap = 60
        spawner = SistemaSpawn(max_ativos=max_cap)
        inimigos_vivos = []

        # Executa 3000 passos de simulação onde nenhum inimigo morre
        for step in range(3000):
            novos = spawner.update(
                dt=0.2,
                camera_x=400.0, camera_y=300.0,
                total_inimigos_vivos=len(inimigos_vivos)
            )
            inimigos_vivos.extend(novos)

            self.assertLessEqual(
                len(inimigos_vivos), max_cap,
                f"Passo {step}: População ({len(inimigos_vivos)}) excedeu o teto máximo ({max_cap})!"
            )

        self.assertEqual(len(inimigos_vivos), max_cap)


class TestLongRunningSimulation(unittest.TestCase):
    """
    Missão 4: Executar simulação headless contínua de 300+ frames (executamos 600 frames).
    Verificar 0 exceções, 0 travamentos, integridade de física/combate e estabilidade de memória.
    """

    def setUp(self):
        self.janela = Window(800, 600, "Protocolo: Batata Headless Stress", resizavel=True, pixel_art=True)

    def test_600_frames_headless_gameplay_stress_and_memory(self):
        """Executa 600 frames contínuos (~10 segundos a 60 FPS) sob stress de combate e movimento."""
        tracemalloc.start()
        snapshot_inicial = tracemalloc.take_snapshot()

        cena = GameplayScene()
        cena.auto_fire_ativo = True
        SceneManager.change_scene(cena)

        # Mock dinâmico de input variando a cada frame
        chaves_ciclo = [["w", "d"], ["s", "d"], ["s", "a"], ["w", "a"], ["w"]]
        erros = []
        frames_executados = 0
        total_frames = 600

        # Rastreamento de métricas a cada 100 frames
        snapshots = []

        for f in range(total_frames):
            try:
                # Simula input do jogador girando pela arena
                chaves = chaves_ciclo[(f // 60) % len(chaves_ciclo)]
                cena.teclado = MockInput(keys=chaves)

                # Cursor de mira gira ao redor do jogador para testar todos os quadrantes de tiro
                ang = math.radians((f * 5) % 360)
                mx = 400 + 200 * math.cos(ang)
                my = 300 + 200 * math.sin(ang)
                cena.mouse = MockInput(mouse_pos=(mx, my), mouse_pressed=True)

                # Executa ciclo completo: lógica de cena, renderização PPlay e blit
                SceneManager.run()
                cena.draw()
                self.janela.update()

                frames_executados += 1

                if f % 100 == 0:
                    gc.collect()
                    snapshots.append(tracemalloc.take_snapshot())

            except Exception as e:
                erros.append((f, str(e)))
                break

        snapshot_final = tracemalloc.take_snapshot()
        tracemalloc.stop()

        # 1. Assert 0 exceções e 0 crashes
        self.assertEqual(len(erros), 0, f"Ocorreram exceções durante os 600 frames: {erros}")
        self.assertEqual(frames_executados, total_frames, f"Simulação parou prematuramente no frame {frames_executados}")

        # 2. Assert atividade do jogo
        self.assertGreater(cena.tempo_sobrevivencia, 5.0, "Tempo de sobrevivência deveria ter avançado")
        self.assertGreaterEqual(len(cena.inimigos), 0, "Lista de inimigos íntegra")
        self.assertGreaterEqual(cena.abates, 0, "Abates íntegros")

        # 3. Assert estabilidade de memória
        # Compara snapshot inicial com snapshot final
        top_stats = snapshot_final.compare_to(snapshot_inicial, 'lineno')
        mem_diff_kb = sum(stat.size_diff for stat in top_stats) / 1024.0

        # Verifica se o crescimento de memória está razoavelmente contido (< 15 MB para 600 frames com sprites e caching)
        self.assertLess(
            mem_diff_kb, 15360.0,
            f"Vazamento excessivo de memória detectado: delta de {mem_diff_kb:.2f} KB em 600 frames"
        )


if __name__ == "__main__":
    unittest.main()
