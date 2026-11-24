"""
Testes de Integração de Combate v2.0 (Onda 2 — worker-combate).
Valida separação LMB/RMB, onda defensiva do Parry, contagem única por janela,
Just-Dodge, armas contínuas (RifleArco/LancaChamas), SMGCompacta, BIOS Modding,
latencia_ping (80ms), hooks B+, exclusão de drone no combo e SFX das 4 novas armas.
"""

import unittest
from types import SimpleNamespace

from src.armas.bastao_choque import BastaoChoque
from src.armas.lanca_chamas import LancaChamas
from src.armas.melee import Melee
from src.armas.pistola import Pistola
from src.armas.rifle_arco import RifleArco
from src.armas.smg_compacta import SMGCompacta
from src.cenas.gameplay_combate import GameplayCombateMixin
from src.entidades.jogador import Jogador
from src.entidades.projetil import Projetil
from src.sistemas.config_efeitos import ModificadoresGameplay
from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.sistemas.efeitos_combate import GerenciadorEfeitosCombate
from src.sistemas.sistema_combo import SistemaCombo
from src.sistemas.sistema_conquistas import SistemaConquistas


class _StubParticulas:
    def __init__(self):
        self.ondas = []

    def emitir_onda_choque(self, x, y, raio_max=100.0, cor=(255, 255, 255)):
        self.ondas.append((x, y, raio_max, cor))

    def emitir_faiscas(self, *args, **kwargs):
        pass

    def emitir_texto_dano(self, *args, **kwargs):
        pass

    def emitir_debris(self, *args, **kwargs):
        pass

    def emitir_burst_drop(self, *args, **kwargs):
        pass

    def adicionar_arco_parry(self, *args, **kwargs):
        pass

    def adicionar_onda_dash(self, *args, **kwargs):
        pass

    def adicionar_capsula(self, *args, **kwargs):
        pass


class _StubDrops:
    def __init__(self):
        self.drops = []

    def gerar_drop_morte_inimigo(self, *args, **kwargs):
        return []


class _StubInimigo:
    def __init__(self, x: float, y: float, hp: int = 100, is_boss: bool = False):
        self.x = float(x)
        self.y = float(y)
        self.largura = 28
        self.altura = 28
        self.hp = int(hp)
        self.hp_max = int(hp)
        self.vivo = True
        self.em_fase = False
        self.estado = "ativo"
        self.is_boss = is_boss
        self.is_elite = False
        self.superaqueceu = False
        self.slow_timer = 0.0
        self.slow_fator = 1.0
        self.queimadura_timer = 0.0
        self.knockback_chamadas = []

    def aplicar_knockback(self, dx: float, dy: float, forca: float):
        self.knockback_chamadas.append((dx, dy, forca))
        self.x += dx * 20.0
        self.y += dy * 20.0

    def receber_dano(self, qtd: int, *args, **kwargs) -> int:
        dano = int(qtd)
        self.hp = max(0, self.hp - dano)
        if self.hp <= 0:
            self.vivo = False
        return dano


class _StubTeclado:
    def __init__(self, keys=None):
        self.keys = set(keys or [])

    def key_down(self, k: str) -> bool:
        return k in self.keys

    def key_pressed(self, k: str) -> bool:
        return k in self.keys


class _StubMouse:
    def __init__(self, pos=(500.0, 400.0), btns=None):
        self.pos = pos
        self.btns = set(btns or [])

    def get_position(self):
        return self.pos

    def button_down(self, btn: int) -> bool:
        return btn in self.btns

    def button_pressed(self, btn: int) -> bool:
        return btn in self.btns


