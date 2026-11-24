"""
Pipeline de Renderização, Câmera/VSync/Iluminação, HUD In-World e Overlays — Protocolo: Batata
Extraído de GameplayScene como mixin behavior-preserving (GameplayRenderMixin).
"""

import math
import random
import pygame
from src.armas.pistola import Pistola
from src.armas.melee import Melee
from src.utils.constantes import (
    LARGURA_TELA, ALTURA_TELA, DASH_COOLDOWN,
    BRANCO, CINZA_FUNDO, VERMELHO_HP, VERDE_CURA,
    AMARELO_XP, AZUL_CIANO, DOURADO, LARANJA_ALERTA, ROXO_ACENTO,
)
from src.utils.math_utils import clamp
from src.sistemas.config_dados import CONFIGURACOES_GAMEPLAY
from src.sistemas.efeitos_combate import obter_bandas_vsync_y


class GameplayRenderMixin:
    """
    Mixin responsável pelo pipeline de renderização, HUD in-world e overlays
    de pausa, vitória e game over da GameplayScene.
    """

    @staticmethod
    def _obter_viewport_nativo(screen) -> tuple[int, int, int, int, float]:
        """Calcula (ox, oy, vw, vh, scale) a partir do tamanho real da superfície de destino."""
        sw, sh = screen.get_size() if hasattr(screen, "get_size") else (LARGURA_TELA, ALTURA_TELA)
        if sw < 1 or sh < 1:
            return 0, 0, LARGURA_TELA, ALTURA_TELA, 1.0
        scale = min(sw / float(LARGURA_TELA), sh / float(ALTURA_TELA))
        vw = max(1, int(round(LARGURA_TELA * scale)))
        vh = max(1, int(round(ALTURA_TELA * scale)))
        ox = (sw - vw) // 2
        oy = (sh - vh) // 2
        return ox, oy, vw, vh, scale

    def _obter_fonte(self, chave: str, scale: float) -> pygame.font.Font:
        """Retorna fonte em DPI nativo cacheada por (chave, px_size) sem alocação por frame."""
        if abs(scale - 1.0) < 1e-4:
            return self._fontes[chave]
        nome, tam_logico, bold = self._fontes_spec[chave]
        px = max(8, int(round(tam_logico * scale)))
        cache_k = (chave, px)
        if cache_k not in self._fontes_nativas_cache:
            try:
                self._fontes_nativas_cache[cache_k] = pygame.font.SysFont(nome, px, bold=bold)
            except Exception:
                self._fontes_nativas_cache[cache_k] = pygame.font.Font(None, px)
        return self._fontes_nativas_cache[cache_k]

    def _escalar_surf_nativa(self, surf: pygame.Surface | None, w: int, h: int) -> pygame.Surface | None:
        if surf is None:
            return None
        w = max(1, int(w))
        h = max(1, int(h))
        if surf.get_width() == w and surf.get_height() == h:
            return surf
        cache = getattr(self.janela, "sprite_scale_cache", None) if hasattr(self, "janela") and self.janela else None
        if cache is not None:
            return cache.obter(surf, w, h)
        return pygame.transform.scale(surf, (w, h))

    def draw(self):
        screen = self.janela.screen
        self._carregar_assets_cenario()
        ox, oy, vw, vh, scale = self._obter_viewport_nativo(screen)
        scr_w, scr_h = screen.get_size() if hasattr(screen, "get_size") else (LARGURA_TELA, ALTURA_TELA)

        # Propagação da flag graficos_qualidade == "baixa"
        baixa_qualidade = (str(self.config_sistema.obter_valor("graficos_qualidade")).lower() == "baixa") if hasattr(self, "config_sistema") and self.config_sistema else False
        if hasattr(self, "janela") and self.janela:
            self.janela.low_graphics = baixa_qualidade
        if hasattr(self, "sistema_particulas") and self.sistema_particulas:
            self.sistema_particulas.low_graphics = baixa_qualidade

        # =========================================================================
        # CAMADA 1: ESPAÇO DO MUNDO (TRANSFORMADO PELA CÂMERA, COM SUPORTE A DPI NATIVO E ZOOM 75%)
        # =========================================================================
        val_zoom = str(self.config_sistema.obter_valor("zoom")) if hasattr(self, "config_sistema") and self.config_sistema else "100%"
        cam_orig_x = self.camera.x
        cam_orig_y = self.camera.y
        cam_orig_w = getattr(self.camera, "largura", LARGURA_TELA)
        cam_orig_h = getattr(self.camera, "altura", ALTURA_TELA)
        jan_orig_w = getattr(self.janela, "largura", LARGURA_TELA)
        jan_orig_h = getattr(self.janela, "altura", ALTURA_TELA)

        precisa_canvas_mundo = (val_zoom == "75%") or (vw != LARGURA_TELA) or (vh != ALTURA_TELA) or (ox != 0) or (oy != 0)
        if val_zoom == "75%":
            view_w, view_h, cam_base_x, cam_base_y = self._obter_viewport_zoom75()
            if self._zoom75_surf is None or self._zoom75_surf.get_size() != (view_w, view_h):
                self._zoom75_surf = pygame.Surface((view_w, view_h))
            world_surf = self._zoom75_surf
            self.camera.x = cam_base_x
            self.camera.y = cam_base_y
            self.camera.largura = view_w
            self.camera.altura = view_h
            self.janela.screen = world_surf
            self.janela.largura = view_w
            self.janela.altura = view_h
        elif precisa_canvas_mundo:
            view_w, view_h = LARGURA_TELA, ALTURA_TELA
            if self._world_canvas_surf is None or self._world_canvas_surf.get_size() != (LARGURA_TELA, ALTURA_TELA):
                self._world_canvas_surf = pygame.Surface((LARGURA_TELA, ALTURA_TELA))
            world_surf = self._world_canvas_surf
            self.janela.screen = world_surf
        else:
            view_w, view_h = LARGURA_TELA, ALTURA_TELA
            world_surf = screen

        # Screen Shake: aplica jitter temporário à câmera durante renderização do mundo
        if self.shake_timer > 0.0 and self.shake_intensidade > 0.0:
            self.camera.x += random.uniform(-self.shake_intensidade, self.shake_intensidade)
            self.camera.y += random.uniform(-self.shake_intensidade, self.shake_intensidade)

        # Fundo da arena
        world_surf.fill(CINZA_FUNDO)

        # Renderização do piso ladrilhado visível (ou grade fallback / baixa qualidade)
        tile_tam = 32
        inicio_tx = max(0, int(self.camera.x // tile_tam))
        fim_tx = min(int(self.largura_arena // tile_tam), int((self.camera.x + view_w) // tile_tam) + 1)
        inicio_ty = max(0, int(self.camera.y // tile_tam))
        fim_ty = min(int(self.altura_arena // tile_tam), int((self.camera.y + view_h) // tile_tam) + 1)

        if self._tile_piso is not None and not baixa_qualidade:
            for tx in range(inicio_tx, fim_tx):
                for ty in range(inicio_ty, fim_ty):
                    wx = tx * tile_tam
                    wy = ty * tile_tam
                    world_surf.blit(self._tile_piso, (self.camera.transform_x(wx), self.camera.transform_y(wy)))
        else:
            # Grade fallback caso textura não esteja em RAM ou graficos_qualidade == "baixa"
            for tx in range(inicio_tx, fim_tx):
                for ty in range(inicio_ty, fim_ty):
                    wx = tx * tile_tam
                    wy = ty * tile_tam
                    dx = self.camera.transform_x(wx)
                    dy = self.camera.transform_y(wy)
                    pygame.draw.rect(world_surf, (28, 32, 42), (dx, dy, tile_tam, tile_tam), 1)

        # Linhas delimitadoras da arena
        borda_x0 = self.camera.transform_x(0)
        borda_y0 = self.camera.transform_y(0)
        pygame.draw.rect(world_surf, AZUL_CIANO, (borda_x0, borda_y0, self.largura_arena, self.altura_arena), width=3)

        # Decais persistentes no piso (cápsulas de latão e marcas de queimadura) abaixo das entidades
        if hasattr(self.sistema_particulas, "desenhar_chao"):
            self.sistema_particulas.desenhar_chao(world_surf, cam_x=self.camera.x, cam_y=self.camera.y, scale=1.0)

        # Posição virtual do cursor do mouse em coordenadas de mundo (respeitando keybinds e zoom)
        val_keybinds_draw = str(self.config_sistema.obter_valor("keybinds")).lower() if hasattr(self, "config_sistema") and self.config_sistema else "padrao"
        cx_mundo = self.jogador.x + self.jogador.largura / 2.0
        cy_mundo = self.jogador.y + self.jogador.altura / 2.0
        if val_keybinds_draw == "uma_mao":
            dir_mov_d = getattr(self.jogador, "dir_movimento", (0.0, -1.0))
            dmx, dmy = float(dir_mov_d[0]), float(dir_mov_d[1])
            if dmx == 0.0 and dmy == 0.0:
                dmx, dmy = 0.0, -1.0
            mouse_mundo_x = cx_mundo + dmx * 160.0
            mouse_mundo_y = cy_mundo + dmy * 160.0
        else:
            try:
                mx, my = self.mouse.get_position()
                if val_keybinds_draw == "pesadelo":
                    my = ALTURA_TELA - my
            except Exception:
                mx, my = (LARGURA_TELA / 2.0, ALTURA_TELA / 2.0)
            # Restaura temporariamente camera.x/y base para _obter_mouse_mundo
            _cur_cx, _cur_cy = self.camera.x, self.camera.y
            self.camera.x, self.camera.y = cam_orig_x, cam_orig_y
            mouse_mundo_x, mouse_mundo_y = self._obter_mouse_mundo(mx, my)
            self.camera.x, self.camera.y = _cur_cx, _cur_cy

        # Indicador de alcance Melee quando empunhada (Antes do golpe - Cone direcional)
        arma_ativa = self.jogador.obter_arma_ativa()
        if (isinstance(arma_ativa, Melee) or getattr(arma_ativa, "slot", None) == 1) and self.jogador.vivo:
            raio = getattr(arma_ativa, "alcance", 84.0)
            arco = getattr(arma_ativa, "arco_graus", 45.0)
            cx_tela = int(self.camera.transform_x(cx_mundo))
            cy_tela = int(self.camera.transform_y(cy_mundo))

            ang_centro = math.atan2(mouse_mundo_y - cy_mundo, mouse_mundo_x - cx_mundo)
            meio_arco = math.radians(arco / 2.0)

            surf_dim = int(raio * 2 + 16)
            if surf_dim not in self._melee_surf_cache:
                self._melee_surf_cache[surf_dim] = pygame.Surface((surf_dim, surf_dim), pygame.SRCALPHA)
            surf_alcance = self._melee_surf_cache[surf_dim]
            surf_alcance.fill((0, 0, 0, 0))
            s_cx = surf_dim // 2
            s_cy = surf_dim // 2

            pontos_setor = [(s_cx, s_cy)]
            num_seg = 12
            for step in range(num_seg + 1):
                ang = ang_centro - meio_arco + (2.0 * meio_arco * step / num_seg)
                px = s_cx + math.cos(ang) * raio
                py = s_cy + math.sin(ang) * raio
                pontos_setor.append((px, py))

            pygame.draw.polygon(surf_alcance, (0, 220, 255, 25), pontos_setor)
            pygame.draw.polygon(surf_alcance, (0, 220, 255, 80), pontos_setor, width=1)
            world_surf.blit(surf_alcance, (cx_tela - s_cx, cy_tela - s_cy))

        # Efeitos visuais de golpe Melee (Depois / Durante o golpe - Slash Fan)
        for ef in self.efeitos_melee:
            raio_base = ef["alcance"]
            arco = ef.get("arco_graus", 45.0)
            ang_centro = ef.get("angulo", 0.0)
            cx_tela = int(self.camera.transform_x(ef["x"]))
            cy_tela = int(self.camera.transform_y(ef["y"]))

            progresso = 1.0 - max(0.0, ef["tempo"] / ef["tempo_total"])
            alpha = int(240 * (1.0 - progresso))
            raio_atual = raio_base * (0.4 + 0.6 * progresso)
            meio_arco = math.radians(arco / 2.0)

            surf_dim = int(raio_base * 2 + 16)
            if surf_dim not in self._melee_surf_cache:
                self._melee_surf_cache[surf_dim] = pygame.Surface((surf_dim, surf_dim), pygame.SRCALPHA)
            surf_golpe = self._melee_surf_cache[surf_dim]
            surf_golpe.fill((0, 0, 0, 0))
            s_cx = surf_dim // 2
            s_cy = surf_dim // 2

            pontos_fan = [(s_cx, s_cy)]
            num_seg = 12
            for step in range(num_seg + 1):
                ang = ang_centro - meio_arco + (2.0 * meio_arco * step / num_seg)
                px = s_cx + math.cos(ang) * raio_atual
                py = s_cy + math.sin(ang) * raio_atual
                pontos_fan.append((px, py))

            pygame.draw.polygon(surf_golpe, (255, 215, 0, alpha // 3), pontos_fan)
            pygame.draw.polygon(surf_golpe, (255, 255, 255, alpha), pontos_fan, width=2)
            world_surf.blit(surf_golpe, (cx_tela - s_cx, cy_tela - s_cy))

        # Zonas de Efeito no Piso (Poças de Gelo, Zonas de Estase, Zonas de Fogo, Trilhas de Plasma, Aura de Cura e Lasers)
        for pg in self.pocas_gelo:
            px_t = int(self.camera.transform_x(pg["x"]))
            py_t = int(self.camera.transform_y(pg["y"]))
            r_pg = int(pg["raio"])
            pygame.draw.circle(world_surf, (45, 110, 165), (px_t, py_t), r_pg)
            pygame.draw.circle(world_surf, (130, 220, 255), (px_t, py_t), r_pg, width=2)

        for ze in self.zonas_estase:
            zx_t = int(self.camera.transform_x(ze["x"]))
            zy_t = int(self.camera.transform_y(ze["y"]))
            r_ze = int(ze["raio"])
            pygame.draw.circle(world_surf, (20, 75, 120), (zx_t, zy_t), r_ze, width=2)
            pygame.draw.circle(world_surf, (56, 189, 248), (zx_t, zy_t), max(4, int(r_ze * 0.65)), width=1)

        for zf in self.zonas_fogo:
            fx_t = int(self.camera.transform_x(zf["x"]))
            fy_t = int(self.camera.transform_y(zf["y"]))
            r_zf = int(zf["raio"])
            pygame.draw.circle(world_surf, (95, 32, 12), (fx_t, fy_t), r_zf)
            pygame.draw.circle(world_surf, (255, 115, 25), (fx_t, fy_t), r_zf, width=2)

        # Estados visuais de EfeitoDashRastro (zonas de fogo, vórtices de vácuo, subprocesso pendente e feixe de stun)
        efeito_dash = (
            self.efeitos_combate._mapa_efeitos.get("dash_rastro")
            if getattr(self, "efeitos_combate", None) is not None and hasattr(self.efeitos_combate, "_mapa_efeitos")
            else None
        )
        if efeito_dash is not None:
            for zf_d in getattr(efeito_dash, "zonas_fogo", []):
                fx_d = int(self.camera.transform_x(zf_d["x"]))
                fy_d = int(self.camera.transform_y(zf_d["y"]))
                r_zfd = max(8, int(zf_d.get("raio", 48.0)))
                pygame.draw.circle(world_surf, (115, 36, 12), (fx_d, fy_d), r_zfd)
                pygame.draw.circle(world_surf, (255, 130, 30), (fx_d, fy_d), r_zfd, width=2)
                pygame.draw.circle(world_surf, (255, 210, 80), (fx_d, fy_d), max(4, r_zfd // 2), width=1)

            for vv in getattr(efeito_dash, "vortices_vacuo", []):
                vx_d = int(self.camera.transform_x(vv["x"]))
                vy_d = int(self.camera.transform_y(vv["y"]))
                r_vv = max(12, int(vv.get("raio", 180.0)))
                fase_vv = float(vv.get("tempo", 0.0)) * 8.0
                pygame.draw.circle(world_surf, (34, 211, 238), (vx_d, vy_d), r_vv, width=1)
                pygame.draw.circle(world_surf, (125, 240, 255), (vx_d, vy_d), max(8, int(r_vv * 0.55)), width=2)
                for seg_v in range(3):
                    ang_v0 = fase_vv + seg_v * (2.0 * math.pi / 3.0)
                    r_esp = max(10, int(r_vv * (0.35 + 0.2 * seg_v)))
                    rect_esp = pygame.Rect(vx_d - r_esp, vy_d - r_esp, r_esp * 2, r_esp * 2)
                    pygame.draw.arc(world_surf, (56, 189, 248), rect_esp, ang_v0, ang_v0 + 1.4, width=2)

            for sp in getattr(efeito_dash, "subprocessos_pendentes", []):
                ox_s = int(self.camera.transform_x(sp["origem"][0]))
                oy_s = int(self.camera.transform_y(sp["origem"][1]))
                dx_s = int(self.camera.transform_x(sp["destino"][0]))
                dy_s = int(self.camera.transform_y(sp["destino"][1]))
                frac_sp = max(0.0, min(1.0, float(sp.get("tempo", 0.0)) / 0.75))
                pygame.draw.line(world_surf, (56, 189, 248), (ox_s, oy_s), (dx_s, dy_s), width=1)
                pygame.draw.circle(world_surf, (125, 240, 255), (ox_s, oy_s), 12, width=1)
                rect_sp = pygame.Rect(ox_s - 16, oy_s - 16, 32, 32)
                pygame.draw.arc(world_surf, (250, 204, 21), rect_sp, 0.0, max(0.1, 2.0 * math.pi * frac_sp), width=2)

            for fx_sp in getattr(efeito_dash, "feixes_subprocesso", []):
                ox_f = int(self.camera.transform_x(fx_sp["origem"][0]))
                oy_f = int(self.camera.transform_y(fx_sp["origem"][1]))
                dx_f = int(self.camera.transform_x(fx_sp["destino"][0]))
                dy_f = int(self.camera.transform_y(fx_sp["destino"][1]))
                dur_f = max(0.01, float(fx_sp.get("duracao", 0.35)))
                ratio_f = max(0.0, min(1.0, float(fx_sp.get("tempo", 0.0)) / dur_f))
                w_fx = max(3, int(round(10 * ratio_f)))
                pygame.draw.line(world_surf, (56, 189, 248), (ox_f, oy_f), (dx_f, dy_f), width=w_fx)
                pygame.draw.line(world_surf, (255, 255, 255), (ox_f, oy_f), (dx_f, dy_f), width=max(1, w_fx // 2))
                pygame.draw.circle(world_surf, (125, 240, 255), (dx_f, dy_f), max(4, int(round(12 * ratio_f))), width=2)

        for tp in self.trilhas_plasma:
            tx1 = int(self.camera.transform_x(tp["x1"]))
            ty1 = int(self.camera.transform_y(tp["y1"]))
            tx2 = int(self.camera.transform_x(tp["x2"]))
            ty2 = int(self.camera.transform_y(tp["y2"]))
            ratio = max(0.0, min(1.0, tp["tempo"] / max(0.01, tp["tempo_max"])))
            w_outer = max(2, int(round(7 * ratio)))
            w_core = max(1, int(round(3 * ratio)))
            pygame.draw.line(world_surf, (34, 211, 238), (tx1, ty1), (tx2, ty2), width=w_outer)
            pygame.draw.line(world_surf, (255, 255, 255), (tx1, ty1), (tx2, ty2), width=w_core)
            pygame.draw.circle(world_surf, (34, 211, 238), (tx1, ty1), max(3, int(8 * ratio)))

        # Aura circular sob a Batata ao receber pulso de cura (Opção C)
        if self.aura_cura_timer > 0.0 and self.jogador.vivo:
            cx_ac = int(self.camera.transform_x(cx_mundo))
            cy_ac = int(self.camera.transform_y(self.jogador.y + self.jogador.altura - 3))
            r_ac = int(16 + (0.65 - self.aura_cura_timer) * 18.0)
            pygame.draw.ellipse(world_surf, (74, 222, 128), (cx_ac - r_ac, cy_ac - r_ac // 2, r_ac * 2, max(6, r_ac)), width=2)

        # Feixe verde do Drone de Cura e Mira Laser pontilhada do Drone de Combate (Opção C)
        for dr_v in getattr(self.jogador, "drones", []):
            if not getattr(dr_v, "ativo", False):
                continue
            dcx_t = int(self.camera.transform_x(dr_v.x + dr_v.largura / 2.0))
            dcy_t = int(self.camera.transform_y(dr_v.y + dr_v.altura / 2.0))
            if getattr(dr_v, "feixe_cura_timer", 0.0) > 0.0:
                jcx_t = int(self.camera.transform_x(cx_mundo))
                jcy_t = int(self.camera.transform_y(cy_mundo))
                pygame.draw.line(world_surf, (74, 222, 128), (dcx_t, dcy_t), (jcx_t, jcy_t), width=3)
                pygame.draw.line(world_surf, (220, 255, 230), (dcx_t, dcy_t), (jcx_t, jcy_t), width=1)
            alv_d = getattr(dr_v, "alvo_atual", None)
            if alv_d is not None and getattr(alv_d, "vivo", False):
                acx_t = int(self.camera.transform_x(alv_d.x + getattr(alv_d, "largura", 28) / 2.0))
                acy_t = int(self.camera.transform_y(alv_d.y + getattr(alv_d, "altura", 28) / 2.0))
                for s_pt in range(0, 7, 2):
                    f1 = s_pt / 7.0
                    f2 = (s_pt + 1) / 7.0
                    p1 = (int(dcx_t + (acx_t - dcx_t) * f1), int(dcy_t + (acy_t - dcy_t) * f1))
                    p2 = (int(dcx_t + (acx_t - dcx_t) * f2), int(dcy_t + (acy_t - dcy_t) * f2))
                    pygame.draw.line(world_surf, (244, 63, 94), p1, p2, width=1)

        # Drops de itens e gemas de XP no chão da arena (pausando pisca durante Boss)
        is_boss_lutando_draw = (self.chefe_final is not None and self.chefe_final.vivo)
        self.sistema_drops.desenhar(self.janela, self.camera, pausar_despawn=is_boss_lutando_draw)

        # Inimigos
        for inimigo in self.inimigos:
            inimigo.desenhar(self.janela, self.camera)

        # Jogador
        self.jogador.desenhar(self.janela, self.camera)

        # Brilho ciano pulsante no cano quando Slot 2 (Pistola) está com 4º tiro sobrecarregado pronto
        if self.jogador.vivo and getattr(self.jogador, "slot_ativo", 0) == 2 and isinstance(arma_ativa, Pistola) and getattr(arma_ativa, "esta_carregada", False):
            ang_cano = float(getattr(self.jogador, "aim_angle", math.atan2(mouse_mundo_y - cy_mundo, mouse_mundo_x - cx_mundo)))
            bx_t = int(round(self.camera.transform_x(cx_mundo + math.cos(ang_cano) * 20.0)))
            by_t = int(round(self.camera.transform_y(cy_mundo + math.sin(ang_cano) * 20.0)))
            pulso_cano = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.015) if pygame.display.get_init() else 1.0
            r_glow = int(round(5 + pulso_cano * 4))
            pygame.draw.circle(world_surf, (56, 189, 248), (bx_t, by_t), r_glow, width=2)
            pygame.draw.circle(world_surf, (220, 250, 255), (bx_t, by_t), max(2, r_glow // 2))

        # Projéteis (tiros do jogador primeiro; projéteis inimigos sempre acima de inimigos, Boss e jogador)
        for proj in self.projeteis:
            if getattr(proj, "dono", "jogador") != "inimigo":
                proj.desenhar(self.janela, self.camera)
        for proj in self.projeteis:
            if getattr(proj, "dono", "jogador") == "inimigo":
                proj.desenhar(self.janela, self.camera)

        # Partículas de combate (faíscas, ondas de choque, bursts e detritos)
        self.sistema_particulas.desenhar(self.janela, self.camera)

        # Hologramas (sombra_espelho / clone_agro)
        for holo in getattr(self, "hologramas", []):
            if hasattr(holo, "desenhar"):
                holo.desenhar(world_surf, self.camera)

        # Arma contínua: Rifle de Arco (feixe elétrico travado em feixe_destino)
        arma_cont = self.jogador.obter_arma_ativa() if (self.jogador.vivo and hasattr(self.jogador, "obter_arma_ativa")) else None
        if arma_cont is not None and getattr(arma_cont, "eh_continua", False):
            eh_arco = "arco" in str(getattr(arma_cont, "id_arma", "")).lower() or "rifle_arco" in str(type(arma_cont).__name__).lower()
            if eh_arco and getattr(arma_cont, "feixe_ativo", False):
                orig_w = getattr(
                    arma_cont,
                    "feixe_origem",
                    (self.jogador.x + self.jogador.largura / 2.0, self.jogador.y + self.jogador.altura / 2.0),
                )
                ox_c = self.camera.transform_x(orig_w[0])
                oy_c = self.camera.transform_y(orig_w[1])
                dest_w = getattr(arma_cont, "feixe_destino", None)
                if dest_w is not None:
                    dx_c = self.camera.transform_x(dest_w[0])
                    dy_c = self.camera.transform_y(dest_w[1])
                else:
                    ang_c = float(getattr(self.jogador, "aim_angle", 0.0))
                    alc = float(getattr(arma_cont, "alcance", 380.0))
                    dx_c = ox_c + math.cos(ang_c) * alc
                    dy_c = oy_c + math.sin(ang_c) * alc
                vx_f = dx_c - ox_c
                vy_f = dy_c - oy_c
                comp_f = math.hypot(vx_f, vy_f)
                nx_f = -vy_f / comp_f if comp_f > 1e-6 else 0.0
                ny_f = vx_f / comp_f if comp_f > 1e-6 else 0.0
                pts = [(int(ox_c), int(oy_c))]
                tick_arco = int(self.tempo_sobrevivencia * 90)
                num_segs = 6
                for seg in range(1, num_segs):
                    frac = seg / float(num_segs)
                    jitter = (((seg * 13 + tick_arco) % 13) - 6) * 1.3
                    px_b = ox_c + vx_f * frac + nx_f * jitter
                    py_b = oy_c + vy_f * frac + ny_f * jitter
                    pts.append((int(px_b), int(py_b)))
                pts.append((int(dx_c), int(dy_c)))
                pygame.draw.lines(world_surf, (56, 189, 248), False, pts, width=5)
                pygame.draw.lines(world_surf, (224, 248, 255), False, pts, width=2)
                # Faíscas de impacto no destino travado
                ix_d, iy_d = int(dx_c), int(dy_c)
                pygame.draw.circle(world_surf, (56, 189, 248), (ix_d, iy_d), 6, width=2)
                pygame.draw.circle(world_surf, (224, 248, 255), (ix_d, iy_d), 3)
                for sp_i in range(4):
                    sp_ang = (tick_arco * 0.25) + sp_i * (math.pi * 0.5)
                    sp_r = 8 + ((tick_arco + sp_i * 3) % 5)
                    pygame.draw.line(
                        world_surf,
                        (224, 248, 255),
                        (ix_d, iy_d),
                        (int(ix_d + math.cos(sp_ang) * sp_r), int(iy_d + math.sin(sp_ang) * sp_r)),
                        width=1,
                    )

        # Hooks visuais B+ (latencia_ping fantasma, sandbox_isolada, firewall_estatico, etc.)
        mods = self.config_sistema.obter_modificadores() if hasattr(self, "config_sistema") and self.config_sistema else None
        if getattr(self, "efeitos_combate", None) is not None:
            try:
                from src.sistemas.efeitos_combate import ContextoCombate
                ctx_render = ContextoCombate(
                    cena=self,
                    jogador=self.jogador,
                    inimigos=self.inimigos,
                    projeteis=self.projeteis,
                    drops=getattr(self.sistema_drops, "drops", []),
                    particulas=self.sistema_particulas,
                    mods=mods,
                    sistema_combo=getattr(self, "sistema_combo", None),
                    sistema_conquistas=getattr(self, "sistema_conquistas", None),
                    hologramas=getattr(self, "hologramas", None),
                    tempo_sobrevivencia=getattr(self, "tempo_sobrevivencia", 0.0),
                )
                self.efeitos_combate.disparar_ao_pos_render_mundo(ctx_render, world_surf, camera=self.camera)
            except Exception:
                pass

        # Passe técnico Modo Wireframe (grade + contornos geométricos + nó vulnerável)
        if getattr(mods, "modo_wireframe", False):
            for gx in range(0, LARGURA_TELA, 64):
                pygame.draw.line(world_surf, (20, 58, 72), (gx, 0), (gx, ALTURA_TELA), width=1)
            for gy in range(0, ALTURA_TELA, 64):
                pygame.draw.line(world_surf, (20, 58, 72), (0, gy), (LARGURA_TELA, gy), width=1)
            for inim in self.inimigos:
                if not getattr(inim, "vivo", True):
                    continue
                ix = int(self.camera.transform_x(inim.x))
                iy = int(self.camera.transform_y(inim.y))
                iw = max(8, int(getattr(inim, "largura", 24)))
                ih = max(8, int(getattr(inim, "altura", 24)))
                pygame.draw.rect(world_surf, (34, 211, 238), (ix, iy, iw, ih), width=1)
                pygame.draw.circle(world_surf, (251, 191, 36), (ix + iw // 2, iy + ih // 2), max(3, min(iw, ih) // 4), width=1)

        # Barra de HP in-world flutuando abaixo do jogador
        hud_visivel = (self.gerenciador_config.obter_valor("hud") != "desligado")
        if hud_visivel:
            self._desenhar_hp_in_world()

        # Restaura a câmera e a janela antes dos efeitos de pós-processamento de tela e HUD
        if val_zoom == "75%":
            self.janela.largura = jan_orig_w
            self.janela.altura = jan_orig_h
            self.camera.largura = cam_orig_w
            self.camera.altura = cam_orig_h
        self.janela.screen = screen
        self.camera.x = cam_orig_x
        self.camera.y = cam_orig_y

        # Fonte de mundo para projeção na viewport nativa (ox, oy, vw, vh)
        fonte_mundo = world_surf

        # Viewport Zoom (Config 9: zoom in 125%, 150%; 75% já renderizado com FOV expandido)
        if val_zoom in ("125%", "150%"):
            z = 1.25 if val_zoom == "125%" else 1.50
            crop_w = int(LARGURA_TELA / z)
            crop_h = int(ALTURA_TELA / z)
            pj_cx = int(self.camera.transform_x(self.jogador.x + self.jogador.largura / 2.0))
            pj_cy = int(self.camera.transform_y(self.jogador.y + self.jogador.altura / 2.0))
            crop_x = clamp(pj_cx - crop_w // 2, 0, LARGURA_TELA - crop_w)
            crop_y = clamp(pj_cy - crop_h // 2, 0, ALTURA_TELA - crop_h)
            crop_key = (crop_w, crop_h)
            if crop_key not in self._zoom_crop_cache:
                self._zoom_crop_cache[crop_key] = pygame.Surface(crop_key)
            crop_surf = self._zoom_crop_cache[crop_key]
            crop_surf.blit(fonte_mundo, (0, 0), area=pygame.Rect(crop_x, crop_y, crop_w, crop_h))
            fonte_mundo = crop_surf

        # Resolução / Pixelation do Mundo (Config 3: 75%, 50%, 25% — escala offscreen + blit nearest-neighbor; HUD nítido por cima)
        val_res = str(self.config_sistema.obter_valor("resolucao")) if hasattr(self, "config_sistema") and self.config_sistema else "100%"
        mapa_fator_res = {"100%": 1.0, "75%": 0.75, "50%": 0.50, "25%": 0.25}
        fator_res = mapa_fator_res.get(val_res, float(getattr(self.janela, "escala_resolucao_mundo", 1.0)))
        if fator_res < 0.999:
            small_w = max(10, int(round(LARGURA_TELA * fator_res)))
            small_h = max(10, int(round(ALTURA_TELA * fator_res)))
            res_key = (small_w, small_h)
            if res_key not in self._res_surf_cache:
                self._res_surf_cache[res_key] = pygame.Surface(res_key)
            small_surf = self._res_surf_cache[res_key]
            pygame.transform.scale(fonte_mundo, res_key, small_surf)
            fonte_mundo = small_surf

        # Projeta o passe do mundo na viewport nativa (ox, oy, vw, vh) com nearest-neighbor limpo
        if fonte_mundo is not screen:
            if ox == 0 and oy == 0 and vw == scr_w and vh == scr_h:
                pygame.transform.scale(fonte_mundo, (vw, vh), screen)
            else:
                if self._world_scaled_surf is None or self._world_scaled_surf.get_size() != (vw, vh):
                    self._world_scaled_surf = pygame.Surface((vw, vh))
                pygame.transform.scale(fonte_mundo, (vw, vh), self._world_scaled_surf)
                screen.blit(self._world_scaled_surf, (ox, oy))

        # Sincronização Vertical (Config 4: vsync == "desligado" -> 2 bandas horizontais simétricas alinhadas à física)
        mods = self.config_sistema.obter_modificadores() if hasattr(self, "config_sistema") and self.config_sistema else None
        if getattr(mods, "vsync_tear_refraction", False) and not self.boss_cutscene_ativa:
            y1_b, y2_b = obter_bandas_vsync_y(getattr(self, "vsync_tear_y", 0.0), ALTURA_TELA)
            strip_h = max(6, int(round(14 * scale)))
            if self._vsync_strip_surf is None or self._vsync_strip_surf.get_size() != (vw, strip_h):
                self._vsync_strip_surf = pygame.Surface((vw, strip_h))
            lw1 = max(1, int(round(2 * scale)))
            bandas = [
                (oy + int(round(y1_b * scale)), max(6, int(round(18 * scale)))),
                (oy + int(round(y2_b * scale)), -max(6, int(round(16 * scale)))),
            ]
            for ty, shift_signed in bandas:
                band_y = max(oy, ty - strip_h // 2)
                band_h = min(strip_h, (oy + vh) - band_y)
                abs_shift = abs(shift_signed)
                if band_h > 0 and vw > abs_shift:
                    self._vsync_strip_surf.blit(screen, (0, 0), area=pygame.Rect(ox, band_y, vw, band_h))
                    if shift_signed >= 0:
                        screen.blit(self._vsync_strip_surf, (ox + abs_shift, band_y), area=pygame.Rect(0, 0, vw - abs_shift, band_h))
                    else:
                        screen.blit(self._vsync_strip_surf, (ox, band_y), area=pygame.Rect(abs_shift, 0, vw - abs_shift, band_h))
                pygame.draw.line(screen, (56, 189, 248), (ox, max(oy, ty)), (ox + vw, max(oy, ty)), width=lw1)

        # Iluminação Dinâmica / Fog of War (Config 18) - renderizado sobre (ox, oy, vw, vh) antes do HUD
        val_ilum = self.config_sistema.obter_valor("iluminacao") if hasattr(self, "config_sistema") and self.config_sistema else "desligado"
        if val_ilum in (True, "Ligado", "ligado", "1"):
            if self._fog_surf is None or self._fog_surf.get_size() != (vw, vh):
                self._fog_surf = pygame.Surface((vw, vh), pygame.SRCALPHA)
            fog = self._fog_surf
            fog.fill((8, 10, 15, 235))
            if val_zoom == "75%":
                fov_w, fov_h, cam75_x, cam75_y = self._obter_viewport_zoom75()
                pj_cx = int(round((self.jogador.x + self.jogador.largura / 2.0 - cam75_x) * (vw / float(fov_w))))
                pj_cy = int(round((self.jogador.y + self.jogador.altura / 2.0 - cam75_y) * (vh / float(fov_h))))
            elif val_zoom in ("125%", "150%"):
                z = 1.25 if val_zoom == "125%" else 1.50
                crop_w = int(LARGURA_TELA / z)
                crop_h = int(ALTURA_TELA / z)
                raw_cx = int(self.camera.transform_x(self.jogador.x + self.jogador.largura / 2.0))
                raw_cy = int(self.camera.transform_y(self.jogador.y + self.jogador.altura / 2.0))
                crop_x = clamp(raw_cx - crop_w // 2, 0, LARGURA_TELA - crop_w)
                crop_y = clamp(raw_cy - crop_h // 2, 0, ALTURA_TELA - crop_h)
                pj_cx = int(round((raw_cx - crop_x) * z * scale))
                pj_cy = int(round((raw_cy - crop_y) * z * scale))
            else:
                pj_cx = int(round(self.camera.transform_x(self.jogador.x + self.jogador.largura / 2.0) * scale))
                pj_cy = int(round(self.camera.transform_y(self.jogador.y + self.jogador.altura / 2.0) * scale))
            pygame.draw.circle(fog, (0, 0, 0, 80), (pj_cx, pj_cy), max(10, int(round(195 * scale))))
            pygame.draw.circle(fog, (0, 0, 0, 0), (pj_cx, pj_cy), max(8, int(round(170 * scale))))
            screen.blit(fog, (ox, oy))

        # =========================================================================
        # CAMADA 2: ESPAÇO DA TELA (SCREEN-SPACE HUD EM DPI NATIVO)
        # =========================================================================
        self._desenhar_hud_tela(hud_visivel=hud_visivel)

        # Cores Invertidas (Config 17) - renderizado antes dos modais, sobre toda a viewport nativa
        val_cores = self.config_sistema.obter_valor("cores_invertidas") if hasattr(self, "config_sistema") and self.config_sistema else "desligado"
        if val_cores in (True, "Ligado", "ligado", "1"):
            if self._inv_surf is None or self._inv_surf.get_size() != (vw, vh):
                self._inv_surf = pygame.Surface((vw, vh))
            inv_surf = self._inv_surf
            inv_surf.fill((255, 255, 255))
            inv_surf.blit(screen, (0, 0), area=pygame.Rect(ox, oy, vw, vh), special_flags=pygame.BLEND_SUB)
            screen.blit(inv_surf, (ox, oy))

        # Overlays modais de Level Up, Overclock, Menu de Configurações, Debug, Vitória, Game Over e Pausa
        if self.modal_overclock.ativo or self.modal_overclock.tempo_transicao_saida > 0.0:
            self.modal_overclock.draw(screen)
        elif self.modal_level_up.ativo or getattr(self.modal_level_up, "tempo_transicao_saida", 0.0) > 0.0:
            self.modal_level_up.draw(screen)
        elif self.menu_configs.ativo:
            self.menu_configs.draw(screen)
        elif hasattr(self, "menu_conquistas") and self.menu_conquistas is not None and self.menu_conquistas.ativo:
            self.menu_conquistas.draw(screen)
        elif hasattr(self, "menu_debug") and self.menu_debug.ativo:
            self.menu_debug.draw(screen)
        elif self.vitoria:
            self._desenhar_overlay_vitoria()
        elif self.game_over:
            self._desenhar_overlay_game_over()
        elif self.pausado:
            self._desenhar_overlay_pausa()

        # Overlay da Cutscene do Chefe Final (Queda de Energia c/ Holofote -> Equalizadores FFT)
        if self.boss_cutscene_ativa and self.overlay_cutscene_alpha > 0:
            if self._overlay_surf is None or self._overlay_surf.get_size() != (scr_w, scr_h):
                self._overlay_surf = pygame.Surface((scr_w, scr_h), pygame.SRCALPHA)
            r, g, b = self.overlay_cutscene_cor
            self._overlay_surf.fill((r, g, b, int(self.overlay_cutscene_alpha)))
            screen.blit(self._overlay_surf, (0, 0))

        # Equalizador FFT ao vivo da Geladeira Tsunami (bordas superior e inferior da viewport nativa)
        mostrar_fft_boss = (
            (self.boss_cutscene_ativa and self.boss_cutscene_fase == "musica_in")
            or (self.chefe_final is not None and getattr(self.chefe_final, "vivo", False) and not self.boss_cutscene_ativa)
        )
        if mostrar_fft_boss and hasattr(self, "analisador_fft_boss") and self.analisador_fft_boss is not None:
            pos_ms = -1
            try:
                if pygame.mixer.get_init():
                    pos_ms = pygame.mixer.music.get_pos()
            except Exception:
                pos_ms = -1
            if pos_ms is None or pos_ms < 0:
                pos_ms = (self.boss_cutscene_timer if self.boss_cutscene_ativa else self.tempo_sobrevivencia) * 1000.0
            bandas = self.analisador_fft_boss.obter_bandas(
                float(pos_ms),
                dt=float(getattr(self, "_ultimo_dt_draw", 1.0 / 60.0)),
                num_bandas=28
            )
            num_barras = len(bandas)
            if num_barras > 0:
                passo_x = vw / float(num_barras)
                gap_b = max(2, int(round(4 * scale)))
                larg_b = max(4, int(passo_x) - gap_b)
                raio_b = max(1, int(round(2 * scale)))
                for idx_b, amp in enumerate(bandas):
                    bx = ox + int(idx_b * passo_x) + gap_b // 2
                    alt_b = max(4, int(round((6.0 + clamp(float(amp), 0.0, 1.0) * 40.0) * scale)))
                    cor_eq = ROXO_ACENTO if idx_b % 2 == 0 else (56, 189, 248)
                    pygame.draw.rect(screen, cor_eq, (bx, oy, larg_b, alt_b), border_radius=raio_b)
                    pygame.draw.rect(screen, cor_eq, (bx, oy + vh - alt_b, larg_b, alt_b), border_radius=raio_b)

        # Banners estilo Steam de conquistas/desbloqueios (sempre visíveis sobre gameplay e HUD)
        if (
            getattr(self, "banners_desbloqueio", None)
            and hasattr(self, "hud")
            and self.hud is not None
            and hasattr(self.hud, "desenhar_banners_desbloqueio")
        ):
            self.hud.desenhar_banners_desbloqueio(screen, self.banners_desbloqueio)

        # Motion Blur (Config 6: motion_blur == "ligado") aplicado sobre TODA a tela (mundo, inimigos, projéteis, HUD e modais)
        val_blur = str(self.config_sistema.obter_valor("motion_blur")).lower() if hasattr(self, "config_sistema") and self.config_sistema else "desligado"
        if val_blur in ("ligado", "true", "1") and not self.boss_cutscene_ativa:
            if self._motion_blur_surf is None or self._motion_blur_surf.get_size() != (scr_w, scr_h):
                self._motion_blur_surf = pygame.Surface((scr_w, scr_h))
                self._motion_blur_surf.set_alpha(155)
                self._motion_blur_surf.blit(screen, (0, 0))
            else:
                screen.blit(self._motion_blur_surf, (0, 0))
                self._motion_blur_surf.blit(screen, (0, 0))
        elif self._motion_blur_surf is not None:
            self._motion_blur_surf = None

    def _desenhar_hp_in_world(self):
        """Desenha a barra de HP em Pixel Art Limpo (Opção A) abaixo da batata, com extensão azul da Barreira de Sobrevida."""
        if not self.jogador.vivo:
            return

        centro_x = self.jogador.x + float(self.jogador.largura) / 2.0
        base_y = self.jogador.y + float(self.jogador.altura) + 5.0

        bar_w = 34
        bar_h = 6
        bar_x = int(self.camera.transform_x(centro_x) - bar_w // 2)
        bar_y = int(self.camera.transform_y(base_y))

        # Moldura pixelada escura (#0f172a)
        pygame.draw.rect(self.janela.screen, (15, 23, 42), (bar_x, bar_y, bar_w, bar_h))

        # Preenchimento verde nítido
        proporcao = clamp(self.jogador.hp / float(max(1, self.jogador.hp_max)), 0.0, 1.0)
        fill_w = int((bar_w - 2) * proporcao)
        if fill_w > 0:
            pygame.draw.rect(self.janela.screen, VERDE_CURA, (bar_x + 1, bar_y + 1, fill_w, bar_h - 2))

        # Barreira de Sobrevida (Drone de Cura quando vida cheia) em azul ciano
        escudo_val = int(getattr(self.jogador, "escudo_sobrevida", 0))
        if escudo_val > 0:
            esc_w = max(2, int((bar_w - 2) * clamp(escudo_val / 25.0, 0.0, 1.0)))
            pygame.draw.rect(self.janela.screen, (56, 189, 248), (bar_x + 1, bar_y - 2, esc_w, 2))

        next_y = bar_y + bar_h + 1
        sub_h = 4

        # Barra de carregamento do Dash (apenas quando desbloqueado)
        if bool(getattr(self.jogador, "dash_desbloqueado", False)):
            cd_rest = max(0.0, float(getattr(self.jogador, "dash_cooldown_restante", 0.0)))
            ativo_t = max(0.0, float(getattr(self.jogador, "dash_ativo_timer", 0.0)))
            pronto_dash = (cd_rest <= 0.0 and ativo_t <= 0.0)
            prog_dash = 1.0 if pronto_dash else clamp(1.0 - (cd_rest / max(0.01, float(DASH_COOLDOWN))), 0.0, 1.0)
            cor_dash = (34, 211, 238) if pronto_dash else (30, 110, 140)
            pygame.draw.rect(self.janela.screen, (15, 23, 42), (bar_x, next_y, bar_w, sub_h))
            fill_dash = int((bar_w - 2) * prog_dash)
            if fill_dash > 0:
                pygame.draw.rect(self.janela.screen, cor_dash, (bar_x + 1, next_y + 1, fill_dash, sub_h - 2))
            next_y += sub_h + 1

        # Barra de munição da arma atual
        arma_ativa = self.jogador.obter_arma_ativa() if hasattr(self.jogador, "obter_arma_ativa") else None
        if arma_ativa is not None:
            municao_inf = bool(getattr(arma_ativa, "municao_infinita", True))
            municao_max = int(getattr(arma_ativa, "municao_max", 0))
            municao_atual = int(getattr(arma_ativa, "municao_atual", 0))
            if not municao_inf and municao_max > 0:
                prog_mun = clamp(municao_atual / float(municao_max), 0.0, 1.0)
                cor_mun = DOURADO if prog_mun > 0.25 else VERMELHO_HP
            else:
                prog_mun = 1.0
                cor_mun = DOURADO
            pygame.draw.rect(self.janela.screen, (15, 23, 42), (bar_x, next_y, bar_w, sub_h))
            fill_mun = int((bar_w - 2) * prog_mun)
            if fill_mun > 0:
                pygame.draw.rect(self.janela.screen, cor_mun, (bar_x + 1, next_y + 1, fill_mun, sub_h - 2))
            if getattr(arma_ativa, "usa_calor", False) and hasattr(self, "hud") and self.hud is not None and hasattr(self.hud, "desenhar_barra_calor_in_world"):
                self.hud.desenhar_barra_calor_in_world(self.janela.screen, bar_x, next_y + sub_h + 2, bar_w, arma_ativa)

    def _resolver_icone_arma(self, arma, chave_padrao: str | None = None):
        """Resolve o sprite do ícone priorizando `arma.icone_asset` antes do fallback legado por nome."""
        if arma is not None:
            icone_chave = getattr(arma, "icone_asset", None)
            if icone_chave:
                img = self._obter_sprite_icone(icone_chave)
                if img is not None:
                    return img
            nome_arma = getattr(arma, "nome", "")
            if "Minigun" in nome_arma:
                return self._obter_sprite_icone("arma_minigun")
            if "Escopeta" in nome_arma or "Shotgun" in nome_arma:
                return self._obter_sprite_icone("arma_shotgun")
            if "Arco" in nome_arma:
                return self._obter_sprite_icone("arma_rifle_arco")
            if "Chamas" in nome_arma:
                return self._obter_sprite_icone("arma_lanca_chamas")
            if "Bastão" in nome_arma or "Choque" in nome_arma:
                return self._obter_sprite_icone("arma_bastao_choque")
            if "SMG" in nome_arma:
                return self._obter_sprite_icone("arma_smg")
            if "Rifle" in nome_arma:
                return self._obter_sprite_icone("arma_rifle")
            if "Railgun" in nome_arma:
                return self._obter_sprite_icone("arma_railgun")
            if "Foguetes" in nome_arma:
                return self._obter_sprite_icone("arma_foguetes")
            if "Granadas" in nome_arma:
                return self._obter_sprite_icone("arma_granadas")
        if chave_padrao:
            return self._obter_sprite_icone(chave_padrao)
        return None

    def _desenhar_hud_tela(self, hud_visivel: bool = True):
        """Renderiza o HUD fixo na tela em DPI nativo: inventário, vitais, telemetria e botão de configurações."""
        screen = self.janela.screen
        ox, oy, vw, vh, s = self._obter_viewport_nativo(screen)
        px_x = lambda lx: ox + int(round(lx * s))
        px_y = lambda ly: oy + int(round(ly * s))
        px_s = lambda v: max(1, int(round(v * s)))

        if hud_visivel:
            # Paleta Cyber-Office local
            cor_card = (17, 24, 39)
            cor_elevado = (30, 41, 59)
            cor_borda_sutil = (51, 65, 85)
            cor_ciano = (34, 211, 238)
            cor_roxo = (168, 85, 247)
            cor_ouro = (251, 191, 36)
            cor_carmesim = (239, 68, 68)
            cor_muted = (148, 163, 184)

            # 0. Painel compacto de Vitais no topo esquerdo (HP numérico + Overshield ciano + prontidão do Dash)
            if hasattr(self, "hud") and self.hud is not None and hasattr(self.hud, "desenhar_painel_vitais"):
                self.hud.desenhar_painel_vitais(screen, self.jogador, visivel=hud_visivel)
            if hasattr(self, "hud") and self.hud is not None:
                if hasattr(self, "sistema_conquistas") and self.sistema_conquistas is not None and hasattr(self.hud, "desenhar_pins_conquistas"):
                    self.hud.desenhar_pins_conquistas(screen, self.sistema_conquistas.obter_resumo_fixadas(), visivel=hud_visivel)
                if hasattr(self, "sistema_combo") and self.sistema_combo is not None and hasattr(self.hud, "desenhar_indicador_combo"):
                    self.hud.desenhar_indicador_combo(screen, self.sistema_combo, visivel=hud_visivel)
                if hasattr(self, "efeitos_combate") and self.efeitos_combate is not None and hasattr(self.hud, "desenhar_barra_ram_gc"):
                    efeito_gc = self.efeitos_combate.obter_efeito("garbage_collector")
                    if efeito_gc is not None:
                        self.hud.desenhar_barra_ram_gc(screen, efeito_gc, visivel=hud_visivel)

            # 1. Slots de inventário ([1]-[4] + [3B]) no Top-Left (16, 14, 54x54 lógico)
            slot_tam_l = 54
            slot_y_l = 14
            slot_tam = px_s(slot_tam_l)
            icone_dim = px_s(34)
            raio_slot = max(2, int(round(4 * s)))
            slot_ativo = getattr(self.jogador, "slot_ativo", 2)

            fonte_slots = self._obter_fonte("slots", s)
            fonte_municao = self._obter_fonte("municao", s)
            ticks_hud = pygame.time.get_ticks() if pygame.display.get_init() else 0

            for i in range(4):
                sx = px_x(16 + i * (slot_tam_l + 6))
                sy = px_y(slot_y_l)
                slot_num = i + 1
                is_ativo = (slot_num == slot_ativo)

                # Verifica estado de sobrecarga da Pistola no Slot 2
                arma_slot2_ref = self.jogador.armas[1] if (i == 1 and hasattr(self.jogador, "armas") and len(self.jogador.armas) > 1) else None
                pistola_carregada = bool(isinstance(arma_slot2_ref, Pistola) and getattr(arma_slot2_ref, "esta_carregada", False))

                bg_cor = cor_elevado if is_ativo else cor_card
                if pistola_carregada:
                    borda_cor = cor_ciano if (ticks_hud // 180) % 2 == 0 else (165, 243, 252)
                    borda_largura = max(2, int(round(2 * s)))
                elif is_ativo:
                    borda_cor = cor_ouro
                    borda_largura = max(2, int(round(2 * s)))
                else:
                    borda_cor = cor_borda_sutil
                    borda_largura = max(1, int(round(1 * s)))

                if is_ativo or pistola_carregada:
                    glow_cor = cor_ciano if pistola_carregada else cor_ouro
                    g_off = max(1, int(round(s)))
                    pygame.draw.rect(screen, glow_cor, (sx - g_off, sy - g_off, slot_tam + g_off * 2, slot_tam + g_off * 2), width=g_off, border_radius=raio_slot + 1)

                pygame.draw.rect(screen, bg_cor, (sx, sy, slot_tam, slot_tam), border_radius=raio_slot)
                pygame.draw.rect(screen, borda_cor, (sx, sy, slot_tam, slot_tam), width=borda_largura, border_radius=raio_slot)

                # Badge de atalho monospace [1]..[4] no canto superior esquerdo
                num_surf = fonte_slots.render(f"[{slot_num}]", True, cor_ciano if pistola_carregada else (cor_ouro if is_ativo else cor_muted))
                screen.blit(num_surf, (sx + max(2, int(round(3 * s))), sy + max(1, int(round(2 * s)))))

                # Ícone do slot
                icone_img = None
                texto_badge = None
                cor_badge = BRANCO

                if i == 0:
                    arma_slot1 = getattr(self.jogador, "arma_melee", None)
                    icone_img = self._resolver_icone_arma(arma_slot1, "arma_melee")
                elif i == 1:
                    arma_slot2 = arma_slot2_ref
                    if arma_slot2 is not None:
                        icone_img = self._resolver_icone_arma(arma_slot2, "arma_pistola")
                        if not getattr(arma_slot2, "municao_infinita", False) and hasattr(arma_slot2, "municao_atual"):
                            mun2 = getattr(arma_slot2, "municao_atual", 0)
                            texto_badge = str(mun2)
                            cor_badge = cor_ouro if mun2 > 5 else cor_carmesim
                    else:
                        icone_img = self._obter_sprite_icone("arma_pistola")
                elif i == 2:
                    if self.jogador.arma_especial:
                        icone_img = self._resolver_icone_arma(self.jogador.arma_especial)

                        mun = getattr(self.jogador.arma_especial, "municao_atual", 0)
                        texto_badge = str(mun)
                        cor_badge = cor_ouro if mun > 5 else cor_carmesim
                elif i == 3:
                    drones_ativos = getattr(self.jogador, "drones", [])
                    if drones_ativos:
                        primeiro_drone = drones_ativos[0]
                        nome_d = getattr(primeiro_drone, "nome", "")
                        if "Cura" in nome_d:
                            icone_img = self._obter_sprite_icone("drone_cura")
                        elif "Combate" in nome_d:
                            icone_img = self._obter_sprite_icone("drone_combate")
                        else:
                            icone_img = self._obter_sprite_icone("drone_suporte")

                        menor_tempo = min(int(getattr(d, "tempo_restante", 0)) for d in drones_ativos)
                        if len(drones_ativos) > 1:
                            texto_badge = f"x{len(drones_ativos)} {menor_tempo}s"
                        else:
                            texto_badge = f"{menor_tempo}s"
                        cor_badge = cor_ciano

                if icone_img is not None:
                    icone_nativo = self._escalar_surf_nativa(icone_img, icone_dim, icone_dim)
                    screen.blit(icone_nativo, (sx + (slot_tam - icone_dim) // 2, sy + (slot_tam - icone_dim) // 2))

                # Medidor 3-pip ciano de sobrecarga da Pistola no Slot 2 (pips_carga 0..3)
                if i == 1 and isinstance(arma_slot2_ref, Pistola):
                    pips = int(getattr(arma_slot2_ref, "pips_carga", 0))
                    pip_w = px_s(11)
                    pip_h = px_s(4)
                    pip_gap = max(2, int(round(3 * s)))
                    total_pips_w = 3 * pip_w + 2 * pip_gap
                    pip_x0 = sx + (slot_tam - total_pips_w) // 2
                    pip_y = sy + slot_tam - max(4, int(round(6 * s)))
                    for p_idx in range(3):
                        px_p = pip_x0 + p_idx * (pip_w + pip_gap)
                        ativo_pip = (p_idx < pips)
                        cor_pip = (165, 243, 252) if (pistola_carregada and (ticks_hud // 140) % 2 == 0) else (cor_ciano if ativo_pip else (30, 41, 59))
                        pygame.draw.rect(screen, cor_pip, (px_p, pip_y, pip_w, pip_h), border_radius=1)
                        if not ativo_pip:
                            pygame.draw.rect(screen, cor_borda_sutil, (px_p, pip_y, pip_w, pip_h), width=1, border_radius=1)

                if texto_badge is not None:
                    badge_surf = fonte_municao.render(texto_badge, True, cor_badge)
                    badge_rect = badge_surf.get_rect(right=sx + slot_tam - max(2, int(round(2 * s))), bottom=sy + slot_tam - max(1, int(round(s))))
                    sombra_b = fonte_municao.render(texto_badge, True, (0, 0, 0))
                    sh_o = max(1, int(round(s)))
                    screen.blit(sombra_b, (badge_rect.x + sh_o, badge_rect.y + sh_o))
                    screen.blit(badge_surf, badge_rect)

            # Slot 3B secundário (desbloqueado com BIOS Modding)
            if getattr(self.jogador, "bios_modding", False):
                sx3b = px_x(16 + 2 * (slot_tam_l + 6))
                sy3b = px_y(slot_y_l + slot_tam_l + 4)
                pygame.draw.rect(screen, (28, 16, 44), (sx3b, sy3b, slot_tam, slot_tam), border_radius=raio_slot)
                pygame.draw.rect(screen, cor_roxo, (sx3b, sy3b, slot_tam, slot_tam), width=max(1, int(round(s))), border_radius=raio_slot)

                num_surf = fonte_slots.render("[3B]", True, (216, 180, 254))
                screen.blit(num_surf, (sx3b + max(2, int(round(3 * s))), sy3b + max(1, int(round(2 * s)))))

                if getattr(self.jogador, "arma_especial_secundaria", None) is not None:
                    icone_img = self._resolver_icone_arma(self.jogador.arma_especial_secundaria)

                    if icone_img:
                        icone_nativo = self._escalar_surf_nativa(icone_img, icone_dim, icone_dim)
                        screen.blit(icone_nativo, (sx3b + (slot_tam - icone_dim) // 2, sy3b + (slot_tam - icone_dim) // 2))

                    mun = getattr(self.jogador.arma_especial_secundaria, "municao_atual", 0)
                    texto_badge = str(mun)
                    cor_badge = cor_ouro if mun > 5 else cor_carmesim
                    badge_surf = fonte_municao.render(texto_badge, True, cor_badge)
                    badge_rect = badge_surf.get_rect(right=sx3b + slot_tam - max(2, int(round(2 * s))), bottom=sy3b + slot_tam - max(1, int(round(s))))
                    sombra_b = fonte_municao.render(texto_badge, True, (0, 0, 0))
                    sh_o = max(1, int(round(s)))
                    screen.blit(sombra_b, (badge_rect.x + sh_o, badge_rect.y + sh_o))
                    screen.blit(badge_surf, badge_rect)

            # 2. Faixa compacta de telemetria no topo central (y=6..26 lógico, 340x20 px)
            minutos = int(self.tempo_sobrevivencia // 60)
            segundos = int(self.tempo_sobrevivencia % 60)
            texto_tempo = f"{minutos:02d}:{segundos:02d}"
            texto_abates = f"ABATES {self.abates}"
            texto_pontos = f"PTS {self.pontos}"

            centro_tela_x = ox + vw // 2
            pill_w = px_s(340)
            pill_h = px_s(20)
            pill_x = centro_tela_x - pill_w // 2
            pill_y = px_y(6)
            raio_pill = max(2, int(round(4 * s)))
            if self._hud_stats_pill_surf is None or self._hud_stats_pill_surf.get_size() != (pill_w, pill_h):
                self._hud_stats_pill_surf = pygame.Surface((pill_w, pill_h), pygame.SRCALPHA)
                pygame.draw.rect(self._hud_stats_pill_surf, (11, 14, 23, 220), (0, 0, pill_w, pill_h), border_radius=raio_pill)
            screen.blit(self._hud_stats_pill_surf, (pill_x, pill_y))
            pulso_intro = float(getattr(self, "pulso_assault_intro_timer", 0.0))
            cor_borda_pill = cor_ouro if (pulso_intro > 0.0 and int(pulso_intro * 10) % 2 == 0) else cor_borda_sutil
            pygame.draw.rect(screen, cor_borda_pill, (pill_x, pill_y, pill_w, pill_h), width=max(1, int(round(s))), border_radius=raio_pill)

            cy_pill = pill_y + pill_h // 2
            tempo_surf = self._obter_fonte("tempo", s).render(texto_tempo, True, BRANCO)
            abates_surf = self._obter_fonte("abates", s).render(texto_abates, True, cor_ouro)
            pontos_surf = self._obter_fonte("abates", s).render(texto_pontos, True, (226, 232, 240))

            screen.blit(tempo_surf, tempo_surf.get_rect(left=pill_x + max(6, int(round(14 * s))), centery=cy_pill))
            screen.blit(abates_surf, abates_surf.get_rect(centerx=centro_tela_x + int(round(4 * s)), centery=cy_pill))
            screen.blit(pontos_surf, pontos_surf.get_rect(right=pill_x + pill_w - max(6, int(round(12 * s))), centery=cy_pill))

            # 3. Barra compacta de Progresso de XP (Top-Center: y=30..41 lógico, 420x11 px)
            if hasattr(self, "hud") and self.hud is not None:
                self.hud.desenhar_barra_xp(screen, self.jogador.sistema_xp)

            # 4. Barra compacta de Mini-Boss / Chefe Final (Top-Center: y=45..63 lógico, 480x18 px com timer 60s inline)
            if hasattr(self, "hud") and self.hud is not None:
                boss_ativo = self.chefe_final if (self.chefe_final is not None and self.chefe_final.vivo) else next((e for e in self.inimigos if getattr(e, "is_elite", False) and e.vivo), None)
                if boss_ativo is not None:
                    self.hud.desenhar_barra_boss(screen, boss_ativo, visivel=hud_visivel)

            # 5. Indicadores visuais de Buffs Ativos na Tela (preservados da v1, escalados em DPI nativo)
            self._desenhar_buffs_ativos(screen)

            # 6. FPS (Top-Right) em ciano monospace sob hud_visivel
            fps_val = int(self.janela.get_fps())
            fonte_fps = self._obter_fonte("fps", s)
            fps_surf = fonte_fps.render(f"FPS {fps_val}", True, cor_ciano)
            fps_rect = fps_surf.get_rect(right=px_x(LARGURA_TELA - 56), centery=px_y(32))
            screen.blit(fps_surf, fps_rect)

        # 4.5. Banner de Grace Period do Chefe Final
        self._desenhar_banner_grace_period(screen)

        # 5. Toasts de Coleta Flutuantes
        self._desenhar_toasts(screen)

        # 6. Botão de Configurações e engrenagem [C] - sempre visível mesmo com hud="desligado"
        gear_x = px_x(LARGURA_TELA - 48)
        gear_y = px_y(16)
        gear_dim = px_s(32)
        if self._btn_gear_img is not None:
            gear_img = self._escalar_surf_nativa(self._btn_gear_img, gear_dim, gear_dim)
            screen.blit(gear_img, (gear_x, gear_y))
        else:
            pygame.draw.rect(screen, (45, 55, 75), (gear_x, gear_y, gear_dim, gear_dim), border_radius=max(2, int(round(4 * s))))
            fonte_fps = self._obter_fonte("fps", s)
            gear_surf = fonte_fps.render("[C]", True, DOURADO)
            gear_rect = gear_surf.get_rect(centerx=gear_x + gear_dim // 2, centery=gear_y + gear_dim // 2)
            screen.blit(gear_surf, gear_rect)

        # 7. Mira (Crosshair) projetada na viewport nativa
        em_combate_ativo = (
            not self.pausado and not self.game_over and not self.vitoria
            and not (self.boss_cutscene_ativa and self.boss_cutscene_fase != "whiteout")
            and not self.menu_configs.ativo and not self.modal_level_up.ativo and not self.modal_overclock.ativo
            and not (hasattr(self, "menu_conquistas") and self.menu_conquistas is not None and self.menu_conquistas.ativo)
            and not (hasattr(self, "menu_debug") and self.menu_debug.ativo)
        )
        if pygame.display.get_init():
            pygame.mouse.set_visible(not (em_combate_ativo and self.jogador.vivo))
        if em_combate_ativo and self.jogador.vivo:
            val_kb = str(self.config_sistema.obter_valor("keybinds")).lower() if hasattr(self, "config_sistema") and self.config_sistema else "padrao"
            if val_kb == "uma_mao":
                dir_m = getattr(self.jogador, "dir_movimento", (0.0, -1.0))
                dmx, dmy = float(dir_m[0]), float(dir_m[1])
                if dmx == 0.0 and dmy == 0.0:
                    dmx, dmy = 0.0, -1.0
                cx_t = self.camera.transform_x(self.jogador.x + self.jogador.largura / 2.0)
                cy_t = self.camera.transform_y(self.jogador.y + self.jogador.altura / 2.0)
                mira_lx = clamp(cx_t + dmx * 72.0, 0.0, float(LARGURA_TELA))
                mira_ly = clamp(cy_t + dmy * 72.0, 0.0, float(ALTURA_TELA))
            else:
                try:
                    mx_c, my_c = self.mouse.get_position()
                    if val_kb == "pesadelo":
                        my_c = ALTURA_TELA - my_c
                except Exception:
                    mx_c, my_c = LARGURA_TELA // 2, ALTURA_TELA // 2
                mira_lx = clamp(float(mx_c), 0.0, float(LARGURA_TELA))
                mira_ly = clamp(float(my_c), 0.0, float(ALTURA_TELA))

            mira_tx = px_x(mira_lx)
            mira_ty = px_y(mira_ly)
            if self._mira_crosshair_img is not None:
                cw = px_s(self._mira_crosshair_img.get_width())
                ch = px_s(self._mira_crosshair_img.get_height())
                mira_img = self._escalar_surf_nativa(self._mira_crosshair_img, cw, ch)
                screen.blit(mira_img, (mira_tx - cw // 2, mira_ty - ch // 2))
            else:
                pygame.draw.circle(screen, AZUL_CIANO, (mira_tx, mira_ty), max(4, int(round(6 * s))), width=max(1, int(round(s))))
                pygame.draw.circle(screen, DOURADO, (mira_tx, mira_ty), max(2, int(round(2 * s))))

    def _desenhar_banner_grace_period(self, screen):
        """Renderiza o banner centralizado com a contagem regressiva de 10s antes do Chefe Final em DPI nativo."""
        if not self.boss_grace_period_ativo or self.boss_cutscene_ativa:
            return

        ox, oy, vw, _vh, s = self._obter_viewport_nativo(screen)
        fonte = self._obter_fonte("grace_banner", s)
        linhas = self.obter_texto_boss_grace_period().split("\n")
        superficies = [fonte.render(linha, True, DOURADO if idx == 0 else BRANCO) for idx, linha in enumerate(linhas)]
        sombras = [fonte.render(linha, True, (10, 5, 20)) for linha in linhas]

        largura_max = max(sf.get_width() for sf in superficies)
        altura_linha = max(sf.get_height() for sf in superficies)
        pad_x = max(12, int(round(24 * s)))
        pad_y = max(6, int(round(12 * s)))
        espaco_linhas = max(3, int(round(6 * s)))

        box_w = largura_max + pad_x * 2
        box_h = len(linhas) * altura_linha + max(0, len(linhas) - 1) * espaco_linhas + pad_y * 2
        centro_x = ox + vw // 2
        box_x = centro_x - box_w // 2
        box_y = oy + int(round(118 * s))

        painel = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        painel.fill((18, 12, 30, 205))
        pygame.draw.rect(painel, DOURADO, (0, 0, box_w, box_h), width=max(1, int(round(2 * s))), border_radius=max(4, int(round(8 * s))))
        screen.blit(painel, (box_x, box_y))

        cur_y = box_y + pad_y
        off_sh = max(1, int(round(s)))
        for surf, sombra in zip(superficies, sombras):
            rect_sombra = sombra.get_rect(centerx=centro_x + off_sh, top=cur_y + off_sh)
            rect_surf = surf.get_rect(centerx=centro_x, top=cur_y)
            screen.blit(sombra, rect_sombra)
            screen.blit(surf, rect_surf)
            cur_y += altura_linha + espaco_linhas

    def _desenhar_toasts(self, screen):
        """Renderiza toasts de coleta flutuantes com clamp horizontal dentro da viewport nativa."""
        ox, oy, vw, _vh, s = self._obter_viewport_nativo(screen)
        fonte_toast = self._obter_fonte("toast", s)
        margem = max(8, int(round(12 * s)))
        off_sh = max(1, int(round(s)))
        for t in self.toasts_coleta:
            tx_tela = ox + self.camera.transform_x(t["x"]) * s
            ty_tela = oy + self.camera.transform_y(t["y"]) * s
            alpha = int(clamp((t["tempo"] / max(0.01, t["tempo_max"])) * 255, 0, 255))

            txt_surf = fonte_toast.render(t["texto"], True, t["cor"])
            txt_sombra = fonte_toast.render(t["texto"], True, (0, 0, 0))
            txt_surf.set_alpha(alpha)
            txt_sombra.set_alpha(alpha)

            rect = txt_surf.get_rect(centerx=int(round(tx_tela)), centery=int(round(ty_tela)))
            if rect.left < ox + margem:
                rect.left = ox + margem
            if rect.right > ox + vw - margem:
                rect.right = ox + vw - margem
            if rect.left < ox + margem:
                rect.left = ox + margem

            screen.blit(txt_sombra, (rect.x + off_sh, rect.y + off_sh))
            screen.blit(txt_surf, rect)

    def _desenhar_buffs_ativos(self, screen):
        """Renderiza badges e indicadores com timers de todos os buffs ativos abaixo do inventário (DPI nativo)."""
        if not hasattr(self.jogador, "obter_buffs_ativos"):
            return

        buffs = self.jogador.obter_buffs_ativos()
        if not buffs:
            return

        ox, oy, _vw, _vh, s = self._obter_viewport_nativo(screen)
        fonte_buff = self._obter_fonte("buff", s)
        fonte_timer = self._obter_fonte("timer", s)

        start_x = ox + int(round(16 * s))
        start_y = oy + int(round(132 * s))
        badge_w = max(60, int(round(152 * s)))
        badge_h = max(12, int(round(22 * s)))
        raio = max(2, int(round(3 * s)))
        borda_w = max(1, int(round(s)))
        passo_y = badge_h + max(2, int(round(3 * s)))

        for b in buffs:
            bg_rect = (start_x, start_y, badge_w, badge_h)
            cor_bg = b.get("cor_bg", (30, 30, 40))
            cor_borda = b.get("cor", (255, 255, 255))
            pygame.draw.rect(screen, cor_bg, bg_rect, border_radius=raio)
            pygame.draw.rect(screen, cor_borda, bg_rect, width=borda_w, border_radius=raio)

            # Barra de progresso do timer
            timer_val = b.get("timer", 0.0)
            duracao_max = b.get("duracao", 15.0)
            if duracao_max > 0.0 and timer_val < 900.0:
                prog = clamp(timer_val / duracao_max, 0.0, 1.0)
                pad_b = max(2, int(round(2 * s)))
                bar_w = int((badge_w - pad_b * 2) * prog)
                if bar_w > 0:
                    pygame.draw.rect(screen, cor_borda, (start_x + pad_b, start_y + badge_h - pad_b, bar_w, max(1, int(round(s)))))

            # Texto do nome do buff
            nome_surf = fonte_buff.render(b["nome"], True, cor_borda)
            screen.blit(nome_surf, (start_x + max(3, int(round(4 * s))), start_y + max(1, int(round(2 * s)))))

            # Texto do timer
            if timer_val < 900.0:
                timer_str = f"{timer_val:.1f}s"
                timer_surf = fonte_timer.render(timer_str, True, BRANCO)
                t_rect = timer_surf.get_rect(right=start_x + badge_w - max(3, int(round(4 * s))), centery=start_y + badge_h // 2 - max(1, int(round(s))))
                screen.blit(timer_surf, t_rect)

            start_y += passo_y

    def _desenhar_overlay_vitoria(self):
        """Overlay modal de vitória projetado em DPI nativo com grade de estatísticas."""
        screen = self.janela.screen
        scr_w, scr_h = screen.get_size() if hasattr(screen, "get_size") else (LARGURA_TELA, ALTURA_TELA)
        vox, voy, vw, vh, s = self._obter_viewport_nativo(screen)
        px_x = lambda lx: vox + int(round(lx * s))
        px_y = lambda ly: voy + int(round(ly * s))
        px_s = lambda v: max(1, int(round(v * s)))

        if self._overlay_surf is None or self._overlay_surf.get_size() != (scr_w, scr_h):
            self._overlay_surf = pygame.Surface((scr_w, scr_h), pygame.SRCALPHA)
        self._overlay_surf.fill((10, 15, 25, 235))
        screen.blit(self._overlay_surf, (0, 0))

        ox = (LARGURA_TELA - 800) // 2
        oy = (ALTURA_TELA - 600) // 2
        cx_tela = vox + vw // 2

        # Painel central estilizado
        painel_rect = pygame.Rect(px_x(ox + 90), px_y(oy + 40), px_s(620), px_s(520))
        pygame.draw.rect(screen, (25, 32, 45), painel_rect, border_radius=max(4, int(round(8 * s))))
        pygame.draw.rect(screen, DOURADO, painel_rect, width=max(1, int(round(2 * s))), border_radius=max(4, int(round(8 * s))))

        # Faixa superior de destaque
        fonte_tit = self._obter_fonte("tit_vit", s)
        tit_surf = fonte_tit.render("GELADEIRA TSUNAMI DESLIGADA", True, DOURADO)
        tit_rect = tit_surf.get_rect(centerx=cx_tela, top=px_y(oy + 60))
        screen.blit(tit_surf, tit_rect)

        minutos = int(self.tempo_sobrevivencia // 60)
        segundos = int(self.tempo_sobrevivencia % 60)
        tempo_str = f"{minutos:02d}:{segundos:02d} ({self.tempo_sobrevivencia:.1f}s)"

        fonte_sub = self._obter_fonte("sub_vit", s)
        sub_surf = fonte_sub.render(f"Cleiton sobreviveu ao escritório por {minutos:02d}:{segundos:02d}.", True, (200, 220, 240))
        sub_rect = sub_surf.get_rect(centerx=cx_tela, top=px_y(oy + 95))
        screen.blit(sub_surf, sub_rect)

        # Quadro de estatísticas internas
        quadro_rect = pygame.Rect(px_x(ox + 120), px_y(oy + 130), px_s(560), px_s(280))
        pygame.draw.rect(screen, (15, 20, 30), quadro_rect, border_radius=max(3, int(round(6 * s))))
        pygame.draw.rect(screen, (45, 60, 80), quadro_rect, width=max(1, int(round(s))), border_radius=max(3, int(round(6 * s))))

        fonte_stat_label = self._obter_fonte("stat_label", s)
        fonte_stat_val = self._obter_fonte("stat_val", s)
        fonte_stat_destaque = self._obter_fonte("stat_destaque", s)

        stats_data = [
            ("Tempo de Partida:", tempo_str, DOURADO),
            ("Máquinas Destruídas:", f"{self.abates}", AMARELO_XP),
            ("Dano Total Causado:", f"{self.dano_total_causado:,}", (255, 100, 100)),
            ("Configurações Desbloqueadas:", f"{len(self.gerenciador_config.desbloqueadas)} / {len(CONFIGURACOES_GAMEPLAY)}", AZUL_CIANO),
            ("Multiplicador de Configurações:", f"x{self.estatisticas_partida_resultado.get('mult_dif', 1.0):.2f}", (180, 210, 240)),
        ]

        start_y = oy + 145
        step_y = 34
        for i, (label, val_str, cor_val) in enumerate(stats_data):
            cur_y = px_y(start_y + i * step_y)
            lbl_surf = fonte_stat_label.render(label, True, (180, 195, 215))
            screen.blit(lbl_surf, (px_x(ox + 140), cur_y))

            val_surf = fonte_stat_val.render(val_str, True, cor_val)
            val_rect = val_surf.get_rect(right=px_x(ox + 660), top=cur_y)
            screen.blit(val_surf, val_rect)

        # Linha de separação
        pygame.draw.line(screen, (50, 65, 85), (px_x(ox + 140), px_y(oy + 315)), (px_x(ox + 660), px_y(oy + 315)), width=max(1, int(round(s))))

        # Pontuação Final
        score_val = self.estatisticas_partida_resultado.get("score_final", self.pontos)
        score_lbl = fonte_stat_destaque.render("PONTUAÇÃO FINAL:", True, DOURADO)
        screen.blit(score_lbl, (px_x(ox + 140), px_y(oy + 330)))

        score_num_surf = fonte_stat_destaque.render(f"{score_val:,} PTS", True, DOURADO)
        score_num_rect = score_num_surf.get_rect(right=px_x(ox + 660), top=px_y(oy + 330))
        screen.blit(score_num_surf, score_num_rect)

        # Badge de Recorde Histórico se atingido
        if self.estatisticas_partida_resultado.get("novo_recorde_pontos", False):
            badge_rec_surf = fonte_stat_val.render("[NOVO RECORDE!]", True, AMARELO_XP)
            badge_rec_rect = badge_rec_surf.get_rect(centerx=cx_tela, top=px_y(oy + 375))
            screen.blit(badge_rec_surf, badge_rec_rect)

        # Rodapé com atalhos de navegação
        fonte_btn = self._obter_fonte("btn", s)
        fonte_btn_sub = self._obter_fonte("btn_sub", s)

        btn1_surf = fonte_btn.render("[ENTER / ESPAÇO] Jogar Novamente", True, DOURADO)
        screen.blit(btn1_surf, btn1_surf.get_rect(centerx=cx_tela, top=px_y(oy + 430)))

        btn2_surf = fonte_btn_sub.render("[ESC / M] Menu Principal", True, (200, 210, 225))
        screen.blit(btn2_surf, btn2_surf.get_rect(centerx=cx_tela, top=px_y(oy + 465)))

        btn3_surf = fonte_btn_sub.render("[C] Menu de Configurações", True, AZUL_CIANO)
        screen.blit(btn3_surf, btn3_surf.get_rect(centerx=cx_tela, top=px_y(oy + 498)))

    def _obter_rects_overlay_pausa(self) -> tuple[pygame.Rect, pygame.Rect]:
        """Retorna os retângulos clicáveis de Continuar e Menu Principal no espaço lógico 1280x720."""
        oy = (ALTURA_TELA - 600) // 2
        cx = LARGURA_TELA // 2
        btn_cont_rect = pygame.Rect(cx - 160, oy + 272, 320, 40)
        btn_menu_rect = pygame.Rect(cx - 160, oy + 324, 320, 40)
        return btn_cont_rect, btn_menu_rect

    def _obter_rect_btn_conquistas_pausa(self) -> pygame.Rect:
        """Retorna o retângulo clicável do botão Conquistas & Firmware (somente leitura) no overlay de pausa."""
        oy = (ALTURA_TELA - 600) // 2
        cx = LARGURA_TELA // 2
        return pygame.Rect(cx - 160, oy + 376, 320, 40)

    def _desenhar_overlay_pausa(self):
        """Overlay modal de pausa projetado em DPI nativo com botões alinhados aos hitboxes lógicos."""
        screen = self.janela.screen
        scr_w, scr_h = screen.get_size() if hasattr(screen, "get_size") else (LARGURA_TELA, ALTURA_TELA)
        vox, voy, vw, _vh, s = self._obter_viewport_nativo(screen)
        px_x = lambda lx: vox + int(round(lx * s))
        px_y = lambda ly: voy + int(round(ly * s))
        px_s = lambda v: max(1, int(round(v * s)))

        if self._overlay_surf is None or self._overlay_surf.get_size() != (scr_w, scr_h):
            self._overlay_surf = pygame.Surface((scr_w, scr_h), pygame.SRCALPHA)
        self._overlay_surf.fill((10, 15, 22, 180))
        screen.blit(self._overlay_surf, (0, 0))

        oy = (ALTURA_TELA - 600) // 2
        cx_tela = vox + vw // 2
        fonte_titulo = self._obter_fonte("tit_pausa", s)
        fonte_sub = self._obter_fonte("sub_pausa", s)

        t_surf = fonte_titulo.render("JOGO PAUSADO", True, DOURADO)
        t_rect = t_surf.get_rect(centerx=cx_tela, top=px_y(oy + 200))
        screen.blit(t_surf, t_rect)

        btn_cont_l, btn_menu_l = self._obter_rects_overlay_pausa()
        btn_conq_l = self._obter_rect_btn_conquistas_pausa()
        btn_cont_rect = pygame.Rect(px_x(btn_cont_l.x), px_y(btn_cont_l.y), px_s(btn_cont_l.w), px_s(btn_cont_l.h))
        btn_menu_rect = pygame.Rect(px_x(btn_menu_l.x), px_y(btn_menu_l.y), px_s(btn_menu_l.w), px_s(btn_menu_l.h))
        btn_conq_rect = pygame.Rect(px_x(btn_conq_l.x), px_y(btn_conq_l.y), px_s(btn_conq_l.w), px_s(btn_conq_l.h))
        raio = max(3, int(round(6 * s)))
        bw = max(1, int(round(s)))

        pygame.draw.rect(screen, (30, 42, 62), btn_cont_rect, border_radius=raio)
        pygame.draw.rect(screen, AZUL_CIANO, btn_cont_rect, width=bw, border_radius=raio)
        c_surf = fonte_sub.render("[ESC] Continuar Partida", True, BRANCO)
        screen.blit(c_surf, c_surf.get_rect(center=btn_cont_rect.center))

        pygame.draw.rect(screen, (52, 34, 24), btn_menu_rect, border_radius=raio)
        pygame.draw.rect(screen, LARANJA_ALERTA, btn_menu_rect, width=bw, border_radius=raio)
        m_surf = fonte_sub.render("[M] Menu Principal", True, DOURADO)
        screen.blit(m_surf, m_surf.get_rect(center=btn_menu_rect.center))

        pygame.draw.rect(screen, (32, 22, 52), btn_conq_rect, border_radius=raio)
        pygame.draw.rect(screen, ROXO_ACENTO, btn_conq_rect, width=bw, border_radius=raio)
        q_surf = fonte_sub.render("Conquistas & Firmware", True, BRANCO)
        screen.blit(q_surf, q_surf.get_rect(center=btn_conq_rect.center))

        if hasattr(self, "banner_dicas") and self.banner_dicas is not None:
            dica_w = px_s(560)
            dica_rect = pygame.Rect(cx_tela - dica_w // 2, btn_conq_rect.bottom + px_s(18), dica_w, px_s(58))
            self.banner_dicas.desenhar(screen, dica_rect, scale=s)

    def _desenhar_overlay_game_over(self):
        """Overlay de fim de jogo projetado em DPI nativo com estatísticas centralizadas."""
        screen = self.janela.screen
        scr_w, scr_h = screen.get_size() if hasattr(screen, "get_size") else (LARGURA_TELA, ALTURA_TELA)
        vox, voy, vw, _vh, s = self._obter_viewport_nativo(screen)
        px_x = lambda lx: vox + int(round(lx * s))
        px_y = lambda ly: voy + int(round(ly * s))
        px_s = lambda v: max(1, int(round(v * s)))

        if self._overlay_surf is None or self._overlay_surf.get_size() != (scr_w, scr_h):
            self._overlay_surf = pygame.Surface((scr_w, scr_h), pygame.SRCALPHA)
        self._overlay_surf.fill((20, 5, 5, 210))
        screen.blit(self._overlay_surf, (0, 0))

        ox = (LARGURA_TELA - 800) // 2
        oy = (ALTURA_TELA - 600) // 2
        cx_tela = vox + vw // 2

        fonte_tit = self._obter_fonte("tit_go", s)
        fonte_sub = self._obter_fonte("sub_go", s)
        fonte_stat = self._obter_fonte("stat_go", s)
        fonte_prompt = self._obter_fonte("prompt_go", s)

        tit_surf = fonte_tit.render("FIM DE LINHA", True, VERMELHO_HP)
        screen.blit(tit_surf, tit_surf.get_rect(centerx=cx_tela, top=px_y(oy + 115)))

        sub_surf = fonte_sub.render("As máquinas do escritório drenaram a bateria de Cleiton.", True, (200, 180, 180))
        screen.blit(sub_surf, sub_surf.get_rect(centerx=cx_tela, top=px_y(oy + 162)))

        causa_str = getattr(self.jogador, "ultima_causa_morte", "") or "Dano fatal no escritório"
        causa_surf = fonte_stat.render(f"Causa da Morte: {causa_str}", True, LARANJA_ALERTA)
        screen.blit(causa_surf, causa_surf.get_rect(centerx=cx_tela, top=px_y(oy + 190)))

        minutos = int(self.tempo_sobrevivencia // 60)
        segundos = int(self.tempo_sobrevivencia % 60)

        # Quadro escuro
        quadro_rect = pygame.Rect(px_x(ox + 150), px_y(oy + 225), px_s(500), px_s(210))
        pygame.draw.rect(screen, (28, 15, 20), quadro_rect, border_radius=max(4, int(round(8 * s))))
        pygame.draw.rect(screen, (80, 40, 50), quadro_rect, width=max(1, int(round(s))), border_radius=max(4, int(round(8 * s))))

        tempo_surf = fonte_stat.render(f"Tempo de Partida: {minutos:02d}:{segundos:02d}", True, BRANCO)
        screen.blit(tempo_surf, tempo_surf.get_rect(centerx=cx_tela, top=px_y(oy + 242)))

        abates_surf = fonte_stat.render(f"Total de Abates: {self.abates}", True, AMARELO_XP)
        screen.blit(abates_surf, abates_surf.get_rect(centerx=cx_tela, top=px_y(oy + 278)))

        dano_surf = fonte_stat.render(f"Dano Total: {self.dano_total_causado:,}", True, (255, 120, 120))
        screen.blit(dano_surf, dano_surf.get_rect(centerx=cx_tela, top=px_y(oy + 314)))

        score_val = self.estatisticas_partida_resultado.get("score_final", self.pontos)
        pontos_surf = fonte_stat.render(f"Pontuação Final: {score_val:,} PTS", True, DOURADO)
        screen.blit(pontos_surf, pontos_surf.get_rect(centerx=cx_tela, top=px_y(oy + 350)))

        if self.estatisticas_partida_resultado.get("novo_recorde_pontos", False):
            rec_surf = fonte_stat.render("[NOVO RECORDE DE PONTOS!]", True, AMARELO_XP)
            screen.blit(rec_surf, rec_surf.get_rect(centerx=cx_tela, top=px_y(oy + 386)))

        prompt_surf = fonte_prompt.render("Pressione [ENTER] para Jogar Novamente ou [ESC] para o Menu", True, DOURADO)
        screen.blit(prompt_surf, prompt_surf.get_rect(centerx=cx_tela, top=px_y(oy + 458)))
