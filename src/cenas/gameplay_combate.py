"""
Resolução de Combate, Armas, Parry, Railgun, Overvolt e Abates — Protocolo: Batata
Extraído de GameplayScene como mixin behavior-preserving (GameplayCombateMixin).
"""

import math
import random
import sys
import pygame
from src.armas.pistola import Pistola
from src.armas.melee import Melee
from src.armas.railgun import Railgun
from src.entidades.projetil import Projetil
from src.entidades.geladeira_tsunami import ESTADO_MORTE
from src.sistemas.efeitos_combate import ContextoCombate
from src.utils import constantes as _const
from src.utils.constantes import (
    LARGURA_TELA, ALTURA_TELA,
    DASH_PARRY_META,
    VERMELHO_DANO, AZUL_CIANO, DOURADO, LARANJA_ALERTA,
    SAVE_FILE_PATH,
)
from src.utils.math_utils import colisao_aabb, distancia, vetor_direcao


class GameplayCombateMixin:
    """
    Mixin responsável pelas ações de combate, melee, parry, railgun, overvolt,
    resolução de projéteis/colisões e registro de abates da GameplayScene.
    """

    def _obter_gerenciador_config(self):
        return getattr(self, "gerenciador_config", None) or getattr(self, "config_sistema", None)

    def _obter_efeitos_combate(self):
        return getattr(self, "efeitos_combate", None)

    def _obter_sistema_combo(self):
        return getattr(self, "sistema_combo", None)

    def _obter_sistema_conquistas(self):
        sis = getattr(self, "sistema_conquistas", None)
        if sis is not None:
            return sis
        ger = self._obter_gerenciador_config()
        return getattr(ger, "sistema_conquistas", None) if ger is not None else None

    def _construir_ctx_combate(self, mods=None, profundidade_recursao: int = 0) -> ContextoCombate:
        ger = self._obter_gerenciador_config()
        if mods is None and ger is not None and hasattr(ger, "obter_modificadores"):
            mods = ger.obter_modificadores()
        drops_obj = getattr(self, "sistema_drops", None)
        drops_list = getattr(drops_obj, "drops", []) if drops_obj is not None else []
        return ContextoCombate(
            cena=self,
            jogador=getattr(self, "jogador", None),
            inimigos=getattr(self, "inimigos", []),
            projeteis=getattr(self, "projeteis", []),
            drops=drops_list,
            particulas=getattr(self, "sistema_particulas", None),
            mods=mods,
            sistema_combo=self._obter_sistema_combo(),
            sistema_conquistas=self._obter_sistema_conquistas(),
            hologramas=getattr(self, "hologramas", None),
            tempo_sobrevivencia=float(getattr(self, "tempo_sobrevivencia", 0.0)),
            profundidade_recursao=int(profundidade_recursao),
        )

    @staticmethod
    def _obter_sfx_arma(arma) -> str | None:
        if arma is None:
            return None
        id_arma = str(getattr(arma, "id_arma", "") or "").lower()
        nome = str(getattr(arma, "nome", "") or "").lower()
        if id_arma == "smg_compacta" or "smg" in nome:
            return "sfx_tiro_minigun"
        if id_arma == "bastao_choque" or "bastão" in nome or "bastao" in nome:
            return "sfx_ataque_melee"
        if id_arma == "rifle_arco" or "rifle de arco" in nome or "arco" in id_arma:
            return "sfx_tiro_railgun"
        if id_arma == "lanca_chamas" or "lança-chamas" in nome or "lanca_chamas" in nome or "chamas" in id_arma:
            return "sfx_tiro_foguete"
        if id_arma == "pistola" or "pistola" in nome:
            return "sfx_tiro_pistola"
        if "minigun" in nome:
            return "sfx_tiro_minigun"
        if "shotgun" in nome or "escopeta" in nome:
            return "sfx_tiro_shotgun"
        if "rifle" in nome:
            return "sfx_tiro_rifle"
        if "foguete" in nome:
            return "sfx_tiro_foguete"
        if "granada" in nome:
            return "sfx_tiro_granada"
        if "railgun" in nome:
            return "sfx_tiro_railgun"
        if "chave" in nome or getattr(arma, "slot", None) == 1:
            return "sfx_ataque_melee"
        return None

    def _tentar_registrar_just_dodge(self, origem: str = "projetil", mods=None) -> bool:
        """Consome a janela de Just-Dodge do Dash e notifica Combo, Conquistas e Pipeline B+."""
        jogador = getattr(self, "jogador", None)
        if jogador is None or not hasattr(jogador, "consumir_just_dodge"):
            return False
        if not jogador.consumir_just_dodge():
            return False

        sis_combo = self._obter_sistema_combo()
        if sis_combo is not None:
            sis_combo.registrar_just_dodge(getattr(jogador, "dash_id_atual", 0))

        sis_cnq = self._obter_sistema_conquistas()
        if sis_cnq is not None and hasattr(sis_cnq, "registrar_evento"):
            notifs = sis_cnq.registrar_evento("just_dodge", 1)
            if notifs:
                ger = self._obter_gerenciador_config()
                if ger is not None and hasattr(ger, "sincronizar_recompensas_conquistas"):
                    ger.sincronizar_recompensas_conquistas()
                if ger is not None and hasattr(ger, "salvar_arquivo"):
                    try:
                        save_path = getattr(
                            sys.modules.get("src.cenas.gameplay"),
                            "SAVE_FILE_PATH",
                            SAVE_FILE_PATH,
                        )
                        ger.salvar_arquivo(save_path)
                    except Exception:
                        pass

        efeitos = self._obter_efeitos_combate()
        if efeitos is not None:
            efeitos.disparar_ao_dash_evasao(
                self._construir_ctx_combate(mods), {"origem": origem}
            )

        if hasattr(self, "toasts_coleta"):
            cx = jogador.x + getattr(jogador, "largura", 32) / 2.0
            self.toasts_coleta.append({
                "texto": "JUST-DODGE!",
                "cor": AZUL_CIANO,
                "x": cx,
                "y": jogador.y - 22,
                "tempo": 1.1,
                "tempo_max": 1.1,
            })
        return True

    def _aplicar_efeitos_disparo_extras(self, novos_tiros: list, mods):
        """Aplica efeitos adicionais de disparo (Refrigeração, Multithreading e Auto-Fire Burst)."""
        if not novos_tiros:
            return

        # 1. Refrigeração a Nitrogênio: atirar reinicia o timer de resfriamento
        if getattr(self.jogador, "refrigeracao_nitrogenio", False):
            self.jogador.timer_sem_atirar_refrig = 0.0

        # 2. Multithreading (Overclock BIOS): dispara eco via coprocessadores orbitais com 0.08s de delay
        if getattr(self.jogador, "multithreading", False):
            angulos = getattr(self.jogador, "coprocessadores_angulos", [0.0, 3.14159])
            for ang_cop in angulos:
                cx_cop = self.jogador.x + self.jogador.largura / 2.0 + math.cos(ang_cop) * 34.0
                cy_cop = self.jogador.y + self.jogador.altura / 2.0 + math.sin(ang_cop) * 34.0
                tiros_multi = []
                ang_var = random.uniform(-0.10, 0.10)
                cos_v, sin_v = math.cos(ang_var), math.sin(ang_var)
                for p in novos_tiros:
                    vx_n = p.vx * cos_v - p.vy * sin_v
                    vy_n = p.vx * sin_v + p.vy * cos_v
                    tiros_multi.append(p.clonar(x=cx_cop, y=cy_cop, vx=vx_n, vy=vy_n))
                self.tiros_echo_pendentes.append({"timer": 0.08, "projeteis": tiros_multi})

        # 3. Auto-Fire Burst (Configuração de Auto-Disparo): eco adicional independente de 0.08s
        if getattr(mods, "auto_fire_burst", False):
            tiros_burst = []
            ang_var = random.uniform(-0.10, 0.10)
            cos_v, sin_v = math.cos(ang_var), math.sin(ang_var)
            for p in novos_tiros:
                vx_n = p.vx * cos_v - p.vy * sin_v
                vy_n = p.vx * sin_v + p.vy * cos_v
                tiros_burst.append(p.clonar(vx=vx_n, vy=vy_n))
            self.tiros_echo_pendentes.append({"timer": 0.08, "projeteis": tiros_burst})

        # 3.5 Efeitos de disparo de armas únicas (Gatilho Magnético, Munição Superaquecida, Recuo Minigun, Trilha Railgun, Cápsulas e Áudio)
        arma_at = self.jogador.obter_arma_ativa() if self.jogador.vivo else None
        if getattr(self.jogador, "buff_cadencia_timer", 0.0) > 0.0 and arma_at is not None and not getattr(arma_at, "municao_infinita", True):
            if hasattr(arma_at, "municao_atual") and hasattr(arma_at, "municao_max"):
                arma_at.municao_atual = min(arma_at.municao_max, arma_at.municao_atual + 1)

        # Ejeção de cápsula de latão persistente no chão
        p0 = novos_tiros[0]
        cx_j = self.jogador.x + self.jogador.largura / 2.0
        cy_j = self.jogador.y + self.jogador.altura / 2.0
        if hasattr(self.sistema_particulas, "adicionar_capsula"):
            self.sistema_particulas.adicionar_capsula(cx_j, cy_j, dir_x=getattr(p0, "dir_x", 1.0), dir_y=getattr(p0, "dir_y", 0.0))

        teve_sobrecarregado = any(getattr(p, "sobrecarregado", False) for p in novos_tiros)
        if teve_sobrecarregado:
            self.aplicar_shake(3.0, 0.12)
            if hasattr(self, "sistema_audio") and self.sistema_audio is not None:
                self.sistema_audio.tocar_tiro_sobrecarregado()
        elif hasattr(self, "sistema_audio") and self.sistema_audio is not None:
            chave_sfx = self._obter_sfx_arma(arma_at) or GameplayCombateMixin._obter_sfx_arma(arma_at)
            if chave_sfx:
                self.sistema_audio.tocar_sfx(chave_sfx, pitch_aleatorio=True)

        for p in novos_tiros:
            if getattr(self.jogador, "buff_dano_timer", 0.0) > 0.0:
                p.superaquecido = True
                p.perfuracoes_restantes = max(getattr(p, "perfuracoes_restantes", 0), 1)
            if getattr(p, "recuo_autor", 0.0) > 0.0:
                self.jogador.x -= p.dir_x * p.recuo_autor * 0.15
                self.jogador.y -= p.dir_y * p.recuo_autor * 0.15
                self._clamp_entidade_arena(self.jogador)
            if getattr(p, "trilha_plasma", False):
                ox, oy = getattr(p, "origem_trilha", (p.x_origem, p.y_origem))
                self.trilhas_plasma.append({
                    "x1": ox,
                    "y1": oy,
                    "x2": ox + p.dir_x * 1100.0,
                    "y2": oy + p.dir_y * 1100.0,
                    "tempo": 0.40,
                    "tempo_max": 0.40
                })

    def _ao_errar_parry(self):
        """Callback acionado quando a janela de parry expira sem refletir projéteis: hitstop 0.2s, som triste e Exposto."""
        self.hitstop_timer = max(getattr(self, "hitstop_timer", 0.0), 0.20)
        self.aplicar_shake(7.0, 0.22)
        if hasattr(self, "sistema_audio") and self.sistema_audio is not None and hasattr(self.sistema_audio, "tocar_parry_whiff"):
            self.sistema_audio.tocar_parry_whiff()
        if hasattr(self, "jogador") and self.jogador is not None:
            self.jogador.exposed_timer = max(getattr(self.jogador, "exposed_timer", 0.0), 1.5)
            cx = self.jogador.x + self.jogador.largura / 2.0
            self.toasts_coleta.append({
                "texto": "EXPOSTO! (+DANO RECEBIDO)",
                "cor": VERMELHO_DANO,
                "x": cx,
                "y": self.jogador.y - 24,
                "tempo": 1.6,
                "tempo_max": 1.6
            })

    def _processar_parry_ativo(self, arma_melee, cx: float, cy: float, angulo_mira: float | None = None) -> list:
        """Verifica e processa parries ativos (padrão, Contra-Detonação, Duelo 3-Estágios e Configs)."""
        if arma_melee is None or not hasattr(arma_melee, "tentar_parry_projeteis"):
            return []
        rebatidos = arma_melee.tentar_parry_projeteis(
            cx, cy, self.projeteis, angulo_mira=angulo_mira
        )
        if not rebatidos:
            return []

        mods = self._obter_gerenciador_config().obter_modificadores() if self._obter_gerenciador_config() else None
        parry_ef = getattr(mods, "parry_efeito", "padrao") if mods else "padrao"

        # Onda de Choque Defensiva Imediata ("Perigo Vira Arma")
        raio_onda = float(getattr(_const, "PARRY_ONDA_RAIO", 135.0))
        dano_onda = int(getattr(_const, "PARRY_ONDA_DANO", 20))
        kb_onda = float(getattr(_const, "PARRY_ONDA_KNOCKBACK", 380.0))
        if hasattr(self, "sistema_particulas") and self.sistema_particulas is not None:
            self.sistema_particulas.emitir_onda_choque(cx, cy, raio_max=raio_onda, cor=DOURADO)
        for inim in list(getattr(self, "inimigos", [])):
            if not getattr(inim, "vivo", True) or getattr(inim, "em_fase", False):
                continue
            if getattr(inim, "is_boss", False) or inim is getattr(self, "chefe_final", None):
                continue
            if getattr(inim, "estado", "") in ("morte", ESTADO_MORTE):
                continue
            icx = inim.x + getattr(inim, "largura", 28) / 2.0
            icy = inim.y + getattr(inim, "altura", 28) / 2.0
            if distancia(cx, cy, icx, icy) <= raio_onda:
                dx_k, dy_k = vetor_direcao(cx, cy, icx, icy)
                if dx_k == 0.0 and dy_k == 0.0:
                    dx_k = 1.0
                if hasattr(inim, "aplicar_knockback"):
                    inim.aplicar_knockback(dx_k, dy_k, kb_onda)
                else:
                    inim.x += dx_k * (kb_onda * 0.12)
                    inim.y += dy_k * (kb_onda * 0.12)
                if hasattr(self, "_clamp_entidade_arena"):
                    self._clamp_entidade_arena(inim)
                ret_onda = inim.receber_dano(
                    dano_onda,
                    origem_x=cx,
                    origem_y=cy,
                    dir_ataque=(dx_k, dy_k),
                    fonte="parry_onda",
                )
                dano_onda_ef = int(ret_onda) if isinstance(ret_onda, (int, float)) else dano_onda
                self.dano_total_causado = getattr(self, "dano_total_causado", 0) + dano_onda_ef
                if not getattr(inim, "vivo", True):
                    self._registrar_abate_inimigo(inim, mods, origem="parry")

        eh_pesado = any(
            getattr(pr, "sobrecarga_termica", False) or int(getattr(pr, "duel_stage", 0)) >= 3
            for pr in rebatidos
        )
        max_stage = max([int(getattr(pr, "duel_stage", 0)) for pr in rebatidos] + [0])
        pitch_clang = 1.5 if max_stage >= 3 else (1.25 if max_stage == 2 else 1.0)

        self.hitstop_timer = max(getattr(self, "hitstop_timer", 0.0), 0.18 if eh_pesado else 0.10)
        self.aplicar_shake(12.0 if eh_pesado else 8.0, 0.25 if eh_pesado else 0.20)
        if hasattr(self, "sistema_audio") and self.sistema_audio is not None:
            self.sistema_audio.tocar_parry_clang(pitch_mult=pitch_clang)

        ang_parry = angulo_mira if angulo_mira is not None else getattr(arma_melee, "parry_angulo", 0.0)
        raio_parry = getattr(arma_melee, "parry_alcance", 109.0)
        arco_parry = getattr(arma_melee, "arco_graus", 90.0)
        if hasattr(self.sistema_particulas, "adicionar_arco_parry"):
            self.sistema_particulas.adicionar_arco_parry(
                cx, cy, ang_parry, raio=raio_parry, arco_graus=arco_parry
            )

        if parry_ef == "pulso_emp":
            self.sistema_particulas.emitir_onda_choque(cx, cy, raio_max=150.0, cor=(56, 189, 248))
            for inim in getattr(self, "inimigos", []):
                if getattr(inim, "vivo", True) and not getattr(inim, "is_boss", False):
                    icx = inim.x + getattr(inim, "largura", 28) / 2.0
                    icy = inim.y + getattr(inim, "altura", 28) / 2.0
                    if distancia(cx, cy, icx, icy) <= 165.0:
                        inim.slow_timer = max(getattr(inim, "slow_timer", 0.0), 1.2)
                        inim.slow_fator = 0.0

        extras_gerados = []
        for pr in rebatidos:
            px_c = pr.x + getattr(pr, "largura", 8) / 2.0
            py_c = pr.y + getattr(pr, "altura", 8) / 2.0
            self.sistema_particulas.emitir_faiscas(
                px_c, py_c, dir_x=math.cos(ang_parry), dir_y=math.sin(ang_parry), cor=DOURADO, qtd=8
            )

            # Duelo de Parry em 3 Estágios (Ninja / Boss Core)
            stage = int(getattr(pr, "duel_stage", 0))
            owner = getattr(pr, "duel_owner", None)
            if stage in (1, 2) and owner is not None and getattr(owner, "vivo", False) and hasattr(owner, "disparar_contra_ataque_duelo"):
                pr.ativo = False
                owner.disparar_contra_ataque_duelo(stage + 1, (cx, cy))
                self.toasts_coleta.append({
                    "texto": f"DUELO PARRY {stage}/3!",
                    "cor": (251, 146, 60),
                    "x": cx, "y": self.jogador.y - 22, "tempo": 1.2, "tempo_max": 1.2
                })
            elif stage >= 3:
                self.sistema_particulas.emitir_onda_choque(cx, cy, raio_max=180.0, cor=DOURADO)
                self.jogador.curar(15)
                if owner is not None and getattr(owner, "vivo", False):
                    if getattr(owner, "is_boss", False):
                        owner.stagger_timer = max(getattr(owner, "stagger_timer", 0.0), 0.6)
                        owner.receber_dano(1200)
                        self.pocas_gelo = [p for p in self.pocas_gelo if distancia(cx, cy, p["x"], p["y"]) > 220.0]
                    else:
                        owner.receber_dano(9999, fonte="parry_ninja_proprio")
                        if not owner.vivo:
                            self._registrar_abate_inimigo(owner, mods)
                self.toasts_coleta.append({
                    "texto": "DUELO VENCIDO! +15 HP",
                    "cor": DOURADO,
                    "x": cx, "y": self.jogador.y - 26, "tempo": 1.8, "tempo_max": 1.8
                })

            # Contra-Detonação (Impressora Térmica / Núcleo Criogênico)
            if getattr(pr, "sobrecarga_termica", False):
                self.sistema_particulas.emitir_onda_choque(px_c, py_c, raio_max=180.0, cor=(251, 146, 60))
                if getattr(pr, "criogenico", False) and self.chefe_final is not None and getattr(self.chefe_final, "vivo", False):
                    self.chefe_final.stagger_timer = max(getattr(self.chefe_final, "stagger_timer", 0.0), 0.6)
                    self.pocas_gelo = [p for p in self.pocas_gelo if distancia(px_c, py_c, p["x"], p["y"]) > 220.0]
                alvos_vivos = [e for e in getattr(self, "inimigos", []) if getattr(e, "vivo", True)]
                alvos_vivos.sort(key=lambda e: distancia(px_c, py_c, e.x + getattr(e, "largura", 28) / 2.0, e.y + getattr(e, "altura", 28) / 2.0))
                for idx_s in range(4):
                    if idx_s < len(alvos_vivos):
                        alvo_s = alvos_vivos[idx_s]
                        sdx, sdy = vetor_direcao(px_c, py_c, alvo_s.x + getattr(alvo_s, "largura", 28) / 2.0, alvo_s.y + getattr(alvo_s, "altura", 28) / 2.0)
                    else:
                        ang_s = ang_parry + (idx_s - 1.5) * 0.45
                        sdx, sdy = math.cos(ang_s), math.sin(ang_s)
                    extras_gerados.append(Projetil(
                        x=px_c - 4.0, y=py_c - 4.0, dir_x=sdx, dir_y=sdy,
                        velocidade=520.0, dano=max(35, pr.dano), tempo_vida=2.0,
                        dono="jogador", largura=9, altura=9, sprite_key="projetil_pistola",
                        perfurante=True, cor=(253, 224, 71), refletido_parry=True
                    ))

            # Config efeito_parry == "estilhaco"
            if parry_ef == "estilhaco" and pr.ativo:
                pr.raio_explosao = 0.0
                pr.perfurante = True
                pr.dano = max(1, int(round(pr.dano * 0.75)))
                ang_base = math.atan2(pr.dir_y, pr.dir_x)
                for off_est in (-0.22, 0.22):
                    extras_gerados.append(pr.clonar(
                        vx=math.cos(ang_base + off_est) * pr.velocidade,
                        vy=math.sin(ang_base + off_est) * pr.velocidade
                    ))

        # Contagem única de Parry por parry_janela_id (sem contagem dupla entre gerenciador_config e sistema_conquistas)
        janela_id = int(getattr(arma_melee, "parry_janela_id", 0))
        if janela_id != getattr(self, "_ultima_janela_parry_contada", -1):
            self._ultima_janela_parry_contada = janela_id
            sis_combo = self._obter_sistema_combo()
            if sis_combo is not None:
                sis_combo.registrar_parry(janela_id)

            ger = self._obter_gerenciador_config()
            if ger is not None and hasattr(ger, "registrar_parry"):
                total_parries, recem_desbloqueou = ger.registrar_parry(DASH_PARRY_META)
                if recem_desbloqueou:
                    self.jogador.dash_desbloqueado = True
                    self.toasts_coleta.append({
                        "texto": "DASH + SMG COMPACTA DESBLOQUEADOS!",
                        "cor": AZUL_CIANO,
                        "x": cx, "y": self.jogador.y - 22, "tempo": 2.6, "tempo_max": 2.6
                    })
                elif total_parries % 5 == 0:
                    self.toasts_coleta.append({
                        "texto": f"PARRY {total_parries}/{DASH_PARRY_META}",
                        "cor": DOURADO,
                        "x": cx, "y": self.jogador.y - 18, "tempo": 1.8, "tempo_max": 1.8
                    })
            else:
                sis_cnq = self._obter_sistema_conquistas()
                if sis_cnq is not None and hasattr(sis_cnq, "registrar_evento"):
                    sis_cnq.registrar_evento("parry", 1)

        efeitos = self._obter_efeitos_combate()
        if efeitos is not None:
            efeitos.disparar_ao_parry(self._construir_ctx_combate(mods), rebatidos)

        if extras_gerados:
            self.projeteis.extend(extras_gerados)
        return rebatidos

    def _executar_golpe_melee(
        self,
        arma_melee,
        centro_jogador_x: float,
        centro_jogador_y: float,
        mouse_mundo_x: float,
        mouse_mundo_y: float,
        crit_chance: float,
        crit_mult: float,
        mult_dano_buff: float,
        mods
    ):
        """Executa golpe corpo-a-corpo puro (Slot 1 / LMB) com knockback e sem janela de parry/whiff."""
        ang_mira = math.atan2(mouse_mundo_y - centro_jogador_y, mouse_mundo_x - centro_jogador_x)
        if hasattr(self, "sistema_audio") and self.sistema_audio is not None:
            self.sistema_audio.tocar_sfx("sfx_ataque_melee", pitch_aleatorio=True)

        afetados = arma_melee.executar_ataque(
            centro_jogador_x, centro_jogador_y,
            self.inimigos,
            mira_x=mouse_mundo_x,
            mira_y=mouse_mundo_y,
            angulo_mira=ang_mira,
            aplicar_dano=False,
            abrir_janela_parry=False,
        )

        sis_combo = self._obter_sistema_combo()
        mult_combo_dano = 1.0
        mult_sinc = 1.0
        if sis_combo is not None:
            mults_c = sis_combo.obter_multiplicadores()
            mult_combo_dano = float(mults_c.get("dano_mult", 1.0))
            if sis_combo.consumir_golpe_sincronizado():
                mult_sinc = 1.25
        efeitos = self._obter_efeitos_combate()
        ctx = self._construir_ctx_combate(mods) if efeitos is not None else None

        if isinstance(afetados, (list, tuple)):
            for inim in afetados:
                dano_base = getattr(arma_melee, "dano", 10)
                is_crit = (crit_chance > 0.0 and random.random() < crit_chance)
                dano_melee = math.ceil(dano_base * mult_dano_buff * mult_combo_dano * mult_sinc * (crit_mult if is_crit else 1.0))
                if efeitos is not None and ctx is not None:
                    res_imp = efeitos.disparar_ao_impacto(ctx, inim, dano_melee, fonte="melee")
                    if res_imp:
                        if res_imp.get("critico_forcado") and not is_crit:
                            is_crit = True
                            dano_melee = math.ceil(dano_melee * crit_mult)
                        if "dano_mult" in res_imp:
                            dano_melee = max(1, int(round(dano_melee * float(res_imp["dano_mult"]))))
                        if "dano_extra" in res_imp:
                            dano_melee += int(res_imp["dano_extra"])

                if getattr(mods, "screen_shake_stagger", False) and inim is not self.chefe_final and not getattr(inim, "is_boss", False):
                    inim.x += math.cos(ang_mira) * 10.0
                    inim.y += math.sin(ang_mira) * 10.0
                    self._clamp_entidade_arena(inim)
                    inim.slow_timer = max(getattr(inim, "slow_timer", 0.0), 1.2)
                    inim.slow_fator = 0.50

                ret_d = inim.receber_dano(
                    dano_melee,
                    origem_x=centro_jogador_x,
                    origem_y=centro_jogador_y,
                    dir_ataque=(math.cos(ang_mira), math.sin(ang_mira))
                )
                dano_efetivo_m = int(ret_d) if isinstance(ret_d, (int, float)) else dano_melee
                self.dano_total_causado += dano_efetivo_m
                self.sistema_particulas.emitir_faiscas(
                    inim.x + getattr(inim, "largura", 28) / 2.0,
                    inim.y + getattr(inim, "altura", 28) / 2.0,
                    dir_x=math.cos(ang_mira),
                    dir_y=math.sin(ang_mira),
                    cor=(255, 240, 150),
                    qtd=5
                )
                if hasattr(self, "config_sistema") and str(self.config_sistema.obter_valor("damage_numbers")).lower() in ("ligado", "true", "1"):
                    self.sistema_particulas.emitir_texto_dano(
                        inim.x + getattr(inim, "largura", 28) / 2.0,
                        inim.y,
                        dano_efetivo_m,
                        critico=is_crit
                    )

                if is_crit:
                    self._aplicar_overvolt_chain(inim, dano_efetivo_m, mods)

                if not getattr(inim, "vivo", True):
                    self._registrar_abate_inimigo(inim, mods, origem="melee")
                elif inim is not self.chefe_final and not getattr(inim, "is_boss", False):
                    self._clamp_entidade_arena(inim)

        self.efeitos_melee.append({
            "x": centro_jogador_x,
            "y": centro_jogador_y,
            "angulo": ang_mira,
            "alcance": getattr(arma_melee, "alcance", 109.0),
            "arco_graus": getattr(arma_melee, "arco_graus", 120.0),
            "tempo": 0.15,
            "tempo_total": 0.15
        })

    @staticmethod
    def _dist_ponto_segmento(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
        """Calcula a menor distância euclidiana entre um ponto e um segmento de reta."""
        dx = x2 - x1
        dy = y2 - y1
        len_sq = dx * dx + dy * dy
        if len_sq <= 1e-9:
            return math.hypot(px - x1, py - y1)
        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / len_sq))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return math.hypot(px - proj_x, py - proj_y)

    def _executar_disparo_railgun(
        self,
        arma_railgun,
        origem_x: float,
        origem_y: float,
        alvo_x: float,
        alvo_y: float,
        mods=None,
        hitbox_mult: float = 1.0,
        mult_dano_buff: float = 1.0
    ) -> bool:
        """Executa o disparo hitscan instantâneo da Railgun (port 1:1 da v2)."""
        feixe = arma_railgun.disparar_feixe(origem_x, origem_y, alvo_x, alvo_y, alcance=1800.0)
        if not feixe:
            return False

        if getattr(self.jogador, "buff_cadencia_timer", 0.0) > 0.0 and hasattr(arma_railgun, "municao_atual"):
            arma_railgun.municao_atual = min(arma_railgun.municao_max, arma_railgun.municao_atual + 1)

        if hasattr(self, "sistema_audio") and self.sistema_audio is not None:
            try:
                self.sistema_audio.tocar_sfx("sfx_tiro_railgun", variacao_pitch=False)
            except Exception:
                pass

        feixes = [feixe]
        if getattr(mods, "auto_fire_burst", False):
            ang_var = random.uniform(-0.08, 0.08)
            cos_v, sin_v = math.cos(ang_var), math.sin(ang_var)
            dx2 = feixe["dir_x"] * cos_v - feixe["dir_y"] * sin_v
            dy2 = feixe["dir_x"] * sin_v + feixe["dir_y"] * cos_v
            feixes.append({
                **feixe,
                "x2": feixe["x1"] + dx2 * 1800.0,
                "y2": feixe["y1"] + dy2 * 1800.0,
                "dir_x": dx2,
                "dir_y": dy2,
            })

        show_dmg = hasattr(self, "config_sistema") and str(self.config_sistema.obter_valor("damage_numbers")).lower() in ("ligado", "true", "1")
        mult_mod = getattr(mods, "dano_mult", 1.0) if mods else 1.0

        for f in feixes:
            self.trilhas_plasma.append({
                "x1": f["x1"],
                "y1": f["y1"],
                "x2": f["x2"],
                "y2": f["y2"],
                "tempo": 0.20,
                "tempo_max": 0.20
            })

            dano_base = max(1, math.ceil(f["dano"] * mult_dano_buff * mult_mod))
            raio_feixe = f["raio"] * hitbox_mult

            for inim in list(self.inimigos):
                if not getattr(inim, "vivo", True):
                    continue
                if getattr(inim, "em_fase", False):
                    continue
                if getattr(inim, "estado", "") in ("morte", ESTADO_MORTE):
                    continue

                ecx = inim.x + getattr(inim, "largura", 28) / 2.0
                ecy = inim.y + getattr(inim, "altura", 28) / 2.0
                e_raio = max(getattr(inim, "largura", 28), getattr(inim, "altura", 28)) * 0.5

                if self._dist_ponto_segmento(ecx, ecy, f["x1"], f["y1"], f["x2"], f["y2"]) <= (e_raio + raio_feixe):
                    critico = bool(getattr(mods, "crits_habilitados", False) and random.random() < 0.25)
                    dano_hit = dano_base * 2 if critico else dano_base
                    ret_d = inim.receber_dano(dano_hit)
                    dano_efetivo = int(ret_d) if isinstance(ret_d, (int, float)) else dano_hit
                    self.dano_total_causado += dano_efetivo
                    self.sistema_particulas.emitir_faiscas(
                        ecx, ecy, dir_x=f["dir_x"], dir_y=f["dir_y"], cor=(56, 189, 248), qtd=8
                    )
                    if show_dmg or critico:
                        self.sistema_particulas.emitir_texto_dano(ecx, inim.y, dano_efetivo, critico=critico)
                    if not getattr(inim, "vivo", True):
                        self._registrar_abate_inimigo(inim, mods)

        self.aplicar_shake(6.0, 0.14)
        return True

    def _aplicar_overvolt_chain(self, alvo_origem, dano_base: int, mods=None):
        """Aplica corrente elétrica em cadeia (Overvolt) a partir de um alvo atingido criticamente."""
        if not getattr(self.jogador, "overvolt", False):
            return

        cx_origem = alvo_origem.x + getattr(alvo_origem, "largura", 28) / 2.0
        cy_origem = alvo_origem.y + getattr(alvo_origem, "altura", 28) / 2.0

        alvos_candidatos = []
        for e in self.inimigos:
            if not getattr(e, "vivo", True) or e is alvo_origem:
                continue
            if getattr(e, "em_fase", False):
                continue
            if getattr(e, "estado", "") in ("morte", ESTADO_MORTE):
                continue
            e_cx = e.x + getattr(e, "largura", 28) / 2.0
            e_cy = e.y + getattr(e, "altura", 28) / 2.0
            dist = distancia(e_cx, e_cy, cx_origem, cy_origem)
            if dist < 220.0:
                alvos_candidatos.append((dist, e, e_cx, e_cy))

        # Ordena por proximidade e seleciona até 4 alvos
        alvos_candidatos.sort(key=lambda item: item[0])
        alvos_chain = alvos_candidatos[:4]

        dano_chain = max(1, dano_base // 2)
        for _, alv, a_cx, a_cy in alvos_chain:
            ret_d = alv.receber_dano(dano_chain)
            dano_efetivo = int(ret_d) if isinstance(ret_d, (int, float)) else dano_chain
            self.dano_total_causado += dano_efetivo
            self.sistema_particulas.emitir_faiscas(a_cx, a_cy, cor=(120, 240, 255), qtd=5)
            if hasattr(self, "config_sistema") and str(self.config_sistema.obter_valor("damage_numbers")).lower() in ("ligado", "true", "1"):
                self.sistema_particulas.emitir_texto_dano(
                    a_cx,
                    alv.y,
                    dano_efetivo,
                    critico=False
                )
            if not getattr(alv, "vivo", True):
                self._registrar_abate_inimigo(alv, mods)

    def _registrar_abate_inimigo(self, inim, mods=None, origem: str = "arma"):
        """Contabiliza o abate de um inimigo, combo, hooks B+, conquistas, score, shrapnel e drops."""
        ger = self._obter_gerenciador_config()
        if mods is None and ger is not None and hasattr(ger, "obter_modificadores"):
            mods = ger.obter_modificadores()

        self.abates += 1
        self.pontos += getattr(inim, "score_valor", 100)
        inim_cx = inim.x + getattr(inim, "largura", 28) / 2.0
        inim_cy = inim.y + getattr(inim, "altura", 28) / 2.0

        sis_combo = self._obter_sistema_combo()
        if sis_combo is not None:
            sis_combo.registrar_abate(origem=origem)

        efeitos = self._obter_efeitos_combate()
        if efeitos is not None:
            efeitos.disparar_ao_abate(self._construir_ctx_combate(mods), inim, fonte=origem)

        sis_cnq = self._obter_sistema_conquistas()
        if sis_cnq is not None and hasattr(sis_cnq, "registrar_evento"):
            notifs_abate = list(sis_cnq.registrar_evento("abate", 1) or [])
            if getattr(inim, "is_elite", False) and not getattr(inim, "superaqueceu", False):
                notifs_abate.extend(sis_cnq.registrar_evento("miniboss_rapido", 1) or [])
            if notifs_abate and ger is not None:
                if hasattr(ger, "sincronizar_recompensas_conquistas"):
                    ger.sincronizar_recompensas_conquistas()
                if hasattr(ger, "salvar_arquivo"):
                    try:
                        save_path = getattr(
                            sys.modules.get("src.cenas.gameplay"),
                            "SAVE_FILE_PATH",
                            SAVE_FILE_PATH,
                        )
                        ger.salvar_arquivo(save_path)
                    except Exception:
                        pass

        # Overvolt (Abordagem A2): descarga elétrica automática a cada 25 abates
        if getattr(self.jogador, "overvolt", False):
            self.jogador.abates_overvolt_contador = getattr(self.jogador, "abates_overvolt_contador", 0) + 1
            if self.jogador.abates_overvolt_contador >= 25:
                self.jogador.abates_overvolt_contador = 0
                self._aplicar_overvolt_chain(inim, 40, mods)

        abate_rapido = False
        if getattr(inim, "is_elite", False):
            self.aplicar_shake(14.0, 0.35)
            self.sistema_particulas.emitir_debris(inim_cx, inim_cy, cor=(255, 215, 0), qtd=16)
            abate_rapido = bool(getattr(inim, "elegivel_abate_rapido", False) or (getattr(inim, "tempo_vida_restante", 0.0) or 0.0) >= 30.0)
            if abate_rapido:
                self.toasts_coleta.append({
                    "texto": "ABATE RÁPIDO (<30s)! ARMA SUPERAQUECIDA + REPARO!",
                    "cor": DOURADO,
                    "x": inim_cx,
                    "y": inim.y - 24,
                    "tempo": 2.4,
                    "tempo_max": 2.4
                })
            if getattr(self.jogador, "bios_modding", False):
                for arma_rec in (getattr(self.jogador, "arma_especial", None), getattr(self.jogador, "arma_especial_secundaria", None)):
                    if arma_rec is not None and hasattr(arma_rec, "municao_max"):
                        arma_rec.municao_atual = min(arma_rec.municao_max, arma_rec.municao_atual + max(1, int(round(arma_rec.municao_max * 0.15))))

        # Estilhaços Low-Poly (Qualidade Gráfica Baixa)
        if getattr(mods, "graficos_shrapnel", False):
            for ang_sh in (0.0, 1.5708, 3.14159, 4.71239):
                spd_sh = random.uniform(220.0, 300.0)
                vx_sh = math.cos(ang_sh + random.uniform(-0.2, 0.2)) * spd_sh
                vy_sh = math.sin(ang_sh + random.uniform(-0.2, 0.2)) * spd_sh
                self.projeteis.append(Projetil(
                    x=inim_cx - 3.0, y=inim_cy - 3.0, vx=vx_sh, vy=vy_sh, dano=12,
                    tempo_vida=0.45, dono="jogador", largura=6, altura=6, cor=(255, 255, 255),
                    perfurante=True
                ))

        is_boss_lutando = (self.chefe_final is not None and self.chefe_final.vivo)
        novos_drops = self.sistema_drops.gerar_drop_morte_inimigo(
            inim.x + getattr(inim, "largura", 28) / 2.0,
            inim.y + getattr(inim, "altura", 28) / 2.0,
            bonus_chance_drop=getattr(mods, "drop_chance_bonus", 0.0) if mods else 0.0,
            mult_chance_drop=getattr(mods, "drop_chance_mult", 1.0) if mods else 1.0,
            xp_base=getattr(inim, "xp_valor", 5),
            loot_enriquecido=getattr(mods, "loot_enriquecido", False) or getattr(inim, "loot_enriquecido", False),
            chance_arma=getattr(inim, "chance_drop_arma", None),
            chance_equipamento=getattr(inim, "chance_drop_equipamento", None),
            is_elite=getattr(inim, "is_elite", False),
            modo_boss=is_boss_lutando,
            abate_rapido=abate_rapido
        )
        if getattr(inim, "is_elite", False) and novos_drops and getattr(self.jogador, "vivo", False):
            mult_drops = getattr(mods, "drops_valor_mult", 1.0) if mods else 1.0
            mult_xp = getattr(mods, "xp_ganho_mult", 1.0) if mods else 1.0
            xp_auto = 0
            for d in novos_drops:
                if getattr(d, "tipo", "") == "xp" and not getattr(d, "coletado", False):
                    d.coletado = True
                    d.ativo = False
                    if d in self.sistema_drops.drops:
                        self.sistema_drops.drops.remove(d)
                    xp_auto += max(1, int(round(d.valor * mult_drops)))
            if xp_auto > 0 and hasattr(self.jogador, "ganhar_xp"):
                self.jogador.ganhar_xp(xp_auto, mult_xp=mult_xp)
                self.sistema_particulas.emitir_burst_drop(inim_cx, inim_cy, tipo="xp")
                if hasattr(self, "sistema_audio") and self.sistema_audio is not None:
                    self.sistema_audio.tocar_sfx("sfx_pickup_xp")

    def _disparar_acao_dash(
        self,
        dx_d: float,
        dy_d: float,
        centro_jogador_x: float,
        centro_jogador_y: float,
        mods,
    ) -> bool:
        """Executa o Dash e notifica partículas, freeze e Pipeline B+ (disparar_ao_dash)."""
        if not self.jogador.iniciar_dash(dx_d, dy_d, mods=mods):
            return False
        if hasattr(self.sistema_particulas, "adicionar_onda_dash"):
            self.sistema_particulas.adicionar_onda_dash(centro_jogador_x, centro_jogador_y)
        if getattr(self.jogador, "dash_stutter_trigger", False):
            self.jogador.dash_stutter_trigger = False
            self.arena_freeze_timer = max(self.arena_freeze_timer, 0.15)
        efeitos = self._obter_efeitos_combate()
        if efeitos is not None:
            dest_x = self.jogador.x + self.jogador.largura / 2.0
            dest_y = self.jogador.y + self.jogador.altura / 2.0
            efeitos.disparar_ao_dash(
                self._construir_ctx_combate(mods),
                (centro_jogador_x, centro_jogador_y),
                (dest_x, dest_y),
            )
        return True

    def _executar_acao_parry(
        self,
        arma_melee,
        centro_jogador_x: float,
        centro_jogador_y: float,
        ang_mira: float,
        mods,
    ) -> bool:
        """Executa Quick-Parry (RMB/E) com cooldown obrigatório e checagem imediata no frame 0."""
        if arma_melee is None or not hasattr(arma_melee, "executar_parry"):
            return False
        parry_ef = getattr(mods, "parry_efeito", "padrao") if mods else "padrao"
        cd_override = (
            5.5
            if parry_ef == "firewall_estatico"
            else (6.5 if parry_ef == "ventoinha_360" else None)
        )
        if not arma_melee.executar_parry(
            ang_mira, punir_whiff=True, cooldown_override=cd_override
        ):
            return False
        if hasattr(self, "sistema_audio") and self.sistema_audio is not None:
            self.sistema_audio.tocar_sfx("sfx_ataque_melee", pitch_aleatorio=True)
        self._processar_parry_ativo(
            arma_melee, centro_jogador_x, centro_jogador_y, angulo_mira=ang_mira
        )
        return True

    def _despachar_tiros_arma(self, arma, novos_tiros: list, mods) -> None:
        """Registra projéteis gerados, aplica efeitos legados e dispara ao_disparo sem recursão."""
        if not novos_tiros:
            return
        self.projeteis.extend(novos_tiros)
        self._aplicar_efeitos_disparo_extras(novos_tiros, mods)
        efeitos = self._obter_efeitos_combate()
        if efeitos is not None:
            extras = efeitos.disparar_ao_disparo(
                self._construir_ctx_combate(mods, profundidade_recursao=0),
                arma,
                novos_tiros,
            )
            if extras:
                # Réplicas (sombra_espelho / gatilho_duplo / canhoes_perimetrais) nunca re-entram em ao_disparo
                self.projeteis.extend(extras)

    def _processar_arma_continua(
        self,
        arma,
        dt: float,
        segurando_gatilho: bool,
        centro_jogador_x: float,
        centro_jogador_y: float,
        alvo_x: float,
        alvo_y: float,
        crit_chance: float,
        crit_mult: float,
        mult_dano: float,
        mods,
    ) -> bool:
        """Atualiza armas contínuas (RifleArco, LancaChamas) e processa ticks de dano/status/abates."""
        if arma is None or not hasattr(arma, "atualizar_fluxo"):
            return False
        eventos_fluxo = arma.atualizar_fluxo(
            dt,
            segurando_gatilho=segurando_gatilho,
            origem_x=centro_jogador_x,
            origem_y=centro_jogador_y,
            destino_x=alvo_x,
            destino_y=alvo_y,
            inimigos=self.inimigos,
        )
        if not eventos_fluxo:
            return bool(segurando_gatilho)

        efeitos = self._obter_efeitos_combate()
        ctx = self._construir_ctx_combate(mods) if efeitos is not None else None
        show_dmg = (
            hasattr(self, "config_sistema")
            and self.config_sistema is not None
            and str(self.config_sistema.obter_valor("damage_numbers")).lower()
            in ("ligado", "true", "1")
        )
        for ev in eventos_fluxo:
            alvo = ev.get("alvo")
            if alvo is None or not getattr(alvo, "vivo", True):
                continue
            dano_base_ev = float(ev.get("dano", getattr(arma, "dano", 10)))
            bonus_crit = float(ev.get("bonus_crit_overvolt", 0.0))
            crit_eff = min(
                1.0,
                crit_chance
                + (bonus_crit if getattr(self.jogador, "overvolt", False) else 0.0),
            )
            is_crit = crit_eff > 0.0 and random.random() < crit_eff
            dano_hit = max(
                1,
                int(round(dano_base_ev * mult_dano * (crit_mult if is_crit else 1.0))),
            )
            if efeitos is not None and ctx is not None:
                res_imp = efeitos.disparar_ao_impacto(ctx, alvo, dano_hit, fonte=arma)
                if res_imp:
                    if res_imp.get("critico_forcado") and not is_crit:
                        is_crit = True
                        dano_hit = max(1, int(round(dano_hit * crit_mult)))
                    if "dano_mult" in res_imp:
                        dano_hit = max(1, int(round(dano_hit * float(res_imp["dano_mult"]))))
                    if "dano_extra" in res_imp:
                        dano_hit += int(res_imp["dano_extra"])

            ret_d = alvo.receber_dano(
                dano_hit, origem_x=centro_jogador_x, origem_y=centro_jogador_y
            )
            dano_ef = int(ret_d) if isinstance(ret_d, (int, float)) else dano_hit
            self.dano_total_causado += dano_ef

            slow_t = float(ev.get("aplicar_slow", 0.0))
            if slow_t > 0.0 and not getattr(alvo, "is_boss", False):
                alvo.slow_timer = max(getattr(alvo, "slow_timer", 0.0), slow_t)
                alvo.slow_fator = min(getattr(alvo, "slow_fator", 1.0), 0.65)
            queim_t = float(ev.get("aplicar_queimadura", 0.0))
            if queim_t > 0.0:
                alvo.queimadura_timer = max(
                    getattr(alvo, "queimadura_timer", 0.0), queim_t
                )

            if show_dmg or is_crit:
                self.sistema_particulas.emitir_texto_dano(
                    alvo.x + getattr(alvo, "largura", 28) / 2.0,
                    alvo.y,
                    dano_ef,
                    critico=is_crit,
                )
            if is_crit:
                self._aplicar_overvolt_chain(alvo, dano_ef, mods)
            if not getattr(alvo, "vivo", True):
                self._registrar_abate_inimigo(alvo, mods, origem="arma")
        return True

    def _disparar_arma_nao_melee(
        self,
        arma,
        centro_jogador_x: float,
        centro_jogador_y: float,
        spawn_origem_x: float,
        spawn_origem_y: float,
        alvo_x: float,
        alvo_y: float,
        mods,
        hitbox_mult: float,
        mult_dano: float,
    ) -> bool:
        """Dispara Railgun ou arma balística (Slot 2 / Slot 3), aplicando escalas e ao_disparo."""
        if arma is None or not self.jogador.vivo:
            return False
        if isinstance(arma, Railgun) or "railgun" in getattr(arma, "nome", "").lower():
            if hasattr(arma, "pode_atirar") and arma.pode_atirar():
                return self._executar_disparo_railgun(
                    arma,
                    centro_jogador_x,
                    centro_jogador_y,
                    alvo_x,
                    alvo_y,
                    mods=mods,
                    hitbox_mult=hitbox_mult,
                    mult_dano_buff=mult_dano,
                )
            return False

        if hasattr(arma, "pode_atirar") and arma.pode_atirar() and hasattr(arma, "disparar"):
            novos_tiros = arma.disparar(spawn_origem_x, spawn_origem_y, alvo_x, alvo_y)
            if novos_tiros:
                eh_slot2 = isinstance(arma, Pistola) or getattr(arma, "slot", None) == 2
                for p in novos_tiros:
                    if hitbox_mult != 1.0:
                        p.largura = max(2, int(round(p.largura * hitbox_mult)))
                        p.altura = max(2, int(round(p.altura * hitbox_mult)))
                        p.width = p.largura
                        p.height = p.altura
                    if mult_dano != 1.0:
                        p.dano = max(1, math.ceil(p.dano * mult_dano))
                    if eh_slot2 and getattr(self.jogador, "controles_tanque", False):
                        p.perfuracoes_restantes = int(getattr(p, "perfuracoes_restantes", 0)) + 1
                if (
                    eh_slot2
                    and getattr(self.jogador, "controles_tanque", False)
                    and getattr(self.jogador, "tanque_parado", False)
                ):
                    arma.tempo_recarga_restante *= 0.80
                self._despachar_tiros_arma(arma, novos_tiros, mods)
                return True
        return False

    def _atualizar_disparos_jogador(
        self,
        dt: float,
        mods,
        hitbox_mult: float,
        mult_dano_buff: float,
    ) -> tuple[float, float, float, float]:
        """Processa pulso overdrive, mira, auto-fire, latencia_ping, dash, parry, armas contínuas/balísticas e BIOS dual-wield."""
        centro_jogador_x = self.jogador.x + self.jogador.largura / 2.0
        centro_jogador_y = self.jogador.y + self.jogador.altura / 2.0

        # Fix 12.3: Pulso de Choque do Overdrive Dash (keybinds_overdrive_dash)
        if getattr(self.jogador, "overdrive_pulse_trigger", False):
            self.jogador.overdrive_pulse_trigger = False
            self.sistema_particulas.emitir_onda_choque(centro_jogador_x, centro_jogador_y, raio_max=110.0, cor=(100, 220, 255))
            for inim in list(self.inimigos):
                if inim == self.chefe_final or getattr(inim, "is_boss", False):
                    continue
                if getattr(inim, "vivo", True) and not getattr(inim, "em_fase", False):
                    i_cx = inim.x + getattr(inim, "largura", 28) / 2.0
                    i_cy = inim.y + getattr(inim, "altura", 28) / 2.0
                    if distancia(i_cx, i_cy, centro_jogador_x, centro_jogador_y) < 110.0:
                        dir_p_x, dir_p_y = vetor_direcao(centro_jogador_x, centro_jogador_y, i_cx, i_cy)
                        inim.x += dir_p_x * 32.0
                        inim.y += dir_p_y * 32.0
                        self._clamp_entidade_arena(inim)
                        ret_d = inim.receber_dano(15, origem_x=centro_jogador_x, origem_y=centro_jogador_y, dir_ataque=(dir_p_x, dir_p_y))
                        dano_aplicado = int(ret_d) if isinstance(ret_d, (int, float)) else 15
                        self.dano_total_causado += dano_aplicado
                        if hasattr(self, "config_sistema") and str(self.config_sistema.obter_valor("damage_numbers")).lower() in ("ligado", "true", "1"):
                            self.sistema_particulas.emitir_texto_dano(
                                inim.x + getattr(inim, "largura", 28) / 2.0,
                                inim.y,
                                dano_aplicado,
                                critico=False
                            )
                        if not inim.vivo:
                            self._registrar_abate_inimigo(inim, mods)

        # Posição virtual do cursor convertida para espaço do mundo (com suporte a zoom e presets)
        val_keybinds = str(self.config_sistema.obter_valor("keybinds")).lower() if hasattr(self, "config_sistema") and self.config_sistema else "padrao"
        is_uma_mao = (val_keybinds == "uma_mao")
        try:
            mx_raw, my_raw = self.mouse.get_position()
            mx, my = mx_raw, my_raw
            if val_keybinds == "pesadelo":
                my = ALTURA_TELA - my
        except Exception:
            mx_raw, my_raw = (LARGURA_TELA / 2.0, ALTURA_TELA / 2.0)
            mx, my = mx_raw, my_raw

        # Input buffer e Auto-Fire
        val_autofire = str(self.config_sistema.obter_valor("auto_fire")).lower() if hasattr(self, "config_sistema") and self.config_sistema else "ligado"
        autofire_desligado = val_autofire in ("desligado", "0", "false")

        if is_uma_mao:
            dir_mov = getattr(self.jogador, "dir_movimento", (0.0, -1.0))
            dir_mira_x, dir_mira_y = float(dir_mov[0]), float(dir_mov[1])
            norm_m = math.hypot(dir_mira_x, dir_mira_y)
            if norm_m > 1e-5:
                dir_mira_x /= norm_m
                dir_mira_y /= norm_m
            else:
                dir_mira_x, dir_mira_y = 0.0, -1.0
            mouse_mundo_x = centro_jogador_x + dir_mira_x * 160.0
            mouse_mundo_y = centro_jogador_y + dir_mira_y * 160.0

            kb_down = bool(
                self.teclado is not None and hasattr(self.teclado, "key_down") and (
                    self.teclado.key_down("SPACE") or self.teclado.key_down("f") or
                    self.teclado.key_down("F") or self.teclado.key_down("ENTER")
                )
            )
            kb_pressed = bool(
                self.teclado is not None and hasattr(self.teclado, "key_pressed") and (
                    self.teclado.key_pressed("SPACE") or self.teclado.key_pressed("f") or
                    self.teclado.key_pressed("F") or self.teclado.key_pressed("ENTER")
                )
            )
            btn1_down = kb_down
            btn1_pressed = kb_pressed if autofire_desligado else True
        else:
            mouse_mundo_x, mouse_mundo_y = self._obter_mouse_mundo(mx, my)
            btn1_down = bool(self.mouse.button_down(1)) if (self.mouse is not None and hasattr(self.mouse, "button_down")) else False
            if self.mouse is not None and hasattr(self.mouse, "button_pressed"):
                btn1_pressed = bool(self.mouse.button_pressed(1))
            elif self.mouse is not None and hasattr(self.mouse, "get_pressed_buttons"):
                pressed_btns = self.mouse.get_pressed_buttons()
                btn1_pressed = bool(pressed_btns[0]) if pressed_btns else False
            elif pygame.mouse.get_focused() and len(pygame.mouse.get_pressed()) > 0:
                btn1_pressed = bool(pygame.mouse.get_pressed()[0])
            else:
                btn1_pressed = False

            if getattr(self, "_aguardando_soltar_lmb", False):
                if not btn1_pressed or btn1_down:
                    self._aguardando_soltar_lmb = False
                else:
                    btn1_pressed = False
                    btn1_down = False

        # Toggle de Auto-Fire na tecla 'F' quando auto_fire == "ligado"
        if not is_uma_mao and not autofire_desligado and self.teclado is not None and hasattr(self.teclado, "key_down"):
            if self.teclado.key_down("f") or self.teclado.key_down("F"):
                self.auto_fire_toggle_ativo = not getattr(self, "auto_fire_toggle_ativo", False)
                self.toasts_coleta.append({
                    "texto": "AUTO-FIRE: ON" if self.auto_fire_toggle_ativo else "AUTO-FIRE: OFF",
                    "cor": AZUL_CIANO if self.auto_fire_toggle_ativo else CINZA_TEXTO if "CINZA_TEXTO" in globals() else (180, 190, 205),
                    "x": centro_jogador_x,
                    "y": self.jogador.y - 14,
                    "tempo": 1.1,
                    "tempo_max": 1.1
                })

        if autofire_desligado:
            self.auto_fire_toggle_ativo = False
            disparar_agora = btn1_down
            self.buffer_tiro = 0.0
        else:
            if btn1_pressed:
                self.buffer_tiro = 0.15
            else:
                self.buffer_tiro = max(0.0, self.buffer_tiro - dt)
            disparar_agora = (self.buffer_tiro > 0.0) or (not is_uma_mao and getattr(self, "auto_fire_toggle_ativo", False))

        # Multiplicadores do SistemaCombo + trava de Garbage Collector
        sis_combo = self._obter_sistema_combo()
        combo_mults = sis_combo.obter_multiplicadores() if sis_combo is not None else {"dano_mult": 1.0, "cadencia_mult": 1.0}
        combo_dano_mult = float(combo_mults.get("dano_mult", 1.0))
        combo_cadencia_mult = float(combo_mults.get("cadencia_mult", 1.0))
        mult_dano_efetivo = mult_dano_buff * combo_dano_mult

        arma_ativa = self.jogador.obter_arma_ativa() if self.jogador.vivo else None
        if combo_cadencia_mult > 1.0 and arma_ativa is not None and hasattr(arma_ativa, "tempo_recarga_restante"):
            arma_ativa.tempo_recarga_restante = max(
                0.0, arma_ativa.tempo_recarga_restante - (combo_cadencia_mult - 1.0) * dt
            )

        efeitos = self._obter_efeitos_combate()
        efeito_gc = efeitos.obter_efeito("garbage_collector") if efeitos is not None else None
        if efeito_gc is not None and getattr(efeito_gc, "disparos_travados", False):
            disparar_agora = False

        efeito_ping = efeitos.obter_efeito("latencia_ping") if efeitos is not None else None

        crit_chance = getattr(mods, "critico_chance", 0.0) if mods else 0.0
        crit_mult = getattr(mods, "critico_mult", 2.0) if mods else 2.0
        if getattr(self.jogador, "overvolt", False):
            crit_chance = min(1.0, crit_chance + 0.30)
            crit_mult = max(crit_mult, 2.0)

        if not is_uma_mao:
            dir_mira_x, dir_mira_y = vetor_direcao(centro_jogador_x, centro_jogador_y, mouse_mundo_x, mouse_mundo_y)
            if dir_mira_x == 0.0 and dir_mira_y == 0.0:
                dir_mira_x = 1.0
        ang_mira = math.atan2(dir_mira_y, dir_mira_x)
        spawn_origem_x = centro_jogador_x + dir_mira_x * 24.0
        spawn_origem_y = centro_jogador_y + dir_mira_y * 24.0

        arma_melee_slot1 = self._obter_arma_melee()
        if arma_melee_slot1 is not None:
            if hasattr(arma_melee_slot1, "atualizar"):
                arma_melee_slot1.atualizar(dt)
            if getattr(arma_melee_slot1, "parry_ativo", False) and self.jogador.vivo:
                self._processar_parry_ativo(arma_melee_slot1, centro_jogador_x, centro_jogador_y)

        # Consome ações atrasadas por latencia_ping (~80ms)
        if efeito_ping is not None and self.jogador.vivo:
            for acao in efeito_ping.consumir_acoes_prontas(dt):
                tipo_ac = acao.get("tipo")
                pl = acao.get("payload") or {}
                if tipo_ac == "dash":
                    self._disparar_acao_dash(
                        pl.get("dx", 0.0), pl.get("dy", 0.0),
                        centro_jogador_x, centro_jogador_y, mods
                    )
                elif tipo_ac == "parry":
                    self._executar_acao_parry(
                        pl.get("arma", arma_melee_slot1),
                        centro_jogador_x, centro_jogador_y,
                        acao.get("ang_mira", ang_mira), mods
                    )
                elif tipo_ac == "melee":
                    arma_m = pl.get("arma", arma_melee_slot1)
                    if arma_m is not None and hasattr(arma_m, "pode_atirar") and arma_m.pode_atirar():
                        self._executar_golpe_melee(
                            arma_m,
                            centro_jogador_x, centro_jogador_y,
                            pl.get("alvo_x", mouse_mundo_x), pl.get("alvo_y", mouse_mundo_y),
                            crit_chance, crit_mult, mult_dano_buff, mods
                        )
                elif tipo_ac == "disparo":
                    arma_p = pl.get("arma", arma_ativa)
                    ax_p = pl.get("alvo_x", mouse_mundo_x)
                    ay_p = pl.get("alvo_y", mouse_mundo_y)
                    dx_p, dy_p = vetor_direcao(centro_jogador_x, centro_jogador_y, ax_p, ay_p)
                    if dx_p == 0.0 and dy_p == 0.0:
                        dx_p = 1.0
                    if getattr(arma_p, "eh_continua", False):
                        self._processar_arma_continua(
                            arma_p, dt, True,
                            centro_jogador_x, centro_jogador_y,
                            ax_p, ay_p,
                            crit_chance, crit_mult, mult_dano_efetivo, mods
                        )
                    else:
                        self._disparar_arma_nao_melee(
                            arma_p,
                            centro_jogador_x, centro_jogador_y,
                            centro_jogador_x + dx_p * 24.0, centro_jogador_y + dy_p * 24.0,
                            ax_p, ay_p, mods, hitbox_mult, mult_dano_efetivo
                        )

        # Dash Direcional Permanente: SPACE/LSHIFT no modo padrão; LSHIFT em uma_mao
        if self.jogador.vivo and self.teclado is not None and hasattr(self.teclado, "key_down"):
            dash_press = bool(
                self.teclado.key_down("LSHIFT")
                if is_uma_mao
                else (self.teclado.key_down("SPACE") or self.teclado.key_down("LSHIFT"))
            )
            if dash_press:
                dx_d, dy_d = getattr(self.jogador, "dir_movimento_atual", (0.0, 0.0))
                if efeito_ping is not None:
                    efeito_ping.agendar_acao(
                        "dash", {"dx": dx_d, "dy": dy_d},
                        (centro_jogador_x, centro_jogador_y), ang_mira
                    )
                else:
                    self._disparar_acao_dash(dx_d, dy_d, centro_jogador_x, centro_jogador_y, mods)

        # Disparo primário (LMB)
        if self.jogador.vivo and arma_ativa is not None:
            eh_melee_ativa = isinstance(arma_ativa, Melee) or getattr(arma_ativa, "slot", None) == 1
            if getattr(arma_ativa, "eh_continua", False):
                if efeito_ping is not None:
                    if disparar_agora:
                        efeito_ping.agendar_acao(
                            "disparo",
                            {"arma": arma_ativa, "alvo_x": mouse_mundo_x, "alvo_y": mouse_mundo_y},
                            (centro_jogador_x, centro_jogador_y),
                            ang_mira,
                        )
                        self.buffer_tiro = 0.0
                    else:
                        self._processar_arma_continua(
                            arma_ativa, dt, False,
                            centro_jogador_x, centro_jogador_y,
                            mouse_mundo_x, mouse_mundo_y,
                            crit_chance, crit_mult, mult_dano_efetivo, mods
                        )
                else:
                    self._processar_arma_continua(
                        arma_ativa, dt, disparar_agora,
                        centro_jogador_x, centro_jogador_y,
                        mouse_mundo_x, mouse_mundo_y,
                        crit_chance, crit_mult, mult_dano_efetivo, mods
                    )
            elif disparar_agora:
                if eh_melee_ativa:
                    if hasattr(arma_ativa, "pode_atirar") and arma_ativa.pode_atirar():
                        if efeito_ping is not None:
                            efeito_ping.agendar_acao(
                                "melee",
                                {"arma": arma_ativa, "alvo_x": mouse_mundo_x, "alvo_y": mouse_mundo_y},
                                (centro_jogador_x, centro_jogador_y),
                                ang_mira,
                            )
                            self.buffer_tiro = 0.0
                        else:
                            self._executar_golpe_melee(
                                arma_ativa,
                                centro_jogador_x, centro_jogador_y,
                                mouse_mundo_x, mouse_mundo_y,
                                crit_chance, crit_mult, mult_dano_buff, mods
                            )
                            self.buffer_tiro = 0.0
                else:
                    if hasattr(arma_ativa, "pode_atirar") and arma_ativa.pode_atirar():
                        if efeito_ping is not None:
                            efeito_ping.agendar_acao(
                                "disparo",
                                {"arma": arma_ativa, "alvo_x": mouse_mundo_x, "alvo_y": mouse_mundo_y},
                                (centro_jogador_x, centro_jogador_y),
                                ang_mira,
                            )
                            self.buffer_tiro = 0.0
                        elif self._disparar_arma_nao_melee(
                            arma_ativa,
                            centro_jogador_x, centro_jogador_y,
                            spawn_origem_x, spawn_origem_y,
                            mouse_mundo_x, mouse_mundo_y,
                            mods, hitbox_mult, mult_dano_efetivo
                        ):
                            self.buffer_tiro = 0.0

        # Dual-Wield (BIOS Modding - B1): LMB dispara também a outra Arma Especial equipada (inclui armas contínuas)
        if getattr(self.jogador, "bios_modding", False) and self.jogador.vivo:
            arma_esp = None
            if getattr(self.jogador, "slot_ativo", None) == 3:
                if getattr(self.jogador, "arma_especial_secundaria", None) is not None and self.jogador.arma_especial_secundaria is not arma_ativa:
                    arma_esp = self.jogador.arma_especial_secundaria
                elif getattr(self.jogador, "arma_especial", None) is not None and self.jogador.arma_especial is not arma_ativa:
                    arma_esp = self.jogador.arma_especial
            elif getattr(self.jogador, "arma_especial", None) is not None and self.jogador.arma_especial is not arma_ativa:
                arma_esp = self.jogador.arma_especial

            if arma_esp is not None:
                if getattr(arma_esp, "eh_continua", False):
                    self._processar_arma_continua(
                        arma_esp, dt, disparar_agora,
                        centro_jogador_x, centro_jogador_y,
                        mouse_mundo_x, mouse_mundo_y,
                        crit_chance, crit_mult, mult_dano_efetivo, mods
                    )
                elif disparar_agora:
                    if efeito_ping is not None:
                        if hasattr(arma_esp, "pode_atirar") and arma_esp.pode_atirar():
                            efeito_ping.agendar_acao(
                                "disparo",
                                {"arma": arma_esp, "alvo_x": mouse_mundo_x, "alvo_y": mouse_mundo_y},
                                (centro_jogador_x, centro_jogador_y),
                                ang_mira,
                            )
                    else:
                        self._disparar_arma_nao_melee(
                            arma_esp,
                            centro_jogador_x, centro_jogador_y,
                            spawn_origem_x, spawn_origem_y,
                            mouse_mundo_x, mouse_mundo_y,
                            mods, hitbox_mult, mult_dano_efetivo
                        )

        # Parry Rápido exclusivo (sem trocar de arma): tecla 'E' ou Botão Direito (RMB)
        if self.jogador.vivo and arma_melee_slot1 is not None and hasattr(arma_melee_slot1, "pode_atirar") and arma_melee_slot1.pode_atirar():
            tecla_e_down = bool(
                self.teclado is not None and hasattr(self.teclado, "key_down") and (
                    self.teclado.key_down("e") or self.teclado.key_down("E")
                )
            )
            rmb_down = False
            if not is_uma_mao and self.mouse is not None:
                if hasattr(self.mouse, "button_down"):
                    rmb_down = bool(self.mouse.button_down(3))
                elif hasattr(self.mouse, "is_button_down"):
                    rmb_down = bool(self.mouse.is_button_down(3))
            if tecla_e_down or rmb_down:
                if efeito_ping is not None:
                    efeito_ping.agendar_acao(
                        "parry",
                        {"arma": arma_melee_slot1},
                        (centro_jogador_x, centro_jogador_y),
                        ang_mira,
                    )
                else:
                    self._executar_acao_parry(
                        arma_melee_slot1,
                        centro_jogador_x, centro_jogador_y,
                        ang_mira, mods
                    )
        return centro_jogador_x, centro_jogador_y, crit_chance, crit_mult

    def _atualizar_fisica_projeteis(
        self,
        dt: float,
        mods,
        cutscene_congelada: bool,
        centro_jogador_x: float,
        centro_jogador_y: float,
    ):
        """Atualiza refração VSync tear, deslocamento de projéteis e zonas de fogo/plasma/estase/gelo."""
        if not cutscene_congelada:
            # Sincronização Vertical (Desligado): Linha de Rasgo divide tiros do jogador (0.75x) e desvia tiros inimigos (±12°)
            if getattr(mods, "vsync_tear_refraction", False):
                self.vsync_tear_y = (getattr(self, "vsync_tear_y", 0.0) + 80.0 * dt) % ALTURA_TELA
                proj_clones = []
                ang_split = math.radians(6.0)
                cos_pos, sin_pos = math.cos(ang_split), math.sin(ang_split)
                cos_neg, sin_neg = math.cos(-ang_split), math.sin(-ang_split)
                ang_desvio = math.radians(12.0)
                for proj in self.projeteis:
                    dono_p = getattr(proj, "dono", "jogador")
                    tela_y = proj.y - self.camera.y
                    if abs(tela_y - self.vsync_tear_y) >= 18.0:
                        continue
                    if (
                        dono_p == "jogador"
                        and not getattr(proj, "ja_dividido_tear", False)
                        and not getattr(proj, "split_done", False)
                    ):
                        proj.ja_dividido_tear = True
                        proj.split_done = True
                        proj.dano = max(1, int(round(proj.dano * 0.75)))
                        orig_vx, orig_vy = proj.vx, proj.vy
                        orig_dx, orig_dy = proj.dir_x, proj.dir_y
                        proj.dir_x = orig_dx * cos_neg - orig_dy * sin_neg
                        proj.dir_y = orig_dx * sin_neg + orig_dy * cos_neg
                        vx_d = orig_vx * cos_pos - orig_vy * sin_pos
                        vy_d = orig_vx * sin_pos + orig_vy * cos_pos
                        clone = proj.clonar(vx=vx_d, vy=vy_d, cor=(56, 189, 248))
                        clone.ja_dividido_tear = True
                        clone.split_done = True
                        proj_clones.append(clone)
                        self.sistema_particulas.emitir_faiscas(
                            proj.x + getattr(proj, "largura", 6) / 2.0,
                            proj.y + getattr(proj, "altura", 6) / 2.0,
                            dir_x=proj.dir_x,
                            dir_y=proj.dir_y,
                            cor=(56, 189, 248),
                            qtd=5
                        )
                    elif dono_p == "inimigo" and not getattr(proj, "ja_desviado_tear", False):
                        proj.ja_desviado_tear = True
                        sinal = -1.0 if (id(proj) % 2 == 0) else 1.0
                        cos_d = math.cos(ang_desvio * sinal)
                        sin_d = math.sin(ang_desvio * sinal)
                        dx_o, dy_o = getattr(proj, "dir_x", 0.0), getattr(proj, "dir_y", 0.0)
                        proj.dir_x = dx_o * cos_d - dy_o * sin_d
                        proj.dir_y = dx_o * sin_d + dy_o * cos_d
                if proj_clones:
                    self.projeteis.extend(proj_clones)

            for proj in self.projeteis:
                if getattr(proj, "dono", "jogador") == "inimigo" and self.arena_freeze_timer > 0.0:
                    continue
                proj._x_ant = proj.x
                proj._y_ant = proj.y
                proj.update(dt)
                if getattr(proj, "superaquecido", False) and proj.ativo:
                    self.sistema_particulas.emitir_faiscas(
                        proj.x + proj.largura / 2.0,
                        proj.y + proj.altura / 2.0,
                        dir_x=-proj.dir_x,
                        dir_y=-proj.dir_y,
                        cor=(255, 120, 30),
                        qtd=1
                    )
                # Desativa projéteis que saíram muito longe dos limites da arena
                if (proj.x < -100 or proj.x > self.largura_arena + 100 or
                    proj.y < -100 or proj.y > self.altura_arena + 100):
                    proj.ativo = False

            # Atualiza Zonas de Fogo (Foguetes), Trilhas de Plasma (Railgun), Zonas de Estase (Drone Suporte) e Poças de Gelo (Geladeira)
            if self.aura_cura_timer > 0.0:
                self.aura_cura_timer = max(0.0, self.aura_cura_timer - dt)

            for zf in self.zonas_fogo:
                zf["tempo"] -= dt
                zf["tick"] = zf.get("tick", 0.0) + dt
                if zf["tick"] >= 0.35:
                    zf["tick"] = 0.0
                    for inim_f in self.inimigos:
                        if getattr(inim_f, "vivo", True) and not getattr(inim_f, "em_fase", False):
                            icx = inim_f.x + getattr(inim_f, "largura", 28) / 2.0
                            icy = inim_f.y + getattr(inim_f, "altura", 28) / 2.0
                            if distancia(icx, icy, zf["x"], zf["y"]) <= zf["raio"]:
                                inim_f.receber_dano(10)
                                if not inim_f.vivo:
                                    self._registrar_abate_inimigo(inim_f, mods)
            self.zonas_fogo = [z for z in self.zonas_fogo if z["tempo"] > 0.0]

            for tp in self.trilhas_plasma:
                tp["tempo"] -= dt
            self.trilhas_plasma = [t for t in self.trilhas_plasma if t["tempo"] > 0.0]

            for ze in self.zonas_estase:
                ze["tempo"] -= dt
                for inim_e in self.inimigos:
                    if getattr(inim_e, "vivo", True):
                        icx = inim_e.x + getattr(inim_e, "largura", 28) / 2.0
                        icy = inim_e.y + getattr(inim_e, "altura", 28) / 2.0
                        if distancia(icx, icy, ze["x"], ze["y"]) <= ze["raio"]:
                            inim_e.slow_timer = max(getattr(inim_e, "slow_timer", 0.0), 0.35)
                            inim_e.slow_fator = 0.50
                            inim_e.vulneravel_estase_timer = 0.35
            self.zonas_estase = [z for z in self.zonas_estase if z["tempo"] > 0.0]

            for pg in self.pocas_gelo:
                pg["tempo"] -= dt
                if distancia(centro_jogador_x, centro_jogador_y, pg["x"], pg["y"]) <= pg["raio"]:
                    self.jogador.x -= getattr(self.jogador, "ultima_dir_dx", 0.0) * 45.0 * dt
                    self.jogador.y -= getattr(self.jogador, "ultima_dir_dy", 0.0) * 45.0 * dt
                    self._clamp_entidade_arena(self.jogador)
            self.pocas_gelo = [p for p in self.pocas_gelo if p["tempo"] > 0.0]

    def _atualizar_projeteis_e_colisoes(
        self,
        dt: float,
        mods,
        cutscene_congelada: bool,
        centro_jogador_x: float,
        centro_jogador_y: float,
        crit_chance: float,
        crit_mult: float,
        val_ilum: bool,
        mult_dano_inim_base: float,
    ):
        """Processa sub-stepping de colisões de projéteis, explosões, parry AoE, fogo amigo e limpeza de entidades."""
        mult_explosivo = getattr(mods, "dano_explosivos_mult", 1.0) if mods else 1.0
        auto_dano = getattr(mods, "auto_dano", False) if mods else False
        efeitos = self._obter_efeitos_combate()
        ctx_combate = self._construir_ctx_combate(mods) if efeitos is not None else None
        efeito_ping = efeitos.obter_efeito("latencia_ping") if efeitos is not None else None
        if efeito_ping is not None:
            pos_hb = efeito_ping.obter_pos_hitbox_atrasada((centro_jogador_x, centro_jogador_y))
            hb_jog_x = pos_hb[0] - self.jogador.largura / 2.0
            hb_jog_y = pos_hb[1] - self.jogador.altura / 2.0
        else:
            hb_jog_x = self.jogador.x
            hb_jog_y = self.jogador.y

        for proj in list(self.projeteis):
            if cutscene_congelada:
                break
            if not proj.ativo and not getattr(proj, "requer_detonacao_ao_expirar", False):
                continue

            vel = float(getattr(proj, "velocidade", 0.0))
            largura_proj = max(1.0, float(getattr(proj, "largura", 8)))
            dist_frame = vel * dt

            x_fim = proj.x
            y_fim = proj.y
            x_ini = getattr(proj, "_x_ant", x_fim - getattr(proj, "dir_x", 0.0) * dist_frame)
            y_ini = getattr(proj, "_y_ant", y_fim - getattr(proj, "dir_y", 0.0) * dist_frame)

            if dist_frame > largura_proj:
                num_passos = max(1, int(math.ceil(dist_frame / largura_proj)))
                passos = [
                    (x_ini + (x_fim - x_ini) * (s / num_passos),
                     y_ini + (y_fim - y_ini) * (s / num_passos))
                    for s in range(1, num_passos + 1)
                ]
            else:
                passos = [(x_fim, y_fim)]

            for sub_x, sub_y in passos:
                if not proj.ativo and not getattr(proj, "requer_detonacao_ao_expirar", False):
                    break
                proj.x = sub_x
                proj.y = sub_y

                # Projéteis de inimigos podem ser bloqueados por núcleos de Multithreading (1 a cada 4s) ou causam dano ao jogador
                if getattr(proj, "dono", "jogador") == "inimigo":
                    if getattr(self.jogador, "vivo", True) and getattr(self.jogador, "multithreading", False) and getattr(self.jogador, "coprocessador_escudo_timer", 0.0) <= 0.0:
                        px_c = proj.x + proj.largura / 2.0
                        py_c = proj.y + proj.altura / 2.0
                        bloqueado_cop = False
                        for ang_cop in getattr(self.jogador, "coprocessadores_angulos", [0.0, 3.14159]):
                            cop_x = centro_jogador_x + math.cos(ang_cop) * 34.0
                            cop_y = centro_jogador_y + math.sin(ang_cop) * 34.0
                            if distancia(px_c, py_c, cop_x, cop_y) <= 18.0:
                                self.jogador.coprocessador_escudo_timer = 4.0
                                self.sistema_particulas.emitir_faiscas(cop_x, cop_y, cor=(0, 240, 255), qtd=8)
                                proj.ativo = False
                                bloqueado_cop = True
                                break
                        if bloqueado_cop:
                            break
                    if getattr(self.jogador, "vivo", True) and colisao_aabb(
                        proj.x, proj.y, proj.largura, proj.altura,
                        hb_jog_x, hb_jog_y, self.jogador.largura, self.jogador.altura
                    ):
                        if getattr(self.jogador, "em_dash_iframes", False):
                            self._tentar_registrar_just_dodge(origem="projetil", mods=mods)
                            continue
                        mult_dano_inim = mult_dano_inim_base
                        if val_ilum:
                            ox = getattr(proj, "x_origem", proj.x + proj.largura / 2.0)
                            oy = getattr(proj, "y_origem", proj.y + proj.altura / 2.0)
                            dist_vis = distancia(ox, oy, centro_jogador_x, centro_jogador_y)
                            if dist_vis > 195.0:
                                mult_dano_inim *= getattr(mods, "dano_fora_visao_mult", 0.50)
                        dano_proj = max(1, int(round(proj.dano * mult_dano_inim)))
                        duel_stg = int(getattr(proj, "duel_stage", 0))
                        if duel_stg >= 2:
                            dano_proj = max(1, int(round(dano_proj * (2.2 if duel_stg == 2 else 3.0))))
                            self.jogador.exposed_timer = max(getattr(self.jogador, "exposed_timer", 0.0), 2.0)
                            self.aplicar_shake(14.0, 0.30)
                            self.toasts_coleta.append({
                                "texto": "FALHA NO DUELO DE PARRY!",
                                "cor": VERMELHO_DANO,
                                "x": centro_jogador_x, "y": self.jogador.y - 26, "tempo": 1.8, "tempo_max": 1.8
                            })
                        self.jogador.receber_dano(dano_proj, causa_morte="Projétil Inimigo / Ondas da Geladeira")
                        if efeitos is not None and ctx_combate is not None:
                            efeitos.disparar_ao_dano_recebido(ctx_combate, dano_proj, fonte=proj)
                        self.aplicar_shake(6.0, 0.15)
                        proj.ativo = False
                        break
                    continue

                if getattr(proj, "explosivo", False):
                    alvo_direto = None
                    detonar = False
                    p_cx = proj.x + proj.largura / 2.0
                    p_cy = proj.y + proj.altura / 2.0
                    r_exp = getattr(proj, "raio_explosao", 80.0)

                    for inimigo in self.inimigos:
                        if not inimigo.vivo or getattr(inimigo, "em_fase", False) or getattr(inimigo, "estado", "") in ("morte", ESTADO_MORTE):
                            continue
                        if colisao_aabb(
                            proj.x, proj.y, proj.largura, proj.altura,
                            inimigo.x, inimigo.y, inimigo.largura, inimigo.altura
                        ):
                            alvo_direto = inimigo
                            detonar = True
                            break

                    if not detonar and auto_dano and getattr(proj, "dono", "jogador") == "jogador":
                        dist_origem = distancia(proj.x, proj.y, getattr(proj, "x_origem", proj.x), getattr(proj, "y_origem", proj.y))
                        if (dist_origem >= 42.0 or (proj.tempo_vida - proj.tempo_vida_restante > 0.20)) and getattr(self.jogador, "vivo", True):
                            if colisao_aabb(proj.x, proj.y, proj.largura, proj.altura, self.jogador.x, self.jogador.y, self.jogador.largura, self.jogador.altura):
                                detonar = True
                        if not detonar:
                            drones_exp = list(self.jogador.drones) if (hasattr(self.jogador, "drones") and self.jogador.drones) else ([self.jogador.drone] if getattr(self.jogador, "drone", None) is not None else [])
                            for dr in drones_exp:
                                if getattr(dr, "ativo", True) and colisao_aabb(proj.x, proj.y, proj.largura, proj.altura, dr.x, dr.y, dr.largura, dr.altura):
                                    detonar = True
                                    break

                    if detonar or proj.tempo_vida_restante <= 0.0 or getattr(proj, "requer_detonacao_ao_expirar", False):
                        proj.ativo = False
                        proj.requer_detonacao_ao_expirar = False
                        self.sistema_particulas.emitir_onda_choque(p_cx, p_cy, raio_max=r_exp)
                        self.sistema_particulas.emitir_debris(p_cx, p_cy, cor=(255, 140, 40), qtd=12)
                        if hasattr(self.sistema_particulas, "adicionar_marca_queimadura"):
                            self.sistema_particulas.adicionar_marca_queimadura(p_cx, p_cy, raio=min(55.0, float(r_exp) * 0.65))
                        self.aplicar_shake(10.0, 0.25)

                        # Lança-Foguetes: Zona de chão em chamas por 2.5s
                        if getattr(proj, "chao_em_chamas", False):
                            self.zonas_fogo.append({
                                "x": p_cx,
                                "y": p_cy,
                                "raio": 72.0,
                                "tempo": 2.5,
                                "tempo_max": 2.5,
                                "tick": 0.0
                            })

                        # Lança-Granadas: 3 sub-explosões de fragmentação
                        if getattr(proj, "fragmentar", False):
                            for i_frag in range(3):
                                ang_f = i_frag * (2.0 * math.pi / 3.0) + 0.4
                                fx = p_cx + math.cos(ang_f) * 42.0
                                fy = p_cy + math.sin(ang_f) * 42.0
                                self.sistema_particulas.emitir_onda_choque(fx, fy, raio_max=38.0, cor=LARANJA_ALERTA)
                                for inim_fr in self.inimigos:
                                    if getattr(inim_fr, "vivo", True) and not getattr(inim_fr, "em_fase", False):
                                        if distancia(fx, fy, inim_fr.x + getattr(inim_fr, "largura", 28) / 2.0, inim_fr.y + getattr(inim_fr, "altura", 28) / 2.0) <= 45.0:
                                            inim_fr.receber_dano(15)
                                            if not inim_fr.vivo:
                                                self._registrar_abate_inimigo(inim_fr, mods)

                        # Onda de Choque (Tremor de Tela Ligado): tropeço/slow em inimigos próximos (sem empurrar Boss)
                        if getattr(mods, "screen_shake_stagger", False):
                            for inim_st in self.inimigos:
                                if not inim_st.vivo or inim_st is self.chefe_final or getattr(inim_st, "is_boss", False):
                                    continue
                                st_cx = inim_st.x + getattr(inim_st, "largura", 28) / 2.0
                                st_cy = inim_st.y + getattr(inim_st, "altura", 28) / 2.0
                                if distancia(st_cx, st_cy, p_cx, p_cy) < 140.0:
                                    dir_st_x, dir_st_y = vetor_direcao(p_cx, p_cy, st_cx, st_cy)
                                    inim_st.x += dir_st_x * 22.0
                                    inim_st.y += dir_st_y * 22.0
                                    self._clamp_entidade_arena(inim_st)
                                    inim_st.slow_timer = max(getattr(inim_st, "slow_timer", 0.0), 1.5)
                                    inim_st.slow_fator = 0.50
                                    inim_st.cooldown_contato_atual = max(getattr(inim_st, "cooldown_contato_atual", 0.0), 0.6)

                        hp_antes_map = {id(e): getattr(e, "hp", 0) for e in self.inimigos if getattr(e, "vivo", True)}
                        afetados = proj.explodir(
                            self.inimigos,
                            jogador=self.jogador,
                            config_sistema=self.config_sistema,
                            mult_dano_explosivo=mult_explosivo,
                            alvo_direto=alvo_direto
                        )

                        # Rocket-Jump (Fogo Amigo Ligado) com animação suave de knockback
                        if getattr(mods, "fogo_amigo_rocket_jump", False) and distancia(p_cx, p_cy, centro_jogador_x, centro_jogador_y) < r_exp:
                            dir_rj_x, dir_rj_y = vetor_direcao(p_cx, p_cy, centro_jogador_x, centro_jogador_y)
                            if hasattr(self.jogador, "aplicar_knockback"):
                                self.jogador.aplicar_knockback(dir_rj_x, dir_rj_y, forca=420.0)
                                self.sistema_particulas.emitir_faiscas(centro_jogador_x, centro_jogador_y, dir_x=dir_rj_x, dir_y=dir_rj_y, cor=(255, 190, 90), qtd=8)
                            else:
                                self.jogador.x += dir_rj_x * 48.0
                                self.jogador.y += dir_rj_y * 48.0
                                self._clamp_entidade_arena(self.jogador)

                        origem_abate_exp = "drone" if getattr(proj, "origem_drone", False) else "arma"
                        for inim in afetados:
                            dano_base_exp = int(getattr(proj, "dano", 35) * mult_explosivo)
                            dano_prev = dano_base_exp * 2 if (inim is alvo_direto) else dano_base_exp
                            hp_ant = hp_antes_map.get(id(inim))
                            dano_exp = max(0, int(hp_ant - getattr(inim, "hp", 0))) if hp_ant is not None and hp_ant > getattr(inim, "hp", 0) else dano_prev
                            is_crit_exp = (inim is alvo_direto)
                            self.dano_total_causado += dano_exp
                            if efeitos is not None and ctx_combate is not None:
                                efeitos.disparar_ao_impacto(ctx_combate, inim, dano_exp, fonte=proj)
                            if hasattr(self, "config_sistema") and str(self.config_sistema.obter_valor("damage_numbers")).lower() in ("ligado", "true", "1"):
                                self.sistema_particulas.emitir_texto_dano(
                                    inim.x + getattr(inim, "largura", 28) / 2.0,
                                    inim.y,
                                    dano_exp,
                                    critico=is_crit_exp
                                )
                            if is_crit_exp:
                                self._aplicar_overvolt_chain(inim, dano_exp, mods)
                            if not inim.vivo:
                                self._registrar_abate_inimigo(inim, mods, origem=origem_abate_exp)
                        break
                else:
                    for inimigo in self.inimigos:
                        if not inimigo.vivo or getattr(inimigo, "estado", "") in ("morte", ESTADO_MORTE):
                            continue

                        if colisao_aabb(
                            proj.x, proj.y, proj.largura, proj.altura,
                            inimigo.x, inimigo.y, inimigo.largura, inimigo.altura
                        ):
                            if getattr(inimigo, "em_fase", False):
                                continue

                            if getattr(inimigo, "is_ninja", False) and not getattr(proj, "refletido_parry", False) and hasattr(inimigo, "aparar_projetil_jogador") and inimigo.pode_aparar_projetil():
                                rebatido_n = inimigo.aparar_projetil_jogador(proj, (centro_jogador_x, centro_jogador_y))
                                if rebatido_n is not None:
                                    if hasattr(self, "sistema_audio") and self.sistema_audio is not None:
                                        self.sistema_audio.tocar_parry_clang(pitch_mult=1.25)
                                    nx_c = inimigo.x + inimigo.largura / 2.0
                                    ny_c = inimigo.y + inimigo.altura / 2.0
                                    self.sistema_particulas.emitir_onda_choque(nx_c, ny_c, raio_max=48.0, cor=(232, 121, 249))
                                    self.sistema_particulas.emitir_faiscas(nx_c, ny_c, cor=(192, 132, 252), qtd=12)
                                    self.toasts_coleta.append({
                                        "texto": "NINJA PARRY!",
                                        "cor": (232, 121, 249),
                                        "x": nx_c, "y": inimigo.y - 18, "tempo": 0.9, "tempo_max": 0.9
                                    })
                                    break

                            if getattr(proj, "perfurante", False):
                                if not hasattr(proj, "alvos_atingidos"):
                                    proj.alvos_atingidos = set()
                                if id(inimigo) in proj.alvos_atingidos:
                                    continue
                                proj.alvos_atingidos.add(id(inimigo))
                            elif getattr(proj, "perfuracoes_restantes", 0) > 0:
                                if not hasattr(proj, "alvos_atingidos"):
                                    proj.alvos_atingidos = set()
                                if id(inimigo) in proj.alvos_atingidos:
                                    continue
                                proj.alvos_atingidos.add(id(inimigo))
                                proj.perfuracoes_restantes -= 1
                            else:
                                proj.ativo = False

                            chance_crit_proj = max(crit_chance, float(getattr(proj, "chance_critico_arma", 0.0)))
                            is_crit = bool(getattr(proj, "critico_nativo", False)) or (chance_crit_proj > 0.0 and random.random() < chance_crit_proj)
                            mult_estase = 1.20 if getattr(inimigo, "vulneravel_estase_timer", 0.0) > 0.0 else 1.0
                            dano_final = int(round(proj.dano * mult_estase * (crit_mult if is_crit else 1.0)))
                            if efeitos is not None and ctx_combate is not None:
                                res_imp = efeitos.disparar_ao_impacto(ctx_combate, inimigo, dano_final, fonte=proj)
                                if res_imp:
                                    if res_imp.get("critico_forcado") and not is_crit:
                                        is_crit = True
                                        dano_final = int(round(dano_final * crit_mult))
                                    if "dano_mult" in res_imp:
                                        dano_final = max(1, int(round(dano_final * float(res_imp["dano_mult"]))))
                                    if "dano_extra" in res_imp:
                                        dano_final += int(res_imp["dano_extra"])

                            dx_k, dy_k = getattr(proj, "dir_x", 0.0), getattr(proj, "dir_y", 0.0)

                            # Knockback individual por pellet (Escopeta / Drone de Combate)
                            kb_proj = float(getattr(proj, "knockback_forca", 0.0))
                            if kb_proj > 0.0 and inimigo is not self.chefe_final and not getattr(inimigo, "is_boss", False):
                                inimigo.x += dx_k * (kb_proj * 0.45)
                                inimigo.y += dy_k * (kb_proj * 0.45)
                                self._clamp_entidade_arena(inimigo)

                            # Números de Dano (Texto com Peso): Empurrão leve no inimigo (exceto Boss)
                            if getattr(mods, "damage_numbers_knockback", False) and inimigo is not self.chefe_final and not getattr(inimigo, "is_boss", False):
                                if dx_k != 0.0 or dy_k != 0.0:
                                    inimigo.x += dx_k * 14.0
                                    inimigo.y += dy_k * 14.0
                                    self._clamp_entidade_arena(inimigo)

                            # Tremor de Tela (screen_shake_stagger): estendido para tiros balísticos (exceto Boss)
                            if getattr(mods, "screen_shake_stagger", False) and inimigo is not self.chefe_final and not getattr(inimigo, "is_boss", False):
                                if dx_k != 0.0 or dy_k != 0.0:
                                    inimigo.x += dx_k * 10.0
                                    inimigo.y += dy_k * 10.0
                                    self._clamp_entidade_arena(inimigo)
                                inimigo.slow_timer = max(getattr(inimigo, "slow_timer", 0.0), 1.2)
                                inimigo.slow_fator = 0.50

                            fonte_dano = (
                                "parry_ninja_proprio"
                                if (getattr(proj, "refletido_parry", False) and getattr(proj, "duel_owner", None) is inimigo)
                                else ("parry_outro" if getattr(proj, "refletido_parry", False) else "projetil_jogador")
                            )
                            ret_d = inimigo.receber_dano(
                                dano_final,
                                origem_x=proj.x,
                                origem_y=proj.y,
                                dir_ataque=(dx_k, dy_k),
                                fonte=fonte_dano
                            )
                            dano_efetivo_b = int(ret_d) if isinstance(ret_d, (int, float)) else dano_final

                            self.dano_total_causado += dano_efetivo_b
                            self.sistema_particulas.emitir_faiscas(
                                proj.x, proj.y,
                                dir_x=dx_k,
                                dir_y=dy_k,
                                cor=(255, 220, 100),
                                qtd=6
                            )
                            if hasattr(self, "config_sistema") and str(self.config_sistema.obter_valor("damage_numbers")).lower() in ("ligado", "true", "1"):
                                self.sistema_particulas.emitir_texto_dano(
                                    inimigo.x + getattr(inimigo, "largura", 28) / 2.0,
                                    inimigo.y,
                                    dano_efetivo_b,
                                    critico=is_crit
                                )

                            # Overvolt (Tensão Crítica): Faíscas elétricas em cadeia em acertos críticos
                            if is_crit:
                                self._aplicar_overvolt_chain(inimigo, dano_efetivo_b, mods)

                            # Projétil refletido por Parry: detona em AoE 90px (75% splash) + onda de choque + marca de queimadura
                            if getattr(proj, "refletido_parry", False):
                                p_cx_parry = proj.x + proj.largura / 2.0
                                p_cy_parry = proj.y + proj.altura / 2.0
                                r_parry_exp = float(getattr(proj, "raio_explosao", 90.0))
                                splash_mult = float(getattr(proj, "splash_mult", 0.75))
                                dano_splash = max(1, int(round(dano_final * splash_mult)))
                                self.sistema_particulas.emitir_onda_choque(p_cx_parry, p_cy_parry, raio_max=r_parry_exp, cor=DOURADO)
                                if hasattr(self.sistema_particulas, "adicionar_marca_queimadura"):
                                    self.sistema_particulas.adicionar_marca_queimadura(p_cx_parry, p_cy_parry, raio=45.0)
                                self.aplicar_shake(8.0, 0.18)
                                for inim_sp in self.inimigos:
                                    if inim_sp is inimigo or not getattr(inim_sp, "vivo", True):
                                        continue
                                    if getattr(inim_sp, "em_fase", False) or getattr(inim_sp, "estado", "") in ("morte", ESTADO_MORTE):
                                        continue
                                    sp_cx = inim_sp.x + getattr(inim_sp, "largura", 28) / 2.0
                                    sp_cy = inim_sp.y + getattr(inim_sp, "altura", 28) / 2.0
                                    if distancia(p_cx_parry, p_cy_parry, sp_cx, sp_cy) <= r_parry_exp:
                                        ret_sp = inim_sp.receber_dano(
                                            dano_splash,
                                            origem_x=p_cx_parry,
                                            origem_y=p_cy_parry,
                                            dir_ataque=vetor_direcao(p_cx_parry, p_cy_parry, sp_cx, sp_cy)
                                        )
                                        dano_sp_ef = int(ret_sp) if isinstance(ret_sp, (int, float)) else dano_splash
                                        self.dano_total_causado += dano_sp_ef
                                        if hasattr(self, "config_sistema") and str(self.config_sistema.obter_valor("damage_numbers")).lower() in ("ligado", "true", "1"):
                                            self.sistema_particulas.emitir_texto_dano(sp_cx, inim_sp.y, dano_sp_ef, critico=False)
                                        if not inim_sp.vivo:
                                            self._registrar_abate_inimigo(inim_sp, mods)

                            if not inimigo.vivo:
                                origem_abate = "drone" if getattr(proj, "origem_drone", False) else "arma"
                                self._registrar_abate_inimigo(inimigo, mods, origem=origem_abate)

                            if not getattr(proj, "perfurante", False):
                                break

                    if not proj.ativo:
                        break

                # Fogo Amigo balístico para projéteis do jogador (após carência >= 42px para o jogador e >= 48px para drones)
                if auto_dano and proj.ativo and getattr(proj, "dono", "jogador") == "jogador":
                    dist_origem = distancia(proj.x, proj.y, getattr(proj, "x_origem", proj.x), getattr(proj, "y_origem", proj.y))
                    if dist_origem >= 42.0 or (proj.tempo_vida - proj.tempo_vida_restante > 0.20):
                        if colisao_aabb(proj.x, proj.y, proj.largura, proj.altura, self.jogador.x, self.jogador.y, self.jogador.largura, self.jogador.altura):
                            if getattr(proj, "perfurante", False):
                                if not hasattr(proj, "alvos_atingidos"):
                                    proj.alvos_atingidos = set()
                                if "jogador" not in proj.alvos_atingidos:
                                    proj.alvos_atingidos.add("jogador")
                                    self.jogador.receber_dano(proj.dano, causa_morte="Fogo Amigo (Seu próprio projétil)")
                                    self.aplicar_shake(6.0, 0.15)
                            else:
                                self.jogador.receber_dano(proj.dano, causa_morte="Fogo Amigo (Seu próprio projétil)")
                                self.aplicar_shake(6.0, 0.15)
                                proj.ativo = False
                                break

                    # Destruição de drones companheiros por fogo amigo (evitando auto-colisão do próprio DroneCombate no spawn)
                    if getattr(proj, "sprite_key", "") != "projetil_drone" or dist_origem >= 28.0:
                        drones_list = []
                        if hasattr(self.jogador, "drones") and self.jogador.drones:
                            drones_list = list(self.jogador.drones)
                        elif getattr(self.jogador, "drone", None) is not None:
                            drones_list = [self.jogador.drone]

                        for dr in drones_list:
                            if getattr(dr, "ativo", True):
                                if colisao_aabb(proj.x, proj.y, proj.largura, proj.altura, dr.x, dr.y, dr.largura, dr.altura):
                                    dr.receber_dano(proj.dano)
                                    if not getattr(proj, "perfurante", False):
                                        proj.ativo = False
                                        break
                    if not proj.ativo:
                        break

            if proj.ativo:
                proj.x = x_fim
                proj.y = y_fim

        # Limpeza de entidades destruídas / inativas
        self.projeteis = [p for p in self.projeteis if p.ativo]
        self.inimigos = [e for e in self.inimigos if e.vivo]