class _CenaCombateTeste(GameplayCombateMixin):
    def __init__(self, mods=None, firmwares=None):
        self.largura_arena = 1280.0
        self.altura_arena = 720.0
        self.jogador = Jogador(400.0, 400.0)
        self.jogador.dash_desbloqueado = True
        self.camera = SimpleNamespace(x=0.0, y=0.0)
        self.gerenciador_config = GerenciadorConfiguracoes()
        self.config_sistema = self.gerenciador_config
        self.sistema_conquistas = SistemaConquistas()
        self.gerenciador_config.sistema_conquistas = self.sistema_conquistas
        self.sistema_combo = SistemaCombo()
        self.efeitos_combate = GerenciadorEfeitosCombate()
        self._mods_custom = mods or ModificadoresGameplay()
        self.efeitos_combate.reconstruir(self._mods_custom, firmwares or [])
        self.gerenciador_config.obter_modificadores = lambda: self._mods_custom
        self.sistema_particulas = _StubParticulas()
        self.sistema_drops = _StubDrops()
        self.sistema_audio = None
        self.teclado = _StubTeclado()
        self.mouse = _StubMouse()
        self.chefe_final = None
        self.hologramas = []
        self.inimigos = []
        self.projeteis = []
        self.efeitos_melee = []
        self.toasts_coleta = []
        self.trilhas_plasma = []
        self.zonas_fogo = []
        self.zonas_estase = []
        self.pocas_gelo = []
        self.tiros_echo_pendentes = []
        self.hitstop_timer = 0.0
        self.arena_freeze_timer = 0.0
        self.aura_cura_timer = 0.0
        self.tempo_sobrevivencia = 10.0
        self.abates = 0
        self.pontos = 0
        self.dano_total_causado = 0
        self.buffer_tiro = 0.0
        self.auto_fire_toggle_ativo = False
        self.shakes = []

    def aplicar_shake(self, intensidade: float, duracao: float):
        self.shakes.append((intensidade, duracao))

    def _clamp_entidade_arena(self, ent):
        pass

    def _obter_mouse_mundo(self, mx: float, my: float):
        return mx, my

    def _obter_arma_melee(self):
        for arma in self.jogador.armas:
            if isinstance(arma, Melee) or getattr(arma, "slot", None) == 1:
                return arma
        return None


