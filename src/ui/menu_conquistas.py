"""
Modal Dual-Tab de Conquistas & Chips de Firmware — Protocolo: Batata (v2.0)
Estética Cyber-Office:
- Aba 0 (CONQUISTAS): 5 Contínuas (3 milestones + barra de progresso) + 11 Únicas,
  filtros (Todas / Contínuas / Únicas / Fixadas) e botão [FIXAR] (0..3 pins na HUD).
- Aba 1 (FIRMWARE): 9 Chips de Firmware em 1..3 slots.
  - No Menu Principal (em_jogo=False): editável, salva save.json imediatamente ao equipar/desequipar.
  - Na Pausa (em_jogo=True): ESTRITAMENTE SOMENTE LEITURA (badge visível, cliques bloqueados).
Regra de ouro: ZERO criação de fontes e ZERO I/O em disco dentro de draw()!
"""

import pygame
from typing import Optional

from src.sistemas.conquistas_dados import (
    CHIPS_FIRMWARE,
    CONQUISTAS_CONTINUAS,
    CONQUISTAS_UNICAS,
)
from src.ui.hud import formatar_recompensas_conquista
from src.utils.constantes import (
    LARGURA_TELA,
    ALTURA_TELA,
    BRANCO,
    SAVE_FILE_PATH,
)
from src.utils.math_utils import clamp


COR_BG_MODAL = (11, 14, 23)
COR_CARD = (17, 24, 39)
COR_ELEVADO = (30, 41, 59)
COR_BORDA = (51, 65, 85)
COR_CIANO = (34, 211, 238)
COR_ROXO = (168, 85, 247)
COR_VERDE = (16, 185, 129)
COR_OURO = (251, 191, 36)
COR_AMBAR = (245, 158, 11)
COR_CARMESIM = (239, 68, 68)
COR_TEXTO_SUAVE = (148, 163, 184)

FILTROS_CONQUISTAS = ("Todas", "Contínuas", "Únicas", "Fixadas")


def _criar_fonte(nomes: tuple[str, ...], tamanho: int, bold: bool = False) -> pygame.font.Font:
    for nome in nomes:
        try:
            f = pygame.font.SysFont(nome, tamanho, bold=bold)
            if f is not None:
                return f
        except Exception:
            continue
    return pygame.font.Font(None, tamanho)


