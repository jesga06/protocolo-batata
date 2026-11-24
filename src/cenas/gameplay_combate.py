"""
Resolução de Combate, Armas, Parry, Railgun, Overvolt e Abates — Protocolo: Batata
Extraído de GameplayScene como mixin behavior-preserving (GameplayCombateMixin).
"""

import math
import random
import sys
from src.entidades.projetil import Projetil
from src.entidades.geladeira_tsunami import ESTADO_MORTE
from src.utils.constantes import (
    DASH_PARRY_META,
    VERMELHO_DANO, AZUL_CIANO, DOURADO,
    SAVE_FILE_PATH,
)
from src.utils.math_utils import distancia, vetor_direcao


class GameplayCombateMixin:
    """
    Mixin responsável pelas ações de combate, melee, parry, railgun, overvolt,
    resolução de projéteis/colisões e registro de abates da GameplayScene.
    """

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
            chave_sfx = self._obter_sfx_arma(arma_at)
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

        mods = self.gerenciador_config.obter_modificadores() if hasattr(self, "gerenciador_config") and self.gerenciador_config else None
        parry_ef = getattr(mods, "parry_efeito", "padrao") if mods else "padrao"

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

            if hasattr(self, "config_sistema") and self.config_sistema is not None and hasattr(self.config_sistema, "registrar_parry"):
                total_parries, recem_desbloqueou = self.config_sistema.registrar_parry(DASH_PARRY_META)
                if recem_desbloqueou:
                    self.jogador.dash_desbloqueado = True
                    try:
                        save_path = getattr(
                            sys.modules.get("src.cenas.gameplay"),
                            "SAVE_FILE_PATH",
                            SAVE_FILE_PATH,
                        )
                        self.config_sistema.salvar_arquivo(save_path)
                    except Exception:
                        pass
                    self.toasts_coleta.append({
                        "texto": "DASH DESBLOQUEADO [ESPAÇO]",
                        "cor": AZUL_CIANO,
                        "x": cx, "y": self.jogador.y - 22, "tempo": 2.6, "tempo_max": 2.6
                    })
                elif total_parries % 10 == 0:
                    self.toasts_coleta.append({
                        "texto": f"PARRY {total_parries}/{DASH_PARRY_META}",
                        "cor": DOURADO,
                        "x": cx, "y": self.jogador.y - 18, "tempo": 1.8, "tempo_max": 1.8
                    })

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
        """Executa golpe corpo-a-corpo (Slot 1, RMB Quick-Melee ou tecla E) com janela de parry."""
        ang_mira = math.atan2(mouse_mundo_y - centro_jogador_y, mouse_mundo_x - centro_jogador_x)
        if hasattr(self, "sistema_audio") and self.sistema_audio is not None:
            self.sistema_audio.tocar_sfx("sfx_ataque_melee", pitch_aleatorio=True)

        afetados = arma_melee.executar_ataque(
            centro_jogador_x, centro_jogador_y,
            self.inimigos,
            mira_x=mouse_mundo_x,
            mira_y=mouse_mundo_y,
            angulo_mira=ang_mira,
            aplicar_dano=False
        )
        # Processa parry imediato na ativação do golpe (janela ativa de 0.18s continua nos frames seguintes)
        self._processar_parry_ativo(arma_melee, centro_jogador_x, centro_jogador_y, angulo_mira=ang_mira)

        if isinstance(afetados, (list, tuple)):
            for inim in afetados:
                dano_base = getattr(arma_melee, "dano", 10)
                is_crit = (crit_chance > 0.0 and random.random() < crit_chance)
                dano_melee = math.ceil(dano_base * mult_dano_buff * (crit_mult if is_crit else 1.0))

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
                    self._registrar_abate_inimigo(inim, mods)
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

    def _registrar_abate_inimigo(self, inim, mods=None):
        """Contabiliza o abate de um inimigo, score, efeitos de shrapnel, shake e drops."""
        if mods is None:
            mods = self.gerenciador_config.obter_modificadores() if hasattr(self, "gerenciador_config") else None

        self.abates += 1
        self.pontos += getattr(inim, "score_valor", 100)
        inim_cx = inim.x + getattr(inim, "largura", 28) / 2.0
        inim_cy = inim.y + getattr(inim, "altura", 28) / 2.0

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
