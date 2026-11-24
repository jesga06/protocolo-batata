"""
Cena do Menu Principal — Protocolo: Batata
Tela inicial do jogo com opções de Jogar, Configurações, Créditos e Sair.
"""

import sys
import os
import pygame
from src.cenas.base_scene import BaseScene
from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.ui.banner_dicas import BannerDica
from src.ui.menu_configs import MenuConfigs
from src.ui.menu_conquistas import MenuConquistas
from src.utils.constantes import (
    LARGURA_TELA, ALTURA_TELA, TITULO_JOGO,
    BRANCO, AZUL_CIANO, AMARELO_XP, CINZA_PAINEL, DOURADO,
    obter_caminho_asset, SAVE_FILE_PATH
)

# Paleta Cyber-Office (Spec §8 aprovada)
_C_BACKDROP = (7, 9, 14)
_C_HUD_PANEL = (11, 14, 23)
_C_CARD = (17, 24, 39)
_C_CARD_HOVER = (22, 30, 48)
_C_ELEVATED = (30, 41, 59)
_C_BORDER = (51, 65, 85)
_C_GRID = (14, 19, 30)
_C_TEXT_PRIMARY = (241, 245, 249)
_C_TEXT_SECONDARY = (148, 163, 184)
_C_TEXT_MUTED = (100, 116, 139)
_C_CYAN = (34, 211, 238)
_C_PURPLE = (168, 85, 247)
_C_GOLD = (251, 191, 36)


_FONT_CACHE: dict[tuple[str, int, bool], pygame.font.Font] = {}


def _carregar_fonte_sans(tamanho: int, bold: bool = False) -> pygame.font.Font:
    px_sz = max(8, int(tamanho))
    chave = ("sans", px_sz, bold)
    if chave in _FONT_CACHE:
        return _FONT_CACHE[chave]
    for nome in ("notosans", "dejavusans", "liberationsans", "arial"):
        f = pygame.font.SysFont(nome, px_sz, bold=bold)
        if f is not None:
            _FONT_CACHE[chave] = f
            return f
    f = pygame.font.SysFont("Arial", px_sz, bold=bold)
    _FONT_CACHE[chave] = f
    return f


def _carregar_fonte_mono(tamanho: int, bold: bool = False) -> pygame.font.Font:
    px_sz = max(8, int(tamanho))
    chave = ("mono", px_sz, bold)
    if chave in _FONT_CACHE:
        return _FONT_CACHE[chave]
    for nome in ("jetbrainsmono", "firacode", "consolas", "dejavusansmono"):
        f = pygame.font.SysFont(nome, px_sz, bold=bold)
        if f is not None:
            _FONT_CACHE[chave] = f
            return f
    f = pygame.font.SysFont("Consolas", px_sz, bold=bold)
    _FONT_CACHE[chave] = f
    return f