class MenuConquistas:
    """Modal Cyber-Office de Conquistas (0..3 pins) e Chips de Firmware (1..3 slots)."""

    def __init__(
        self,
        gerenciador_config,
        sistema_conquistas=None,
        em_jogo: bool = False,
        cena=None,
    ):
        self.gerenciador_config = gerenciador_config
        self.sistema_conquistas = (
            sistema_conquistas
            if sistema_conquistas is not None
            else getattr(gerenciador_config, "sistema_conquistas", None)
        )
        self.em_jogo = bool(em_jogo)
        self.cena = cena

        self.ativo: bool = False
        self.aba_atual: int = 0  # 0 = CONQUISTAS, 1 = FIRMWARE
        self.filtro_atual: str = "Todas"
        self.indice_selecionado: int = 0
        self.scroll_y: float = 0.0
        self.cooldown_input: float = 0.0
        self._mouse_prev_down: bool = False
        self._mensagem_feedback: str = ""
        self._timer_feedback: float = 0.0

        self.largura_modal = 780
        self.altura_modal = 560
        self.offset_x = (LARGURA_TELA - self.largura_modal) // 2
        self.offset_y = (ALTURA_TELA - self.altura_modal) // 2

        # Cache de fontes inicializado no __init__ (zero alocação em draw)
        self._fontes: dict[tuple[str, int, bool], pygame.font.Font] = {
            ("sans", 20, True): _criar_fonte(("DejaVu Sans", "Arial"), 20, bold=True),
            ("sans", 15, True): _criar_fonte(("DejaVu Sans", "Arial"), 15, bold=True),
            ("sans", 13, True): _criar_fonte(("DejaVu Sans", "Arial"), 13, bold=True),
            ("sans", 12, False): _criar_fonte(("DejaVu Sans", "Arial"), 12, bold=False),
            ("sans", 11, True): _criar_fonte(("DejaVu Sans", "Arial"), 11, bold=True),
            ("mono", 12, True): _criar_fonte(("DejaVu Sans Mono", "Consolas", "Courier New"), 12, bold=True),
            ("mono", 11, True): _criar_fonte(("DejaVu Sans Mono", "Consolas", "Courier New"), 11, bold=True),
            ("mono", 10, False): _criar_fonte(("DejaVu Sans Mono", "Consolas", "Courier New"), 10, bold=False),
        }

        self._overlay_cache: dict[tuple[int, int], pygame.Surface] = {}

    def _fonte(self, familia: str, px: int, bold: bool = True) -> pygame.font.Font:
        chave = (familia, px, bold)
        if chave not in self._fontes:
            nomes = ("DejaVu Sans Mono", "Consolas", "Courier New") if familia == "mono" else ("DejaVu Sans", "Arial")
            self._fontes[chave] = _criar_fonte(nomes, px, bold=bold)
        return self._fontes[chave]

    def abrir(self, aba: int | None = None):
        self.ativo = True
        if aba is not None:
            self.aba_atual = int(aba) % 2
        self.scroll_y = 0.0
        self.indice_selecionado = 0
        self.cooldown_input = 0.22
        self._mouse_prev_down = False
        self._mensagem_feedback = ""
        self._timer_feedback = 0.0
        try:
            pygame.mouse.set_visible(True)
        except Exception:
            pass

    @staticmethod
    def _garantir_coords_virtuais(mx: float, my: float) -> tuple[float, float]:
        """Converte coordenadas nativas da janela para o canvas virtual 1280x720 se necessário."""
        try:
            surf = pygame.display.get_surface()
            if surf is not None:
                sw, sh = surf.get_size()
                if (sw, sh) != (LARGURA_TELA, ALTURA_TELA) and sw > 0 and sh > 0:
                    scale = min(sw / float(LARGURA_TELA), sh / float(ALTURA_TELA))
                    vx = (sw - LARGURA_TELA * scale) * 0.5
                    vy = (sh - ALTURA_TELA * scale) * 0.5
                    if scale > 0:
                        return (mx - vx) / scale, (my - vy) / scale
        except Exception:
            pass
        return mx, my

    def fechar(self):
        self.ativo = False
        if not self.em_jogo and self.gerenciador_config is not None:
            self.gerenciador_config.salvar_arquivo(SAVE_FILE_PATH)

    def alternar_aba(self, nova_aba: int):
        self.aba_atual = int(nova_aba) % 2
        self.scroll_y = 0.0
        self.indice_selecionado = 0

    def _salvar_se_fora_de_jogo(self):
        if not self.em_jogo and self.gerenciador_config is not None:
            self.gerenciador_config.salvar_arquivo(SAVE_FILE_PATH)

    def tentar_alternar_fixada(self, conquista_id: str) -> bool:
        if self.sistema_conquistas is None:
            return False
        ok = self.sistema_conquistas.alternar_fixada(conquista_id)
        if ok:
            self._mensagem_feedback = "Pin atualizado!"
            self._timer_feedback = 1.6
            self._salvar_se_fora_de_jogo()
        else:
            self._mensagem_feedback = "Máximo de 3 conquistas fixadas."
            self._timer_feedback = 1.8
        return ok

    def tentar_alternar_firmware(self, chip_id: str) -> bool:
        """
        Equipa/desequipa um Chip de Firmware quando em_jogo=False.
        Bloqueia estritamente quando em_jogo=True (somente leitura na pausa).
        """
        if self.em_jogo:
            self._mensagem_feedback = "Firmware somente leitura durante a partida!"
            self._timer_feedback = 2.0
            return False
        if self.sistema_conquistas is None:
            return False

        equipados = self.sistema_conquistas.modificadores_equipados
        if chip_id in equipados:
            ok = self.sistema_conquistas.desequipar_firmware(chip_id)
            if ok:
                self._mensagem_feedback = "Chip desequipado."
                self._timer_feedback = 1.5
                self._salvar_se_fora_de_jogo()
            return ok

        ok = self.sistema_conquistas.equipar_firmware(chip_id)
        if ok:
            self._mensagem_feedback = "Chip equipado!"
            self._timer_feedback = 1.5
            self._salvar_se_fora_de_jogo()
        else:
            if not self.sistema_conquistas.possui_recompensa("modificador_run", chip_id):
                self._mensagem_feedback = "Chip bloqueado por conquista."
            else:
                self._mensagem_feedback = "Todos os slots de Firmware ocupados."
            self._timer_feedback = 1.8
        return ok

    def _obter_itens_conquistas(self) -> list[tuple[str, str, object]]:
        itens: list[tuple[str, str, object]] = []
        fixadas = set(getattr(self.sistema_conquistas, "fixadas", []))
        if self.filtro_atual in ("Todas", "Contínuas", "Fixadas"):
            for cid, cdef in CONQUISTAS_CONTINUAS.items():
                if self.filtro_atual == "Fixadas" and cid not in fixadas:
                    continue
                itens.append(("continua", cid, cdef))
        if self.filtro_atual in ("Todas", "Únicas", "Fixadas"):
            for cid, cdef in CONQUISTAS_UNICAS.items():
                if self.filtro_atual == "Fixadas" and cid not in fixadas:
                    continue
                itens.append(("unica", cid, cdef))
        return itens

    def _obter_rects_topo(self) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
        ox, oy = self.offset_x, self.offset_y
        aba0 = pygame.Rect(ox + 28, oy + 56, 190, 32)
        aba1 = pygame.Rect(ox + 228, oy + 56, 220, 32)
        fechar = pygame.Rect(ox + self.largura_modal - 128, oy + 56, 100, 32)
        return aba0, aba1, fechar

    def _obter_rects_filtros(self) -> list[tuple[str, pygame.Rect]]:
        ox, oy = self.offset_x, self.offset_y
        rects = []
        x = ox + 28
        for nome in FILTROS_CONQUISTAS:
            w = 96
            rects.append((nome, pygame.Rect(x, oy + 98, w, 26)))
            x += w + 8
        return rects

    def update(self, dt: float, teclado=None, mouse=None):
        if not self.ativo:
            return

        if self.cooldown_input > 0.0:
            self.cooldown_input = max(0.0, self.cooldown_input - dt)
        if self._timer_feedback > 0.0:
            self._timer_feedback = max(0.0, self._timer_feedback - dt)

        if teclado is not None:
            if self.cooldown_input <= 0.0:
                if (hasattr(teclado, "key_down") and teclado.key_down("ESC")) or (
                    hasattr(teclado, "key_pressed") and teclado.key_pressed("ESC")
                ):
                    self.fechar()
                    return

            if (hasattr(teclado, "key_down") and teclado.key_down("TAB")) or (
                hasattr(teclado, "key_pressed") and teclado.key_pressed("TAB")
            ):
                self.alternar_aba((self.aba_atual + 1) % 2)
                return

            if hasattr(teclado, "key_down"):
                if teclado.key_down("UP") or teclado.key_down("w") or teclado.key_down("W"):
                    self.indice_selecionado = max(0, self.indice_selecionado - 1)
                elif teclado.key_down("DOWN") or teclado.key_down("s") or teclado.key_down("S"):
                    total = len(self._obter_itens_conquistas()) if self.aba_atual == 0 else len(CHIPS_FIRMWARE)
                    self.indice_selecionado = min(max(0, total - 1), self.indice_selecionado + 1)
                elif teclado.key_down("RETURN") or teclado.key_down("SPACE"):
                    if self.aba_atual == 0:
                        itens = self._obter_itens_conquistas()
                        if 0 <= self.indice_selecionado < len(itens):
                            self.tentar_alternar_fixada(itens[self.indice_selecionado][1])
                    else:
                        chips = list(CHIPS_FIRMWARE.keys())
                        if 0 <= self.indice_selecionado < len(chips):
                            self.tentar_alternar_firmware(chips[self.indice_selecionado])

        try:
            pygame.mouse.set_visible(True)
        except Exception:
            pass

        if mouse is not None and hasattr(mouse, "get_position"):
            try:
                mx, my = mouse.get_position()
            except Exception:
                mx, my = self._garantir_coords_virtuais(*pygame.mouse.get_pos())
        else:
            mx, my = self._garantir_coords_virtuais(*pygame.mouse.get_pos())

        self._hover_pos = (mx, my)

        wheel = 0
        if mouse is not None and hasattr(mouse, "get_wheel_delta"):
            try:
                wheel = mouse.get_wheel_delta()
            except Exception:
                wheel = 0
        if not wheel:
            try:
                for ev in pygame.event.get(pygame.MOUSEWHEEL):
                    wheel += ev.y
            except Exception:
                pass
        if wheel:
            self.scroll_y = max(0.0, self.scroll_y - wheel * 28.0)

        mouse_down = False
        mouse_edge_down = False
        if mouse is not None:
            try:
                if hasattr(mouse, "button_down") and mouse.button_down(1):
                    mouse_edge_down = True
                if hasattr(mouse, "is_button_down") and mouse.is_button_down(1):
                    mouse_down = True
                elif hasattr(mouse, "is_button_pressed") and mouse.is_button_pressed(1):
                    mouse_down = True
                elif hasattr(mouse, "button_pressed") and mouse.button_pressed(1):
                    mouse_down = True
            except Exception:
                pass
        if not mouse_down:
            try:
                mouse_down = bool(pygame.mouse.get_pressed()[0])
            except Exception:
                pass

        clicou = mouse_edge_down or (mouse_down and not self._mouse_prev_down)
        self._mouse_prev_down = mouse_down

        # Hover nos cards para feedback visual
        if self.aba_atual == 0:
            area_y = self.offset_y + 134
            area_h = self.altura_modal - 178
            itens_hover = self._obter_itens_conquistas()
            card_h = 92
            gap = 8
            for idx_h, _ in enumerate(itens_hover):
                cy = area_y + idx_h * (card_h + gap) - int(self.scroll_y)
                if cy + card_h < area_y or cy > area_y + area_h:
                    continue
                if pygame.Rect(self.offset_x + 28, cy, self.largura_modal - 56, card_h).collidepoint(mx, my):
                    self.indice_selecionado = idx_h
                    break
        else:
            area_y = self.offset_y + 134
            area_h = self.altura_modal - 178
            card_w = (self.largura_modal - 72) // 2
            card_h = 98
            gap_x = 16
            gap_y = 10
            for idx_h, _ in enumerate(CHIPS_FIRMWARE.keys()):
                col = idx_h % 2
                row = idx_h // 2
                cx = self.offset_x + 28 + col * (card_w + gap_x)
                cy = area_y + row * (card_h + gap_y) - int(self.scroll_y)
                if cy + card_h < area_y or cy > area_y + area_h:
                    continue
                if pygame.Rect(cx, cy, card_w, card_h).collidepoint(mx, my):
                    self.indice_selecionado = idx_h
                    break

        if not clicou or self.cooldown_input > 0.0:
            return

        aba0, aba1, btn_fechar = self._obter_rects_topo()
        if btn_fechar.collidepoint(mx, my):
            self.fechar()
            return
        if aba0.collidepoint(mx, my):
            self.alternar_aba(0)
            return
        if aba1.collidepoint(mx, my):
            self.alternar_aba(1)
            return

        if self.aba_atual == 0:
            for nome_f, r_f in self._obter_rects_filtros():
                if r_f.collidepoint(mx, my):
                    self.filtro_atual = nome_f
                    self.scroll_y = 0.0
                    self.indice_selecionado = 0
                    return

            area_y = self.offset_y + 134
            area_h = self.altura_modal - 178
            itens = self._obter_itens_conquistas()
            card_h = 92
            gap = 8
            for idx, (_tipo, cid, _cdef) in enumerate(itens):
                cy = area_y + idx * (card_h + gap) - int(self.scroll_y)
                if cy + card_h < area_y or cy > area_y + area_h:
                    continue
                btn_pin = pygame.Rect(self.offset_x + self.largura_modal - 134, cy + 28, 96, 28)
                if btn_pin.collidepoint(mx, my):
                    self.tentar_alternar_fixada(cid)
                    return
        else:
            area_y = self.offset_y + 134
            area_h = self.altura_modal - 178
            card_w = (self.largura_modal - 72) // 2
            card_h = 98
            gap_x = 16
            gap_y = 10
            for idx, chip_id in enumerate(CHIPS_FIRMWARE.keys()):
                col = idx % 2
                row = idx // 2
                cx = self.offset_x + 28 + col * (card_w + gap_x)
                cy = area_y + row * (card_h + gap_y) - int(self.scroll_y)
                if cy + card_h < area_y or cy > area_y + area_h:
                    continue
                rect_card = pygame.Rect(cx, cy, card_w, card_h)
                if rect_card.collidepoint(mx, my):
                    self.tentar_alternar_firmware(chip_id)
                    return

    def _obter_overlay(self, w: int, h: int) -> pygame.Surface:
        chave = (w, h)
        if chave not in self._overlay_cache:
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            s.fill((6, 9, 16, 210))
            self._overlay_cache[chave] = s
        return self._overlay_cache[chave]

    def draw(self, screen: pygame.Surface):
        if not self.ativo or screen is None:
            return

        try:
            pygame.mouse.set_visible(True)
        except Exception:
            pass

        sw, sh = screen.get_size()
        self.offset_x = (sw - self.largura_modal) // 2
        self.offset_y = (sh - self.altura_modal) // 2
        ox, oy = self.offset_x, self.offset_y

        screen.blit(self._obter_overlay(sw, sh), (0, 0))

        modal_rect = pygame.Rect(ox, oy, self.largura_modal, self.altura_modal)
        pygame.draw.rect(screen, COR_BG_MODAL, modal_rect, border_radius=8)
        pygame.draw.rect(screen, COR_CIANO, modal_rect, width=2, border_radius=8)

        # Título
        f_titulo = self._fonte("sans", 20, True)
        f_sub = self._fonte("mono", 11, True)
        titulo_surf = f_titulo.render("SISTEMA DE CONQUISTAS & FIRMWARE", True, BRANCO)
        screen.blit(titulo_surf, (ox + 28, oy + 18))

        # Abas e Fechar
        aba0, aba1, btn_fechar = self._obter_rects_topo()
        for idx, (rect, label) in enumerate([(aba0, "CONQUISTAS"), (aba1, "CHIPS DE FIRMWARE")]):
            ativa = self.aba_atual == idx
            cor_bg = COR_ELEVADO if ativa else COR_CARD
            cor_bd = COR_CIANO if ativa else COR_BORDA
            pygame.draw.rect(screen, cor_bg, rect, border_radius=5)
            pygame.draw.rect(screen, cor_bd, rect, width=2 if ativa else 1, border_radius=5)
            s_lbl = self._fonte("sans", 13, True).render(label, True, BRANCO if ativa else COR_TEXTO_SUAVE)
            screen.blit(s_lbl, s_lbl.get_rect(center=rect.center))

        pygame.draw.rect(screen, (60, 20, 28), btn_fechar, border_radius=5)
        pygame.draw.rect(screen, COR_CARMESIM, btn_fechar, width=1, border_radius=5)
        s_close = self._fonte("sans", 13, True).render("FECHAR [ESC]", True, BRANCO)
        screen.blit(s_close, s_close.get_rect(center=btn_fechar.center))

        if self.aba_atual == 0:
            self._desenhar_aba_conquistas(screen, ox, oy)
        else:
            self._desenhar_aba_firmware(screen, ox, oy)

        # Rodapé / Feedback
        rodape_y = oy + self.altura_modal - 32
        if self._timer_feedback > 0.0 and self._mensagem_feedback:
            s_fb = f_sub.render(self._mensagem_feedback, True, COR_OURO)
            screen.blit(s_fb, (ox + 28, rodape_y))
        else:
            dica = "TAB: Trocar Aba  |  Mouse/Scroll: Navegar  |  ESC: Fechar"
            screen.blit(self._fonte("mono", 10, False).render(dica, True, COR_TEXTO_SUAVE), (ox + 28, rodape_y))

    def _desenhar_aba_conquistas(self, screen: pygame.Surface, ox: int, oy: int):
        f_btn = self._fonte("sans", 11, True)
        f_nome = self._fonte("sans", 15, True)
        f_desc = self._fonte("sans", 12, False)
        f_mono = self._fonte("mono", 11, True)

        for nome_f, r_f in self._obter_rects_filtros():
            ativo = self.filtro_atual == nome_f
            pygame.draw.rect(screen, COR_ELEVADO if ativo else COR_CARD, r_f, border_radius=4)
            pygame.draw.rect(screen, COR_CIANO if ativo else COR_BORDA, r_f, width=1, border_radius=4)
            s = f_btn.render(nome_f, True, BRANCO if ativo else COR_TEXTO_SUAVE)
            screen.blit(s, s.get_rect(center=r_f.center))

        fixadas = getattr(self.sistema_conquistas, "fixadas", []) if self.sistema_conquistas else []
        s_pins = f_mono.render(f"FIXADAS NA HUD: {len(fixadas)}/3", True, COR_OURO)
        screen.blit(s_pins, (ox + self.largura_modal - 205, oy + 104))

        area_rect = pygame.Rect(ox + 24, oy + 132, self.largura_modal - 48, self.altura_modal - 174)
        prev_clip = screen.get_clip()
        screen.set_clip(area_rect)

        itens = self._obter_itens_conquistas()
        card_h = 92
        gap = 8
        max_scroll = max(0, len(itens) * (card_h + gap) - area_rect.height)
        self.scroll_y = clamp(self.scroll_y, 0.0, float(max_scroll))

        f_recomp = self._fonte("sans", 11, True)
        hover_pos = getattr(self, "_hover_pos", (-1, -1))

        for idx, (tipo, cid, cdef) in enumerate(itens):
            cy = area_rect.y + idx * (card_h + gap) - int(self.scroll_y)
            if cy + card_h < area_rect.y or cy > area_rect.bottom:
                continue

            card_rect = pygame.Rect(ox + 28, cy, self.largura_modal - 56, card_h)
            fixada = cid in fixadas
            hovered = card_rect.collidepoint(*hover_pos)

            if tipo == "continua":
                estado = self.sistema_conquistas.continuas.get(cid, {"valor": 0, "milestones_concluidos": []}) if self.sistema_conquistas else {"valor": 0, "milestones_concluidos": []}
                atual = int(estado.get("valor", 0))
                concluidos = estado.get("milestones_concluidos", [])
                concluida = len(concluidos) >= len(cdef.milestones)
                prox_meta = cdef.milestones[-1].meta
                prox_ms = cdef.milestones[-1]
                for ms_idx, ms in enumerate(cdef.milestones):
                    if ms_idx not in concluidos:
                        prox_meta = ms.meta
                        prox_ms = ms
                        break
                progresso = clamp(atual / max(1, prox_meta), 0.0, 1.0)
                status_txt = f"M{len(concluidos)}/{len(cdef.milestones)}  ({atual}/{prox_meta})"
                recomp_txt = (
                    "Todos os marcos concluídos!"
                    if concluida
                    else f"Desbloqueia: {formatar_recompensas_conquista(prox_ms.recompensas)}"
                )
            else:
                concluida = cid in getattr(self.sistema_conquistas, "unicas_concluidas", set())
                progresso = 1.0 if concluida else 0.0
                status_txt = "CONCLUÍDA" if concluida else "PENDENTE"
                recomp_txt = f"Desbloqueia: {formatar_recompensas_conquista(cdef.recompensas)}"

            cor_bd = COR_VERDE if concluida else (COR_OURO if fixada else (COR_CIANO if hovered else COR_BORDA))
            pygame.draw.rect(screen, COR_ELEVADO if hovered else COR_CARD, card_rect, border_radius=5)
            pygame.draw.rect(screen, cor_bd, card_rect, width=1, border_radius=5)

            screen.blit(f_nome.render(cdef.nome, True, COR_OURO if concluida else BRANCO), (card_rect.x + 12, cy + 7))
            screen.blit(f_desc.render(cdef.descricao[:78], True, COR_TEXTO_SUAVE), (card_rect.x + 12, cy + 28))
            screen.blit(f_recomp.render(recomp_txt[:82], True, COR_VERDE if concluida else COR_CIANO), (card_rect.x + 12, cy + 47))
            screen.blit(f_mono.render(status_txt, True, COR_VERDE if concluida else COR_CIANO), (card_rect.x + 12, cy + 68))

            # Barra de progresso
            bar_x = card_rect.x + 195
            bar_y = cy + 72
            bar_w = card_rect.width - 330
            pygame.draw.rect(screen, COR_ELEVADO, (bar_x, bar_y, bar_w, 8), border_radius=3)
            if progresso > 0.0:
                pygame.draw.rect(screen, COR_VERDE if concluida else COR_CIANO, (bar_x, bar_y, int(bar_w * progresso), 8), border_radius=3)

            btn_pin = pygame.Rect(ox + self.largura_modal - 134, cy + 28, 96, 28)
            btn_hover = btn_pin.collidepoint(*hover_pos)
            pygame.draw.rect(screen, (60, 48, 16) if fixada else (COR_BORDA if btn_hover else COR_ELEVADO), btn_pin, border_radius=4)
            pygame.draw.rect(screen, COR_OURO if fixada else (COR_CIANO if btn_hover else COR_BORDA), btn_pin, width=1, border_radius=4)
            s_pin = f_btn.render("FIXADA" if fixada else "FIXAR", True, COR_OURO if fixada else BRANCO)
            screen.blit(s_pin, s_pin.get_rect(center=btn_pin.center))

        screen.set_clip(prev_clip)

    def _desenhar_aba_firmware(self, screen: pygame.Surface, ox: int, oy: int):
        f_mono = self._fonte("mono", 12, True)
        f_nome = self._fonte("sans", 13, True)
        f_desc = self._fonte("sans", 12, False)
        f_badge = self._fonte("sans", 11, True)

        equipados = list(getattr(self.sistema_conquistas, "modificadores_equipados", [])) if self.sistema_conquistas else []
        slots_max = int(getattr(self.sistema_conquistas, "slots_firmware_max", 1)) if self.sistema_conquistas else 1

        s_slots = f_mono.render(f"SLOTS DE FIRMWARE: {len(equipados)}/{slots_max}", True, COR_ROXO)
        screen.blit(s_slots, (ox + 28, oy + 100))

        if self.em_jogo:
            badge_ro = pygame.Rect(ox + self.largura_modal - 270, oy + 96, 242, 24)
            pygame.draw.rect(screen, (68, 22, 22), badge_ro, border_radius=4)
            pygame.draw.rect(screen, COR_CARMESIM, badge_ro, width=1, border_radius=4)
            s_ro = f_badge.render("SOMENTE LEITURA EM PARTIDA", True, COR_CARMESIM)
            screen.blit(s_ro, s_ro.get_rect(center=badge_ro.center))

        area_rect = pygame.Rect(ox + 24, oy + 132, self.largura_modal - 48, self.altura_modal - 174)
        prev_clip = screen.get_clip()
        screen.set_clip(area_rect)

        card_w = (self.largura_modal - 72) // 2
        card_h = 98
        gap_x = 16
        gap_y = 10
        total_rows = (len(CHIPS_FIRMWARE) + 1) // 2
        max_scroll = max(0, total_rows * (card_h + gap_y) - area_rect.height)
        self.scroll_y = clamp(self.scroll_y, 0.0, float(max_scroll))

        for idx, (chip_id, chip) in enumerate(CHIPS_FIRMWARE.items()):
            col = idx % 2
            row = idx // 2
            cx = ox + 28 + col * (card_w + gap_x)
            cy = area_rect.y + row * (card_h + gap_y) - int(self.scroll_y)
            if cy + card_h < area_rect.y or cy > area_rect.bottom:
                continue

            desbloqueado = (
                self.sistema_conquistas.possui_recompensa("modificador_run", chip_id)
                if self.sistema_conquistas
                else False
            )
            equipado = chip_id in equipados

            card_rect = pygame.Rect(cx, cy, card_w, card_h)
            cor_bg = (26, 20, 44) if equipado else COR_CARD
            cor_bd = COR_ROXO if equipado else (COR_CIANO if desbloqueado else COR_BORDA)
            pygame.draw.rect(screen, cor_bg, card_rect, border_radius=5)
            pygame.draw.rect(screen, cor_bd, card_rect, width=2 if equipado else 1, border_radius=5)

            cor_nome = COR_OURO if equipado else (BRANCO if desbloqueado else COR_TEXTO_SUAVE)
            screen.blit(f_nome.render(chip.nome, True, cor_nome), (cx + 10, cy + 8))

            status = "EQUIPADO" if equipado else ("LIBERADO" if desbloqueado else "BLOQUEADO")
            cor_st = COR_ROXO if equipado else (COR_VERDE if desbloqueado else COR_CARMESIM)
            s_st = f_badge.render(status, True, cor_st)
            screen.blit(s_st, (cx + card_w - s_st.get_width() - 10, cy + 10))

            # Quebra simples da descrição em 2 linhas
            desc = chip.descricao
            linha1 = desc[:48]
            linha2 = desc[48:96]
            screen.blit(f_desc.render(linha1, True, COR_TEXTO_SUAVE), (cx + 10, cy + 34))
            if linha2:
                screen.blit(f_desc.render(linha2, True, COR_TEXTO_SUAVE), (cx + 10, cy + 52))
            screen.blit(f_mono.render(f"[{chip.categoria}]", True, chip.icone_cor), (cx + 10, cy + 74))

        screen.set_clip(prev_clip)