class TestIntegracaoCombateV2(unittest.TestCase):
    def test_lmb_melee_puro_sem_parry_nem_whiff(self):
        cena = _CenaCombateTeste()
        melee = cena._obter_arma_melee()
        melee.tempo_recarga_restante = 0.0
        inim = _StubInimigo(430.0, 400.0, hp=50)
        cena.inimigos.append(inim)

        # Projétil inimigo em cima do jogador NÃO deve ser rebatido por LMB
        proj_inim = Projetil(x=410.0, y=400.0, vx=-200.0, vy=0.0, dano=10, dono="inimigo")
        cena.projeteis.append(proj_inim)

        cena._executar_golpe_melee(melee, 416.0, 416.0, 460.0, 416.0, 0.0, 2.0, 1.0, cena._mods_custom)

        self.assertFalse(melee.parry_ativo)
        self.assertEqual(melee.parry_janela_id, 0)
        self.assertFalse(melee.parry_pode_punir_whiff)
        self.assertEqual(proj_inim.dono, "inimigo")
        self.assertLess(inim.hp, 50)

        # Expirar janela não aplica whiff penalty
        cd_antes = melee.tempo_recarga_restante
        melee.atualizar(0.20)
        self.assertLessEqual(melee.tempo_recarga_restante, cd_antes)

    def test_rmb_parry_onda_choque_contagem_unica_e_desbloqueio(self):
        cena = _CenaCombateTeste()
        melee = cena._obter_arma_melee()
        melee.tempo_recarga_restante = 0.0
        cena.jogador.dash_desbloqueado = False

        # Deixa 14 parries acumulados antes do 15º
        cena.sistema_conquistas.continuas["mestre_chave_inglesa"]["valor"] = 14

        inim_perto = _StubInimigo(460.0, 416.0, hp=50)
        boss_perto = _StubInimigo(450.0, 416.0, hp=500, is_boss=True)
        cena.inimigos.extend([inim_perto, boss_perto])

        # 2 projéteis inimigos na mesma janela -> devem contar EXATAMENTE 1 parry!
        p1 = Projetil(x=435.0, y=412.0, vx=-100.0, vy=0.0, dano=10, dono="inimigo")
        p2 = Projetil(x=440.0, y=418.0, vx=-100.0, vy=0.0, dano=10, dono="inimigo")
        cena.projeteis.extend([p1, p2])

        cena.mouse = _StubMouse(pos=(500.0, 416.0), btns={3})
        cena._atualizar_disparos_jogador(1 / 60, cena._mods_custom, 1.0, 1.0)

        # Onda defensiva (20 dano + knockback apenas no não-boss)
        self.assertEqual(inim_perto.hp, 30)
        self.assertEqual(len(inim_perto.knockback_chamadas), 1)
        self.assertEqual(boss_perto.hp, 500)
        self.assertEqual(len(boss_perto.knockback_chamadas), 0)

        # Contagem única -> 14 + 1 = 15 -> desbloqueia Dash + SMG Compacta!
        self.assertEqual(cena.sistema_conquistas.continuas["mestre_chave_inglesa"]["valor"], 15)
        self.assertEqual(cena.sistema_combo.contagem, 3)
        self.assertTrue(cena.jogador.dash_desbloqueado)
        self.assertTrue(cena.sistema_conquistas.possui_recompensa("habilidade", "dash"))
        self.assertTrue(cena.sistema_conquistas.possui_recompensa("arma", "smg_compacta"))

    def test_just_dodge_projetil_uma_vez_por_dash(self):
        cena = _CenaCombateTeste()
        cena.jogador.iniciar_dash(1.0, 0.0, mods=cena._mods_custom)
        self.assertTrue(cena.jogador.em_dash_iframes)

        p1 = Projetil(x=cena.jogador.x + 4, y=cena.jogador.y + 4, vx=-50.0, vy=0.0, dano=20, dono="inimigo")
        p2 = Projetil(x=cena.jogador.x + 8, y=cena.jogador.y + 8, vx=-50.0, vy=0.0, dano=20, dono="inimigo")
        cena.projeteis.extend([p1, p2])

        hp_antes = cena.jogador.hp
        cena._atualizar_projeteis_e_colisoes(
            1 / 60, cena._mods_custom, False, 416.0, 416.0, 0.0, 2.0, False, 1.0
        )

        self.assertEqual(cena.jogador.hp, hp_antes)
        self.assertEqual(cena.sistema_combo.contagem, 3)
        self.assertEqual(cena.sistema_conquistas.continuas["velocidade_de_clock"]["valor"], 1)

    def test_armas_continuas_e_smg_compacta(self):
        cena = _CenaCombateTeste()
        rifle = RifleArco()
        cena.jogador.equipar_arma_especial(rifle)
        cena.jogador.selecionar_slot(3)
        inim = _StubInimigo(490.0, 405.0, hp=100)
        cena.inimigos.append(inim)
        cena.mouse = _StubMouse(pos=(520.0, 416.0), btns={1})

        cena._atualizar_disparos_jogador(0.15, cena._mods_custom, 1.0, 1.0)
        self.assertTrue(rifle.feixe_ativo)
        self.assertLess(inim.hp, 100)

        chamas = LancaChamas()
        cena.jogador.equipar_arma_especial(chamas)
        cena.jogador.selecionar_slot(3)
        hp_antes_chamas = inim.hp
        cena._atualizar_disparos_jogador(0.15, cena._mods_custom, 1.0, 1.0)
        self.assertTrue(chamas.fluxo_ativo)
        self.assertLess(inim.hp, hp_antes_chamas)
        self.assertGreater(inim.queimadura_timer, 0.0)

        # SMGCompacta em zona ideal gera projétil superaquecido
        smg = SMGCompacta()
        smg.calor_atual = 75.0
        cena.jogador.armas[1] = smg
        cena.jogador.selecionar_slot(2)
        cena._atualizar_disparos_jogador(0.02, cena._mods_custom, 1.0, 1.0)
        self.assertTrue(any(getattr(p, "superaquecido", False) for p in cena.projeteis))

    def test_latencia_ping_atrasa_todas_as_4_acoes(self):
        mods = ModificadoresGameplay(latencia_ping=True)
        cena = _CenaCombateTeste(mods=mods)
        cena.mouse = _StubMouse(pos=(560.0, 416.0), btns={1, 3})
        cena.teclado = _StubTeclado(keys={"SPACE"})

        # Frame 0: dispara LMB (slot 2 pistola), RMB (parry) e SPACE (dash) -> tudo enfileirado (80ms)
        cena.jogador.selecionar_slot(2)
        cena._atualizar_disparos_jogador(0.016, mods, 1.0, 1.0)
        self.assertEqual(len(cena.projeteis), 0)
        self.assertFalse(cena.jogador.em_dash_iframes)
        self.assertFalse(cena._obter_arma_melee().parry_ativo)

        # Após 90ms sem novos inputs -> as 3 ações enfileiradas executam!
        cena.mouse = _StubMouse(pos=(560.0, 416.0), btns=set())
        cena.teclado = _StubTeclado()
        cena.buffer_tiro = 0.0
        cena._atualizar_disparos_jogador(0.090, mods, 1.0, 1.0)
        self.assertGreaterEqual(len(cena.projeteis), 1)
        self.assertTrue(cena.jogador.em_dash_iframes)
        self.assertTrue(cena._obter_arma_melee().parry_ativo)

    def test_sombra_espelho_bios_modding_sem_recursao_e_drone_excluido_combo(self):
        mods = ModificadoresGameplay(parry_precisao="padrao")
        cena = _CenaCombateTeste(mods=mods, firmwares=[])
        # Ativa sombra_espelho via config_efeitos / gerenciador
        mods.dash_protocolo = "sombra_espelho"
        cena.efeitos_combate.reconstruir(mods, [])
        cena.jogador.dash_protocolo = "sombra_espelho"
        cena.jogador.bios_modding = True
        cena.jogador.equipar_arma_especial(Pistola())
        cena.jogador.iniciar_dash(1.0, 0.0, mods=mods)
        cena.efeitos_combate.disparar_ao_dash(
            cena._construir_ctx_combate(mods), (400.0, 400.0), (480.0, 400.0)
        )
        self.assertEqual(len(cena.hologramas), 1)

        cena.jogador.selecionar_slot(2)
        cena.mouse = _StubMouse(pos=(560.0, 416.0), btns={1})
        cena._atualizar_disparos_jogador(0.016, mods, 1.0, 1.0)
        replicas = [p for p in cena.projeteis if getattr(p, "eh_replica", False)]
        self.assertGreaterEqual(len(replicas), 1)
        self.assertLessEqual(len(replicas), 12)

        # Drone kill não soma no SistemaCombo
        inim_drone = _StubInimigo(500.0, 500.0, hp=10)
        inim_drone.vivo = False
        cena._registrar_abate_inimigo(inim_drone, mods, origem="drone")
        self.assertEqual(cena.sistema_combo.contagem, 0)

        # Abate normal soma +1 no SistemaCombo
        inim_arma = _StubInimigo(510.0, 510.0, hp=10)
        inim_arma.vivo = False
        cena._registrar_abate_inimigo(inim_arma, mods, origem="arma")
        self.assertEqual(cena.sistema_combo.contagem, 1)

    def test_obter_sfx_4_novas_armas(self):
        self.assertEqual(GameplayCombateMixin._obter_sfx_arma(BastaoChoque()), "sfx_ataque_melee")
        self.assertEqual(GameplayCombateMixin._obter_sfx_arma(SMGCompacta()), "sfx_tiro_minigun")
        self.assertEqual(GameplayCombateMixin._obter_sfx_arma(RifleArco()), "sfx_tiro_railgun")
        self.assertEqual(GameplayCombateMixin._obter_sfx_arma(LancaChamas()), "sfx_tiro_foguete")


if __name__ == "__main__":
    unittest.main()