class MenuPrincipalScene(BaseScene):
    def __init__(self):
        super().__init__()
        self.tempo_acumulado = 0.0
        self.opcao_selecionada = 0
        self.opcoes = [
            "JOGAR [ENTER]",
            "CONFIGURAÇÕES [C]",
            "CONQUISTAS & FIRMWARE [F]",
            "TUTORIAL [T]",
            "RESETAR DADOS SALVOS",
            "SAIR [ESC]",
        ]
        self.confirmar_reset_save = False
        self.aviso_reset_timer = 0.0
        self.cooldown_input = 0.0

        # Sistema de configurações, Conquistas/Firmware e Menu de Configurações
        self.gerenciador_config = GerenciadorConfiguracoes()
        self.gerenciador_config.carregar_arquivo(SAVE_FILE_PATH)
        self.menu_configs = MenuConfigs(self.gerenciador_config, em_jogo=False, cena=self)
        self.menu_conquistas = MenuConquistas(
            self.gerenciador_config,
            getattr(self.gerenciador_config, "sistema_conquistas", None),
            em_jogo=False,
            cena=self,
        )
        self.banner_dicas = BannerDica()
        self.mostrar_popup_tutorial = not bool(getattr(self.gerenciador_config, "tutorial_visto", False))
        self._popup_overlay_cache: dict[tuple[int, int], pygame.Surface] = {}
        try:
            pygame.mouse.set_visible(True)
        except Exception:
            pass

        # Cache de fontes para alta performance (Sans-Serif + Monospace — zero alocação por frame)
        self._fonte_titulo = _carregar_fonte_sans(40, bold=True)
        self._fonte_sub = _carregar_fonte_sans(13, bold=False)
        self._fonte_badge = _carregar_fonte_mono(13, bold=True)
        self._fonte_opcoes = _carregar_fonte_sans(16, bold=True)
        self._fonte_hotkey = _carregar_fonte_mono(11, bold=True)
        self._fonte_rodape = _carregar_fonte_mono(12, bold=False)

        # Sprite original do Cleiton em cache (base + escala dinâmica por DPI)
        self._cleiton_base = None
        self._cleiton_sprite = None
        self._cleiton_sprite_tam = 0
        try:
            caminho_batata = obter_caminho_asset("batata_idle")
            if os.path.isfile(caminho_batata):
                self._cleiton_base = pygame.image.load(caminho_batata).convert_alpha()
                self._cleiton_sprite = pygame.transform.scale(self._cleiton_base, (44, 44))
                self._cleiton_sprite_tam = 44
        except Exception:
            self._cleiton_base = None
            self._cleiton_sprite = None

        # Inicia a trilha sonora e sincroniza volumes com as configurações salvas
        try:
            from PPlay.sound import SoundManager
            SoundManager.inicializar()
            vol_master = self.gerenciador_config.obter_valor("volume_master")
            if vol_master is None:
                vol_master = 100
            vol_musica = self.gerenciador_config.obter_valor("volume_musica")
            if vol_musica is None:
                vol_musica = 100
            vol_sfx = self.gerenciador_config.obter_valor("volume_sfx")
            if vol_sfx is None:
                vol_sfx = 100

            # Aplica volume de SFX
            sfx_efetivo = int(round(vol_sfx * (vol_master / 100.0)))
            SoundManager.set_sfx_volume(sfx_efetivo)

            # Aplica volume de Música e toca a faixa dinâmica de menu (8bits-control)
            from src.sistemas.sistema_musica import obter_sistema_musica
            sistema_musica = obter_sistema_musica()
            sistema_musica.inicializar()
            sistema_musica.atualizar_volume(vol_master, vol_musica)
            sistema_musica.tocar_menu()
        except Exception:
            pass

    def loop(self):
        try:
            pygame.mouse.set_visible(True)
        except Exception:
            pass

        dt = min(self.janela.delta_time(), 0.1)
        self._ultimo_dt = dt
        self.tempo_acumulado += dt

        if getattr(self, "mostrar_popup_tutorial", False):
            if self.cooldown_input > 0.0:
                self.cooldown_input = max(0.0, self.cooldown_input - dt)
                return
            mx, my = None, None
            if self.mouse is not None and hasattr(self.mouse, "get_position"):
                try:
                    mx, my = self.mouse.get_position()
                except Exception:
                    mx, my = None, None
            clicou = False
            if self.mouse is not None and hasattr(self.mouse, "button_down"):
                try:
                    clicou = bool(self.mouse.button_down(1))
                except Exception:
                    clicou = False
            if clicou and mx is not None and my is not None:
                _, btn_ver, btn_nao = self._obter_rects_popup_tutorial()
                if btn_ver.collidepoint(mx, my):
                    self._confirmar_popup_tutorial(True)
                    return
                if btn_nao.collidepoint(mx, my):
                    self._confirmar_popup_tutorial(False)
                    return
            if self.teclado is not None and hasattr(self.teclado, "key_down"):
                if self.teclado.key_down("ENTER") or self.teclado.key_down("SPACE") or self.teclado.key_down("t") or self.teclado.key_down("T"):
                    self._confirmar_popup_tutorial(True)
                    return
                if self.teclado.key_down("ESC"):
                    self._confirmar_popup_tutorial(False)
                    return
            return

        # Se o Menu de Configurações estiver aberto, delega o loop para ele
        if self.menu_configs.ativo:
            self.menu_configs.update(dt, self.teclado, self.mouse)
            if not self.menu_configs.ativo:
                self.cooldown_input = 0.18
            return

        if getattr(self, "menu_conquistas", None) is not None and self.menu_conquistas.ativo:
            self.menu_conquistas.update(dt, self.teclado, self.mouse)
            if not self.menu_conquistas.ativo:
                self.cooldown_input = 0.18
            return

        if self.cooldown_input > 0.0:
            self.cooldown_input = max(0.0, self.cooldown_input - dt)
            return

        # Atalho direto para Configurações via tecla 'C'
        if hasattr(self.teclado, "key_down") and (self.teclado.key_down("c") or self.teclado.key_down("C")):
            self.menu_configs.abrir()
            return

        # Atalho direto para Conquistas & Firmware via tecla 'F'
        if hasattr(self.teclado, "key_down") and (self.teclado.key_down("f") or self.teclado.key_down("F")):
            self.menu_conquistas.abrir()
            return

        # Atalho direto para Tutorial via tecla 'T'
        if hasattr(self.teclado, "key_down") and (self.teclado.key_down("t") or self.teclado.key_down("T")):
            self.abrir_tutorial()
            return

        # Suporte a mouse (hover e clique nos botões do menu e seletor de Loadout)
        inicio_y = 232
        espacamento = 44
        mx, my = None, None
        if self.mouse is not None and hasattr(self.mouse, "get_position"):
            try:
                mx, my = self.mouse.get_position()
            except Exception:
                mx, my = None, None

        mouse_clicado = False
        if self.mouse is not None and hasattr(self.mouse, "button_down"):
            try:
                if self.mouse.button_down(1):
                    mouse_clicado = True
            except Exception:
                pass

        if mx is not None and my is not None:
            for i in range(len(self.opcoes)):
                y = inicio_y + i * espacamento
                rect_opcao = pygame.Rect(0, y - 5, 320, 34)
                rect_opcao.centerx = LARGURA_TELA // 2
                if rect_opcao.collidepoint(mx, my):
                    self.opcao_selecionada = i
                    if mouse_clicado:
                        self._executar_opcao_selecionada()
                        return
            r_slot1, r_slot2 = self._obter_rects_loadout()
            if mouse_clicado:
                if r_slot1.collidepoint(mx, my):
                    self.alternar_loadout_slot1()
                    self.cooldown_input = 0.14
                    return
                if r_slot2.collidepoint(mx, my):
                    self.alternar_loadout_slot2()
                    self.cooldown_input = 0.14
                    return

        # Navegação com Teclado
        if self.teclado.key_down("UP") or self.teclado.key_down("w"):
            self.opcao_selecionada = (self.opcao_selecionada - 1) % len(self.opcoes)
            self.confirmar_reset_save = False
            self.opcoes[4] = "RESETAR DADOS SALVOS"
        elif self.teclado.key_down("DOWN") or self.teclado.key_down("s"):
            self.opcao_selecionada = (self.opcao_selecionada + 1) % len(self.opcoes)
            self.confirmar_reset_save = False
            self.opcoes[4] = "RESETAR DADOS SALVOS"

        if getattr(self, "aviso_reset_timer", 0.0) > 0.0:
            self.aviso_reset_timer = max(0.0, self.aviso_reset_timer - dt)
            if self.aviso_reset_timer <= 0.0:
                self.opcoes[4] = "RESETAR DADOS SALVOS"

        # Seleção de opções
        if self.teclado.key_down("ENTER") or self.teclado.key_down("SPACE"):
            self._executar_opcao_selecionada()

        if self.teclado.key_down("ESC"):
            self.sair_jogo()

    @staticmethod
    def _obter_rects_popup_tutorial() -> tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
        """Retorna (modal_rect, btn_ver_tutorial, btn_agora_nao) em coords lógicas 1280x720."""
        mw, mh = 560, 210
        mx = (LARGURA_TELA - mw) // 2
        my = (ALTURA_TELA - mh) // 2
        modal_rect = pygame.Rect(mx, my, mw, mh)
        btn_ver = pygame.Rect(mx + 44, my + 136, 220, 42)
        btn_nao = pygame.Rect(mx + mw - 44 - 220, my + 136, 220, 42)
        return modal_rect, btn_ver, btn_nao

    def _confirmar_popup_tutorial(self, abrir_tutorial: bool):
        """Marca tutorial_visto=True, salva save.json e opcionalmente abre o Tutorial."""
        self.mostrar_popup_tutorial = False
        self.cooldown_input = 0.2
        if hasattr(self, "gerenciador_config") and self.gerenciador_config is not None:
            self.gerenciador_config.tutorial_visto = True
            try:
                self.gerenciador_config.salvar_arquivo(SAVE_FILE_PATH)
            except Exception:
                pass
        if abrir_tutorial:
            self.abrir_tutorial()

    @staticmethod
    def _obter_rects_loadout() -> tuple[pygame.Rect, pygame.Rect]:
        """Retorna os retângulos lógicos (1280x720) do seletor compacto de Loadout."""
        r_slot1 = pygame.Rect(850, 258, 280, 44)
        r_slot2 = pygame.Rect(850, 314, 280, 44)
        return r_slot1, r_slot2

    def alternar_loadout_slot1(self) -> bool:
        """Alterna Slot 1 entre Chave de Manutenção e Bastão de Choque (se desbloqueado)."""
        sys_conq = getattr(self.gerenciador_config, "sistema_conquistas", None)
        atual = self.gerenciador_config.loadout.get("slot1", "chave_manutencao")
        if atual == "chave_manutencao":
            if sys_conq is not None and sys_conq.possui_recompensa("arma", "bastao_choque"):
                ok = self.gerenciador_config.definir_loadout("slot1", "bastao_choque")
                if ok:
                    self.gerenciador_config.salvar_arquivo(SAVE_FILE_PATH)
                return ok
            return False
        ok = self.gerenciador_config.definir_loadout("slot1", "chave_manutencao")
        if ok:
            self.gerenciador_config.salvar_arquivo(SAVE_FILE_PATH)
        return ok

    def alternar_loadout_slot2(self) -> bool:
        """Alterna Slot 2 entre Pistola Padrão e SMG Compacta (se desbloqueada)."""
        sys_conq = getattr(self.gerenciador_config, "sistema_conquistas", None)
        atual = self.gerenciador_config.loadout.get("slot2", "pistola")
        if atual == "pistola":
            if sys_conq is not None and sys_conq.possui_recompensa("arma", "smg_compacta"):
                ok = self.gerenciador_config.definir_loadout("slot2", "smg_compacta")
                if ok:
                    self.gerenciador_config.salvar_arquivo(SAVE_FILE_PATH)
                return ok
            return False
        ok = self.gerenciador_config.definir_loadout("slot2", "pistola")
        if ok:
            self.gerenciador_config.salvar_arquivo(SAVE_FILE_PATH)
        return ok

    def _executar_opcao_selecionada(self):
        if self.opcao_selecionada == 0:
            self.iniciar_jogo()
        elif self.opcao_selecionada == 1:
            self.menu_configs.abrir()
        elif self.opcao_selecionada == 2:
            self.menu_conquistas.abrir()
        elif self.opcao_selecionada == 3:
            self.abrir_tutorial()
        elif self.opcao_selecionada == 4:
            if not getattr(self, "confirmar_reset_save", False):
                self.confirmar_reset_save = True
                self.opcoes[4] = "CONFIRMAR RESET?"
            else:
                self.confirmar_reset_save = False
                self.gerenciador_config.from_dict({})
                self.gerenciador_config.salvar_arquivo()
                self.opcoes[4] = "DADOS RESETADOS!"
                self.aviso_reset_timer = 2.0
        elif self.opcao_selecionada == 5:
            self.sair_jogo()

    def abrir_tutorial(self):
        from PPlay.scenemanager import SceneManager
        from src.cenas.tutorial import TutorialScene
        SceneManager.change_scene(TutorialScene())

    def draw(self):
        screen = self.janela.screen

        # Se o Menu de Configurações ou Conquistas estiver ativo, desenha-o
        if self.menu_configs.ativo:
            self.menu_configs.draw(screen)
            return
        if getattr(self, "menu_conquistas", None) is not None and self.menu_conquistas.ativo:
            self.menu_conquistas.draw(screen)
            return

        # Projeção Native-DPI (espelha Janela._calcular_viewport e screen_to_virtual_coords 1:1)
        sw, sh = screen.get_size()
        scale = min(sw / float(LARGURA_TELA), sh / float(ALTURA_TELA))
        vx = (sw - int(round(LARGURA_TELA * scale))) // 2
        vy = (sh - int(round(ALTURA_TELA * scale))) // 2

        def px(val: float) -> int:
            return vx + int(round(val * scale))

        def py(val: float) -> int:
            return vy + int(round(val * scale))

        def ps(val: float) -> int:
            return max(1, int(round(val * scale)))

        # Fontes nativas cacheadas por resolução
        fonte_titulo = _carregar_fonte_sans(max(8, int(round(40 * scale))), bold=True)
        fonte_sub = _carregar_fonte_sans(max(8, int(round(13 * scale))), bold=False)
        fonte_badge = _carregar_fonte_mono(max(8, int(round(13 * scale))), bold=True)
        fonte_opcoes = _carregar_fonte_sans(max(8, int(round(16 * scale))), bold=True)
        fonte_hotkey = _carregar_fonte_mono(max(8, int(round(11 * scale))), bold=True)
        fonte_rodape = _carregar_fonte_mono(max(8, int(round(12 * scale))), bold=False)

        # Fundo Cyber-Office (#07090e) cobrindo toda a tela nativa (sw, sh) com grade geométrica sutil
        screen.fill(_C_BACKDROP)
        grid_step = max(20, ps(40))
        for gx in range(grid_step, sw, grid_step):
            pygame.draw.line(screen, _C_GRID, (gx, 0), (gx, sh), 1)
        for gy in range(grid_step, sh, grid_step):
            pygame.draw.line(screen, _C_GRID, (0, gy), (sw, gy), 1)

        # Filete superior assinatura Roxo / Dourado cobrindo toda a largura nativa
        stripe_h = max(2, ps(3))
        pygame.draw.rect(screen, _C_PURPLE, (0, 0, sw // 2, stripe_h))
        pygame.draw.rect(screen, _C_GOLD, (sw // 2, 0, sw - sw // 2, stripe_h))

        # Título principal perfeitamente centralizado em y=88..136 (lógico)
        centro_x = px(LARGURA_TELA // 2)
        titulo_sombra = fonte_titulo.render(TITULO_JOGO, True, (0, 0, 0))
        titulo_surf = fonte_titulo.render(TITULO_JOGO, True, _C_GOLD)
        titulo_rect = titulo_surf.get_rect(centerx=centro_x, top=py(88))
        sh_off = max(1, ps(2))
        screen.blit(titulo_sombra, (titulo_rect.x + sh_off, titulo_rect.y + sh_off))
        screen.blit(titulo_surf, titulo_rect)

        if self._cleiton_base is not None:
            tam_cleiton = ps(44)
            if self._cleiton_sprite is None or self._cleiton_sprite_tam != tam_cleiton:
                self._cleiton_sprite = pygame.transform.scale(self._cleiton_base, (tam_cleiton, tam_cleiton))
                self._cleiton_sprite_tam = tam_cleiton
            emblema_sz = ps(52)
            emblema_r = pygame.Rect(0, 0, emblema_sz, emblema_sz)
            emblema_r.right = titulo_rect.left - ps(16)
            emblema_r.centery = titulo_rect.centery
            pygame.draw.rect(screen, _C_HUD_PANEL, emblema_r, border_radius=ps(10))
            pygame.draw.rect(screen, _C_PURPLE, emblema_r, width=max(1, ps(1)), border_radius=ps(10))
            screen.blit(self._cleiton_sprite, self._cleiton_sprite.get_rect(center=emblema_r.center))

        sub_surf = fonte_sub.render("SOBREVIVÊNCIA CYBER-OFFICE  •  CONFIGURAÇÕES COMO MECÂNICA", True, _C_TEXT_SECONDARY)
        screen.blit(sub_surf, sub_surf.get_rect(centerx=centro_x, top=py(144)))

        # Badge de Recorde e Melhor Tempo (Estatísticas Globais em monospace)
        estatisticas = self.gerenciador_config.obter_estatisticas()
        high_score = estatisticas.get("high_score", 0)
        melhor_tempo = estatisticas.get("melhor_tempo", 0.0)
        m_tempo = int(melhor_tempo // 60)
        s_tempo = int(melhor_tempo % 60)

        badge_rect = pygame.Rect(0, py(178), ps(520), ps(36))
        badge_rect.centerx = centro_x
        pygame.draw.rect(screen, _C_HUD_PANEL, badge_rect, border_radius=ps(8))
        pygame.draw.rect(screen, _C_BORDER, badge_rect, width=max(1, ps(1)), border_radius=ps(8))

        texto_badge = f"RECORDE: {high_score:,} PTS   •   MELHOR TEMPO: {m_tempo:02d}:{s_tempo:02d}"
        badge_surf = fonte_badge.render(texto_badge, True, _C_CYAN)
        badge_text_rect = badge_surf.get_rect(center=badge_rect.center)
        screen.blit(badge_surf, badge_text_rect)

        # Painel central das opções (inicio_y=232, espacamento=44)
        inicio_y = 232
        espacamento = 44

        for i, texto in enumerate(self.opcoes):
            y = inicio_y + i * espacamento
            selecionado = (i == self.opcao_selecionada)
            lift = -2 if selecionado else 0

            caixa = pygame.Rect(0, py(y - 6 + lift), ps(320), ps(38))
            caixa.centerx = centro_x
            cor_bg = _C_CARD_HOVER if selecionado else _C_CARD
            cor_borda = _C_GOLD if (selecionado and i == 0) else (_C_CYAN if selecionado else _C_ELEVATED)

            pygame.draw.rect(screen, cor_bg, caixa, border_radius=ps(8))
            pygame.draw.rect(screen, cor_borda, caixa, width=ps(2) if selecionado else max(1, ps(1)), border_radius=ps(8))
            if selecionado:
                pygame.draw.rect(
                    screen,
                    cor_borda,
                    (caixa.x + max(1, ps(1)), caixa.y + ps(7), max(2, ps(3)), caixa.height - ps(14)),
                    border_radius=max(1, ps(2))
                )

            if "[" in texto and texto.endswith("]"):
                idx_col = texto.rfind("[")
                rotulo = texto[:idx_col].strip()
                atalho = texto[idx_col:].strip()
            else:
                rotulo = texto
                atalho = ""

            cor_texto = _C_GOLD if (selecionado and i == 0) else (_C_TEXT_PRIMARY if selecionado else _C_TEXT_SECONDARY)
            opcao_surf = fonte_opcoes.render(rotulo, True, cor_texto)
            screen.blit(opcao_surf, opcao_surf.get_rect(left=caixa.x + ps(18), centery=caixa.centery))

            if atalho:
                hk_fg = _C_BACKDROP if selecionado else _C_TEXT_SECONDARY
                hk_bg = cor_borda if selecionado else _C_ELEVATED
                hk_surf = fonte_hotkey.render(atalho, True, hk_fg)
                hk_pill = pygame.Rect(0, 0, hk_surf.get_width() + ps(14), hk_surf.get_height() + ps(8))
                hk_pill.right = caixa.right - ps(12)
                hk_pill.centery = caixa.centery
                pygame.draw.rect(screen, hk_bg, hk_pill, border_radius=ps(5))
                screen.blit(hk_surf, hk_surf.get_rect(center=hk_pill.center))

        # Seletor compacto de Loadout Inicial (Slot 1 / Slot 2)
        r_s1_l, r_s2_l = self._obter_rects_loadout()
        sys_conq = getattr(self.gerenciador_config, "sistema_conquistas", None)
        s1_id = self.gerenciador_config.loadout.get("slot1", "chave_manutencao")
        s2_id = self.gerenciador_config.loadout.get("slot2", "pistola")
        s1_lib = bool(sys_conq is not None and sys_conq.possui_recompensa("arma", "bastao_choque"))
        s2_lib = bool(sys_conq is not None and sys_conq.possui_recompensa("arma", "smg_compacta"))

        painel_loadout = pygame.Rect(px(838), py(228), ps(304), ps(142))
        pygame.draw.rect(screen, _C_HUD_PANEL, painel_loadout, border_radius=ps(8))
        pygame.draw.rect(screen, _C_BORDER, painel_loadout, width=max(1, ps(1)), border_radius=ps(8))
        tit_ld = fonte_hotkey.render("LOADOUT INICIAL (CLIQUE P/ TROCAR)", True, _C_CYAN)
        screen.blit(tit_ld, (px(850), py(236)))

        for r_l, label_slot, arma_id, liberada_alt in [
            (r_s1_l, "SLOT 1:", s1_id, s1_lib),
            (r_s2_l, "SLOT 2:", s2_id, s2_lib),
        ]:
            r_p = pygame.Rect(px(r_l.x), py(r_l.y), ps(r_l.width), ps(r_l.height))
            pygame.draw.rect(screen, _C_CARD, r_p, border_radius=ps(6))
            pygame.draw.rect(screen, _C_PURPLE if liberada_alt else _C_ELEVATED, r_p, width=max(1, ps(1)), border_radius=ps(6))
            nome_arma = arma_id.replace("_", " ").upper()
            s_lbl = fonte_hotkey.render(f"{label_slot} {nome_arma}", True, _C_TEXT_PRIMARY)
            screen.blit(s_lbl, (r_p.x + ps(10), r_p.y + ps(8)))
            sub = "TROCA DISPONÍVEL" if liberada_alt else "ALT. BLOQUEADA"
            s_sub = fonte_hotkey.render(sub, True, _C_GOLD if liberada_alt else _C_TEXT_SECONDARY)
            screen.blit(s_sub, (r_p.x + ps(10), r_p.y + ps(24)))

        # Rodapé com instruções perfeitamente centralizado
        dica_rect = pygame.Rect(0, py(516), ps(700), ps(56))
        dica_rect.centerx = centro_x
        if hasattr(self, "banner_dicas") and self.banner_dicas is not None:
            self.banner_dicas.atualizar(getattr(self, "_ultimo_dt", 0.0))
            self.banner_dicas.desenhar(screen, dica_rect, scale=scale)

        rodape_surf = fonte_rodape.render(
            "[W/S] ou [Setas] Navegar   •   [ENTER] Confirmar   •   [C] Configurações   •   [T] Tutorial",
            True,
            _C_TEXT_MUTED
        )
        rodape_rect = rodape_surf.get_rect(centerx=centro_x, bottom=py(ALTURA_TELA - 25))
        screen.blit(rodape_surf, rodape_rect)

        if getattr(self, "mostrar_popup_tutorial", False):
            if (sw, sh) not in self._popup_overlay_cache:
                ov = pygame.Surface((sw, sh), pygame.SRCALPHA)
                ov.fill((6, 9, 16, 200))
                self._popup_overlay_cache[(sw, sh)] = ov
            screen.blit(self._popup_overlay_cache[(sw, sh)], (0, 0))

            m_l, bv_l, bn_l = self._obter_rects_popup_tutorial()
            m_r = pygame.Rect(px(m_l.x), py(m_l.y), ps(m_l.width), ps(m_l.height))
            bv_r = pygame.Rect(px(bv_l.x), py(bv_l.y), ps(bv_l.width), ps(bv_l.height))
            bn_r = pygame.Rect(px(bn_l.x), py(bn_l.y), ps(bn_l.width), ps(bn_l.height))

            pygame.draw.rect(screen, _C_HUD_PANEL, m_r, border_radius=ps(10))
            pygame.draw.rect(screen, _C_CYAN, m_r, width=max(1, ps(2)), border_radius=ps(10))
            meio_p = (m_r.width - ps(24)) // 2
            pygame.draw.rect(screen, _C_PURPLE, (m_r.x + ps(12), m_r.y + 1, meio_p, max(2, ps(2))))
            pygame.draw.rect(screen, _C_GOLD, (m_r.x + ps(12) + meio_p, m_r.y + 1, meio_p, max(2, ps(2))))

            t_pop = fonte_badge.render("BEM-VINDO AO PROTOCOLO: BATATA", True, _C_GOLD)
            screen.blit(t_pop, t_pop.get_rect(centerx=m_r.centerx, top=m_r.y + ps(22)))

            msg1 = fonte_opcoes.render("Parece ser sua primeira vez jogando —", True, _C_TEXT_PRIMARY)
            msg2 = fonte_opcoes.render("que tal ver o tutorial?", True, _C_TEXT_PRIMARY)
            screen.blit(msg1, msg1.get_rect(centerx=m_r.centerx, top=m_r.y + ps(56)))
            screen.blit(msg2, msg2.get_rect(centerx=m_r.centerx, top=m_r.y + ps(82)))

            pygame.draw.rect(screen, (22, 48, 62), bv_r, border_radius=ps(6))
            pygame.draw.rect(screen, _C_CYAN, bv_r, width=max(1, ps(2)), border_radius=ps(6))
            s_ver = fonte_badge.render("Ver Tutorial", True, _C_TEXT_PRIMARY)
            screen.blit(s_ver, s_ver.get_rect(center=bv_r.center))

            pygame.draw.rect(screen, _C_CARD, bn_r, border_radius=ps(6))
            pygame.draw.rect(screen, _C_BORDER, bn_r, width=max(1, ps(1)), border_radius=ps(6))
            s_nao = fonte_badge.render("Agora Não", True, _C_TEXT_SECONDARY)
            screen.blit(s_nao, s_nao.get_rect(center=bn_r.center))

    def iniciar_jogo(self):
        from PPlay.scenemanager import SceneManager
        from src.cenas.gameplay import GameplayScene
        SceneManager.change_scene(GameplayScene())

    def sair_jogo(self):
        self.janela.close()
