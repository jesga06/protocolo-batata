"""
Sistema de Partículas e Feedback Visual — Protocolo: Batata
Gerencia efeitos visuais de alta performance:
- Faíscas balísticas de impacto de tiros
- Bursts cintilantes na coleta de drops (XP, cura, caixas)
- Ondas de choque expansivas e detritos de explosões
"""

import math
import random
import pygame


class Particula:
    """Representa uma partícula individual em coordenadas de mundo."""
    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        vida_max: float,
        tamanho_inicial: float,
        tamanho_final: float,
        cor: tuple[int, int, int],
        decaimento_vel: float = 0.92
    ):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.vida_max = max(0.01, float(vida_max))
        self.vida = self.vida_max
        self.tamanho_inicial = float(tamanho_inicial)
        self.tamanho_final = float(tamanho_final)
        self.cor = cor
        self.decaimento_vel = float(decaimento_vel)

    @property
    def viva(self) -> bool:
        return self.vida > 0.0

    @property
    def progresso(self) -> float:
        """Retorna valor de 0.0 (nascimento) a 1.0 (morte)."""
        return 1.0 - (self.vida / self.vida_max)

    def update(self, dt: float):
        self.vida -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= (self.decaimento_vel ** (dt * 60.0))
        self.vy *= (self.decaimento_vel ** (dt * 60.0))

    def obter_tamanho_atual(self) -> float:
        p = self.progresso
        return max(0.5, self.tamanho_inicial + (self.tamanho_final - self.tamanho_inicial) * p)


class OndaChoque:
    """Representa um anel expansivo de onda de choque."""
    def __init__(
        self,
        x: float,
        y: float,
        raio_max: float = 80.0,
        vida_max: float = 0.25,
        cor: tuple[int, int, int] = (255, 140, 30)
    ):
        self.x = float(x)
        self.y = float(y)
        self.raio_max = float(raio_max)
        self.vida_max = max(0.01, float(vida_max))
        self.vida = self.vida_max
        self.cor = cor

    @property
    def viva(self) -> bool:
        return self.vida > 0.0

    @property
    def progresso(self) -> float:
        return 1.0 - (self.vida / self.vida_max)

    def update(self, dt: float):
        self.vida -= dt

    def obter_raio_atual(self) -> float:
        return max(1.0, self.raio_max * (self.progresso ** 0.5))


class TextoDano:
    """Representa um número ou callout flutuante no espaço do mundo."""
    def __init__(
        self,
        x: float,
        y: float,
        dano: int,
        critico: bool = False,
        vida_max: float = 0.65,
        texto: str = None,
        cor: tuple[int, int, int] = None
    ):
        self.x = float(x)
        self.y = float(y)
        self.vx = random.uniform(-20.0, 20.0)
        self.vy = random.uniform(-70.0, -100.0)
        self.dano = int(dano)
        self.critico = bool(critico)
        self.vida_max = max(0.01, float(vida_max))
        self.vida = self.vida_max
        self.texto = str(texto) if texto is not None else (f"{dano}!" if critico else f"{dano}")
        self.cor = cor if cor is not None else ((255, 215, 0) if critico else (255, 255, 255))
        self._surf = None

    @property
    def viva(self) -> bool:
        return self.vida > 0.0

    @property
    def progresso(self) -> float:
        return 1.0 - (self.vida / self.vida_max)

    def update(self, dt: float):
        self.vida -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 60.0 * dt


class CapsulaChao:
    """Representa uma cápsula de latão ejetada no chão que gira e some em 1.5s."""
    def __init__(self, x: float, y: float, dir_x: float = 1.0, dir_y: float = 0.0, vida_max: float = 1.5):
        self.x = float(x)
        self.y = float(y)
        base_ang = math.atan2(-dir_y, -dir_x) if (dir_x != 0.0 or dir_y != 0.0) else random.uniform(0.0, 2.0 * math.pi)
        ang_ej = base_ang + random.uniform(-0.65, 0.65)
        vel = random.uniform(55.0, 115.0)
        self.vx = math.cos(ang_ej) * vel
        self.vy = math.sin(ang_ej) * vel
        self.angulo = random.uniform(0.0, 2.0 * math.pi)
        self.vel_ang = random.uniform(-11.0, 11.0)
        self.vida_max = max(0.01, float(vida_max))
        self.vida = self.vida_max
        self.cor = (232, 194, 74)

    @property
    def viva(self) -> bool:
        return self.vida > 0.0

    @property
    def progresso(self) -> float:
        return 1.0 - (self.vida / self.vida_max)

    def update(self, dt: float):
        self.vida -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        fator_atrito = 0.84 ** (dt * 60.0)
        self.vx *= fator_atrito
        self.vy *= fator_atrito
        self.angulo += self.vel_ang * dt
        self.vel_ang *= fator_atrito


class MarcaQueimadura:
    """Representa uma marca circular escura de queimadura de explosão no chão (5.0s)."""
    def __init__(self, x: float, y: float, raio: float = 40.0, vida_max: float = 5.0):
        self.x = float(x)
        self.y = float(y)
        self.raio = max(4.0, float(raio))
        self.vida_max = max(0.01, float(vida_max))
        self.vida = self.vida_max

    @property
    def viva(self) -> bool:
        return self.vida > 0.0

    @property
    def progresso(self) -> float:
        return 1.0 - (self.vida / self.vida_max)

    def update(self, dt: float):
        self.vida -= dt


class ArcoParry:
    """Representa um arco luminoso dourado de 120° emitido ao executar parry."""
    def __init__(
        self,
        x: float,
        y: float,
        angulo: float,
        raio: float = 128.0,
        arco_graus: float = 120.0,
        vida_max: float = 0.24,
        cor: tuple[int, int, int] | None = None,
    ):
        self.x = float(x)
        self.y = float(y)
        self.angulo = float(angulo)
        self.raio = max(8.0, float(raio))
        self.arco_graus = float(arco_graus)
        self.vida_max = max(0.01, float(vida_max))
        self.vida = self.vida_max
        self.cor = cor

    @property
    def viva(self) -> bool:
        return self.vida > 0.0

    @property
    def progresso(self) -> float:
        return 1.0 - (self.vida / self.vida_max)

    def update(self, dt: float):
        self.vida -= dt


class SistemaParticulas:
    """
    Gerenciador global de partículas com teto rígido de instâncias e rendering otimizado.
    """
    MAX_PARTICULAS = 300
    MAX_TEXTOS = 100
    MAX_ONDAS = 30
    MAX_CAPSULAS = 120
    MAX_MARCAS = 60
    MAX_ARCOS = 16
    _fonte_dano = None

    def __init__(self):
        self.particulas: list[Particula] = []
        self.ondas_choque: list[OndaChoque] = []
        self.textos_dano: list[TextoDano] = []
        self.capsulas: list[CapsulaChao] = []
        self.marcas_queimadura: list[MarcaQueimadura] = []
        self.arcos_parry: list[ArcoParry] = []
        self.low_graphics: bool = False
        self._acum_jato_chamas: float = 0.0
        self._surfs_onda_cache: dict[int, pygame.Surface] = {}
        self._surfs_marca_cache: dict[int, pygame.Surface] = {}

    def limpar(self):
        """Descarta todas as partículas, ondas, textos, arcos e persistências de chão ativos."""
        self.particulas.clear()
        self.ondas_choque.clear()
        self.textos_dano.clear()
        self.capsulas.clear()
        self.marcas_queimadura.clear()
        self.arcos_parry.clear()

    def adicionar_capsula(self, x: float, y: float, dir_x: float = 1.0, dir_y: float = 0.0):
        """Adiciona uma cápsula de latão rotacionando no chão (duração 1.5s)."""
        self.capsulas.append(CapsulaChao(x=x, y=y, dir_x=dir_x, dir_y=dir_y, vida_max=1.5))
        if len(self.capsulas) > self.MAX_CAPSULAS:
            del self.capsulas[:len(self.capsulas) - self.MAX_CAPSULAS]

    def adicionar_marca_queimadura(self, x: float, y: float, raio: float = 40.0):
        """Adiciona uma marca escura circular de explosão no chão (duração 5.0s)."""
        self.marcas_queimadura.append(MarcaQueimadura(x=x, y=y, raio=raio, vida_max=5.0))
        if len(self.marcas_queimadura) > self.MAX_MARCAS:
            del self.marcas_queimadura[:len(self.marcas_queimadura) - self.MAX_MARCAS]

    def adicionar_arco_parry(
        self,
        x: float,
        y: float,
        angulo: float,
        raio: float = 128.0,
        arco_graus: float = 120.0,
        mostrar_texto: bool = True,
        cor: tuple | None = None,
    ):
        """
        Emite VFX de parry/golpe RMB: arco luminoso, anel radial, faíscas direcionais
        e callout flutuante 'PARRY!' (apenas quando mostrar_texto=True).
        """
        self.arcos_parry.append(
            ArcoParry(x=x, y=y, angulo=angulo, raio=raio, arco_graus=arco_graus, vida_max=0.24, cor=cor)
        )
        if len(self.arcos_parry) > self.MAX_ARCOS:
            del self.arcos_parry[:len(self.arcos_parry) - self.MAX_ARCOS]

        cor_onda = cor if cor is not None else (255, 245, 165)
        cor_faisca = cor if cor is not None else (255, 225, 90)

        # Anel de flash branco-dourado radial
        self.ondas_choque.append(OndaChoque(x=x, y=y, raio_max=max(48.0, float(raio) * 0.95), vida_max=0.22, cor=cor_onda))
        if len(self.ondas_choque) > self.MAX_ONDAS:
            del self.ondas_choque[:len(self.ondas_choque) - self.MAX_ONDAS]

        # Faíscas direcionais douradas e branco-quente
        dx = math.cos(angulo)
        dy = math.sin(angulo)
        self.emitir_faiscas(x, y, dir_x=dx, dir_y=dy, cor=cor_faisca, qtd=10)
        self.emitir_faiscas(x, y, dir_x=dx, dir_y=dy, cor=(255, 250, 210), qtd=6)

        # Callout flutuante "PARRY!" apenas quando um parry real ocorre
        if mostrar_texto:
            self.textos_dano.append(
                TextoDano(x=x, y=y - 16.0, dano=0, critico=True, vida_max=0.75, texto="PARRY!", cor=(255, 235, 90))
            )
            if len(self.textos_dano) > self.MAX_TEXTOS:
                del self.textos_dano[:len(self.textos_dano) - self.MAX_TEXTOS]

    def adicionar_onda_dash(self, x: float, y: float):
        """Emite anel expansivo ciano de onda de choque ao iniciar um Dash."""
        self.ondas_choque.append(OndaChoque(x=x, y=y, raio_max=72.0, vida_max=0.22, cor=(0, 230, 255)))
        if len(self.ondas_choque) > self.MAX_ONDAS:
            del self.ondas_choque[:len(self.ondas_choque) - self.MAX_ONDAS]
        self.emitir_faiscas(x, y, dir_x=0.0, dir_y=0.0, cor=(90, 240, 255), qtd=5)

    def emitir_texto_dano(
        self,
        x: float,
        y: float,
        dano: int,
        critico: bool = False
    ):
        """Emite número flutuante de dano no mundo."""
        self.textos_dano.append(TextoDano(x, y, dano, critico=critico))
        if len(self.textos_dano) > self.MAX_TEXTOS:
            del self.textos_dano[:len(self.textos_dano) - self.MAX_TEXTOS]

    def emitir_faiscas(
        self,
        x: float,
        y: float,
        dir_x: float = 0.0,
        dir_y: float = 0.0,
        cor: tuple[int, int, int] = (255, 220, 100),
        qtd: int = 6
    ):
        """
        Emite faíscas balísticas direcionais ao atingir um alvo.
        """
        if self.low_graphics:
            qtd = max(1, qtd // 2)

        base_ang = math.atan2(dir_y, dir_x) if (dir_x != 0 or dir_y != 0) else random.uniform(0, 2 * math.pi)

        for _ in range(qtd):
            # Cone de espalhamento de ~90 graus
            ang = base_ang + random.uniform(-0.8, 0.8)
            vel = random.uniform(120.0, 320.0)
            vx = math.cos(ang) * vel
            vy = math.sin(ang) * vel
            vida = random.uniform(0.10, 0.22)
            tam_ini = random.uniform(2.5, 4.0)

            p = Particula(
                x=x,
                y=y,
                vx=vx,
                vy=vy,
                vida_max=vida,
                tamanho_inicial=tam_ini,
                tamanho_final=0.5,
                cor=cor,
                decaimento_vel=0.88
            )
            self.particulas.append(p)

        if len(self.particulas) > self.MAX_PARTICULAS:
            del self.particulas[:len(self.particulas) - self.MAX_PARTICULAS]

    def emitir_burst_drop(self, x: float, y: float, tipo: str = "xp"):
        """
        Emite partículas cintilantes ascendentes ao coletar um drop.
        """
        mapa_cores = {
            "xp": (255, 215, 0),         # Dourado
            "cura": (50, 230, 90),        # Verde
            "arma": (255, 140, 0),        # Laranja
            "equipamento": (175, 75, 255),# Roxo
            "config": (0, 220, 255),      # Ciano
            "overclock": (175, 75, 255)   # Roxo
        }
        cor = mapa_cores.get(tipo, (255, 255, 255))
        qtd = 12 if tipo in ("arma", "equipamento", "overclock") else 8
        if self.low_graphics:
            qtd = max(1, qtd // 2)

        for _ in range(qtd):
            ang = random.uniform(-math.pi * 0.8, -math.pi * 0.2)  # Direção preferencialmente para cima
            vel = random.uniform(60.0, 160.0)
            vx = math.cos(ang) * vel + random.uniform(-20, 20)
            vy = math.sin(ang) * vel
            vida = random.uniform(0.20, 0.40)
            tam_ini = random.uniform(3.0, 5.0)

            p = Particula(
                x=x + random.uniform(-6, 6),
                y=y + random.uniform(-6, 6),
                vx=vx,
                vy=vy,
                vida_max=vida,
                tamanho_inicial=tam_ini,
                tamanho_final=0.0,
                cor=cor,
                decaimento_vel=0.94
            )
            self.particulas.append(p)

        if len(self.particulas) > self.MAX_PARTICULAS:
            del self.particulas[:len(self.particulas) - self.MAX_PARTICULAS]

    def emitir_onda_choque(
        self,
        x: float,
        y: float,
        raio_max: float = 80.0,
        cor: tuple[int, int, int] = (255, 140, 30)
    ):
        """
        Cria uma onda de choque radial expansiva.
        """
        self.ondas_choque.append(OndaChoque(x=x, y=y, raio_max=raio_max, vida_max=0.28, cor=cor))
        if len(self.ondas_choque) > self.MAX_ONDAS:
            del self.ondas_choque[:len(self.ondas_choque) - self.MAX_ONDAS]

    def emitir_debris(
        self,
        x: float,
        y: float,
        cor: tuple[int, int, int] = (200, 120, 50),
        qtd: int = 10
    ):
        """
        Emite fragmentos de detritos em todas as direções para explosões.
        """
        if self.low_graphics:
            qtd = max(1, qtd // 2)

        for _ in range(qtd):
            ang = random.uniform(0, 2 * math.pi)
            vel = random.uniform(80.0, 260.0)
            vx = math.cos(ang) * vel
            vy = math.sin(ang) * vel
            vida = random.uniform(0.20, 0.45)
            tam_ini = random.uniform(2.0, 4.5)

            p = Particula(
                x=x,
                y=y,
                vx=vx,
                vy=vy,
                vida_max=vida,
                tamanho_inicial=tam_ini,
                tamanho_final=0.5,
                cor=cor,
                decaimento_vel=0.90
            )
            self.particulas.append(p)

        if len(self.particulas) > self.MAX_PARTICULAS:
            del self.particulas[:len(self.particulas) - self.MAX_PARTICULAS]

    def emitir_jato_chamas(
        self,
        x: float,
        y: float,
        angulo: float,
        alcance: float,
        arco_graus: float,
        dt: float = 1.0 / 60.0,
        vel_origem_x: float = 0.0,
        vel_origem_y: float = 0.0,
    ):
        """
        Emite partículas leves de fogo, brasa e fumaça ao longo do cone do Lança-Chamas
        (zero alocações de fontes ou superfícies), calibradas para preencher exatamente
        o setor de dano (alcance e arco_graus) com densidade equilibrada.
        """
        taxa = 85.0 if self.low_graphics else 165.0
        self._acum_jato_chamas = min(
            6.0, self._acum_jato_chamas + taxa * max(0.0, float(dt))
        )
        qtd = int(self._acum_jato_chamas)
        if qtd <= 0:
            return
        self._acum_jato_chamas -= qtd

        meio_arco_rad = math.radians(max(1.0, float(arco_graus)) * 0.5) * 0.92
        alc = max(24.0, float(alcance))
        decaimento = 0.965
        k_arrasto = -60.0 * math.log(decaimento)
        vox = max(-420.0, min(420.0, float(vel_origem_x))) * 0.60
        voy = max(-420.0, min(420.0, float(vel_origem_y))) * 0.60
        paleta_chama = (
            (255, 232, 115),  # núcleo amarelo-quente
            (255, 148, 38),   # chama laranja
            (235, 72, 24),    # brasa vermelho-alaranjada
            (92, 82, 76),     # fumaça escura leve
        )

        for _ in range(qtd):
            ang = float(angulo) + random.uniform(-meio_arco_rad, meio_arco_rad)
            vida = random.uniform(0.15, 0.22)
            fator_dist = (1.0 - math.exp(-k_arrasto * vida)) / k_arrasto
            dist_alvo = alc * random.uniform(0.82, 0.98)
            vel = dist_alvo / max(0.04, fator_dist)
            vx = math.cos(ang) * vel + vox
            vy = math.sin(ang) * vel + voy
            if random.random() < 0.14:
                cor = paleta_chama[3]
                tam_ini = random.uniform(2.5, 4.0)
                tam_fim = random.uniform(5.0, 7.0)
            else:
                cor = paleta_chama[random.randrange(3)]
                tam_ini = random.uniform(3.2, 5.0)
                tam_fim = random.uniform(1.6, 2.8)

            p = Particula(
                x=float(x),
                y=float(y),
                vx=vx,
                vy=vy,
                vida_max=vida,
                tamanho_inicial=tam_ini,
                tamanho_final=tam_fim,
                cor=cor,
                decaimento_vel=decaimento,
            )
            self.particulas.append(p)

        if len(self.particulas) > self.MAX_PARTICULAS:
            del self.particulas[:len(self.particulas) - self.MAX_PARTICULAS]

    def atualizar(self, dt: float):
        """
        Atualiza física e tempo de vida de partículas, ondas, textos,
        arcos de parry e elementos persistentes no chão (cápsulas e marcas).
        """
        for p in self.particulas:
            p.update(dt)
        self.particulas = [p for p in self.particulas if p.viva]

        for oc in self.ondas_choque:
            oc.update(dt)
        self.ondas_choque = [oc for oc in self.ondas_choque if oc.viva]

        for td in self.textos_dano:
            td.update(dt)
        self.textos_dano = [td for td in self.textos_dano if td.viva]

        for ap in self.arcos_parry:
            ap.update(dt)
        self.arcos_parry = [ap for ap in self.arcos_parry if ap.viva]

        for cap in self.capsulas:
            cap.update(dt)
        self.capsulas = [cap for cap in self.capsulas if cap.viva]

        for mq in self.marcas_queimadura:
            mq.update(dt)
        self.marcas_queimadura = [mq for mq in self.marcas_queimadura if mq.viva]

    def update(self, dt: float):
        """Alias compatível para atualizar(dt)."""
        self.atualizar(dt)

    def desenhar_chao(self, screen, cam_x: float = 0.0, cam_y: float = 0.0, scale: float = 1.0):
        """
        Renderiza persistência leve no chão (marcas de queimadura e cápsulas de latão)
        abaixo das entidades.
        """
        surf = getattr(screen, "screen", screen)
        largura_tela = getattr(screen, "largura", getattr(surf, "get_width", lambda: 1280)())
        altura_tela = getattr(screen, "altura", getattr(surf, "get_height", lambda: 720)())
        is_low_graphics = self.low_graphics or getattr(screen, "low_graphics", False)
        esc = max(0.01, float(scale))

        # 1. Marcas de queimadura de explosões (desaparecem em 5.0s)
        for mq in self.marcas_queimadura:
            sx = (mq.x - cam_x) * esc
            sy = (mq.y - cam_y) * esc
            r_px = max(2, int(round(mq.raio * esc)))
            if sx < -r_px - 8 or sx > largura_tela + r_px + 8 or sy < -r_px - 8 or sy > altura_tela + r_px + 8:
                continue

            fator_vida = max(0.0, 1.0 - mq.progresso)
            alpha = int(145 * fator_vida)
            if alpha <= 4:
                continue

            if is_low_graphics:
                tom = max(12, int(24 + 18 * mq.progresso))
                pygame.draw.circle(surf, (tom, tom, tom + 2), (int(sx), int(sy)), r_px)
            else:
                dim = r_px * 2 + 4
                try:
                    surf_m = self._surfs_marca_cache.get(dim)
                    if surf_m is None:
                        surf_m = pygame.Surface((dim, dim), pygame.SRCALPHA)
                        self._surfs_marca_cache[dim] = surf_m
                    else:
                        surf_m.fill((0, 0, 0, 0))
                    c = dim // 2
                    pygame.draw.circle(surf_m, (18, 16, 20, alpha), (c, c), r_px)
                    pygame.draw.circle(surf_m, (8, 7, 10, min(255, int(alpha * 1.2))), (c, c), max(1, int(r_px * 0.6)))
                    surf.blit(surf_m, (int(sx - c), int(sy - c)))
                except Exception:
                    pass

        # 2. Cápsulas de latão rotacionando no chão (desaparecem em 1.5s)
        for cap in self.capsulas:
            sx = (cap.x - cam_x) * esc
            sy = (cap.y - cam_y) * esc
            if sx < -16 or sx > largura_tela + 16 or sy < -16 or sy > altura_tela + 16:
                continue

            fator_vida = max(0.0, 1.0 - cap.progresso)
            if fator_vida <= 0.02:
                continue

            half_l = max(1.5, 2.8 * esc)
            half_w = max(0.8, 1.3 * esc)
            ca = math.cos(cap.angulo)
            sa = math.sin(cap.angulo)
            pts = (
                (int(sx + ca * half_l - sa * half_w), int(sy + sa * half_l + ca * half_w)),
                (int(sx - ca * half_l - sa * half_w), int(sy - sa * half_l + ca * half_w)),
                (int(sx - ca * half_l + sa * half_w), int(sy - sa * half_l - ca * half_w)),
                (int(sx + ca * half_l + sa * half_w), int(sy + sa * half_l - ca * half_w)),
            )
            r_col = int(cap.cor[0] * (0.45 + 0.55 * fator_vida))
            g_col = int(cap.cor[1] * (0.45 + 0.55 * fator_vida))
            b_col = int(cap.cor[2] * (0.45 + 0.55 * fator_vida))
            pygame.draw.polygon(surf, (r_col, g_col, b_col), pts)

    def desenhar(self, janela, camera=None):
        """
        Renderiza todas as partículas, ondas de choque e números de dano na tela virtual com suporte a low_graphics.
        """
        screen = getattr(janela, "screen", janela)
        largura_janela = getattr(janela, "largura", getattr(screen, "get_width", lambda: 1280)())
        altura_janela = getattr(janela, "altura", getattr(screen, "get_height", lambda: 720)())
        is_low_graphics = self.low_graphics or getattr(janela, "low_graphics", False)

        # 1. Renderiza ondas de choque
        for oc in self.ondas_choque:
            tx = camera.transform_x(oc.x) if camera else oc.x
            ty = camera.transform_y(oc.y) if camera else oc.y

            if tx < -100 or tx > largura_janela + 100 or ty < -100 or ty > altura_janela + 100:
                continue

            raio = oc.obter_raio_atual()
            if is_low_graphics:
                # Desenha círculo simples diretamente sem alocação de Surface com alpha
                largura_linha = max(1, int(2 * (1.0 - oc.progresso)))
                pygame.draw.circle(screen, oc.cor, (int(tx), int(ty)), int(raio), width=largura_linha)
            else:
                alpha = int(max(0, 255 * (1.0 - oc.progresso)))
                dim = int(raio * 2 + 10)

                if dim > 0 and alpha > 5:
                    try:
                        surf_oc = self._surfs_onda_cache.get(dim)
                        if surf_oc is None:
                            surf_oc = pygame.Surface((dim, dim), pygame.SRCALPHA)
                            self._surfs_onda_cache[dim] = surf_oc
                        else:
                            surf_oc.fill((0, 0, 0, 0))

                        cx = dim // 2
                        cy = dim // 2
                        cor_rgba = (oc.cor[0], oc.cor[1], oc.cor[2], alpha)
                        largura_linha = max(1, int(3 * (1.0 - oc.progresso)))
                        pygame.draw.circle(surf_oc, cor_rgba, (cx, cy), int(raio), width=largura_linha)
                        screen.blit(surf_oc, (int(tx - cx), int(ty - cy)))
                    except Exception:
                        pass

        # 1b. Renderiza arcos dourados de parry (120°)
        for ap in self.arcos_parry:
            tx = camera.transform_x(ap.x) if camera else ap.x
            ty = camera.transform_y(ap.y) if camera else ap.y
            r_ap = ap.raio * (0.85 + 0.20 * ap.progresso)
            if tx < -r_ap - 30 or tx > largura_janela + r_ap + 30 or ty < -r_ap - 30 or ty > altura_janela + r_ap + 30:
                continue

            fator = max(0.0, 1.0 - ap.progresso)
            meio_rad = math.radians(ap.arco_graus / 2.0)
            passos = 14 if not is_low_graphics else 8
            pontos = []
            for i in range(passos + 1):
                t = i / passos
                ang = (ap.angulo - meio_rad) + (2.0 * meio_rad) * t
                pontos.append((int(tx + math.cos(ang) * r_ap), int(ty + math.sin(ang) * r_ap)))

            if len(pontos) >= 2:
                larg_ext = max(2, int(round(7 * fator)))
                cor_custom = getattr(ap, "cor", None)
                if cor_custom is not None:
                    cor_ext = (
                        int(cor_custom[0] * (0.65 + 0.35 * fator)),
                        int(cor_custom[1] * (0.65 + 0.35 * fator)),
                        int(cor_custom[2] * (0.65 + 0.35 * fator)),
                    )
                else:
                    cor_ext = (255, int(205 + 40 * fator), int(60 + 50 * fator))
                pygame.draw.lines(screen, cor_ext, False, pontos, larg_ext)
                if not is_low_graphics:
                    larg_int = max(1, int(round(3 * fator)))
                    pygame.draw.lines(screen, (255, 252, 210), False, pontos, larg_int)

        # 2. Renderiza partículas
        for p in self.particulas:
            tx = camera.transform_x(p.x) if camera else p.x
            ty = camera.transform_y(p.y) if camera else p.y

            if tx < -20 or tx > largura_janela + 20 or ty < -20 or ty > altura_janela + 20:
                continue

            tam = p.obter_tamanho_atual()
            if tam > 0:
                if is_low_graphics:
                    int_tam = max(1, int(tam))
                    pygame.draw.rect(screen, p.cor, (int(tx - int_tam // 2), int(ty - int_tam // 2), int_tam, int_tam))
                else:
                    pygame.draw.circle(screen, p.cor, (int(tx), int(ty)), max(1, int(tam)))

        # 3. Renderiza números flutuantes de dano
        if self.textos_dano:
            if self._fonte_dano is None:
                try:
                    if pygame.font.get_init():
                        self._fonte_dano = pygame.font.SysFont("arial", 16, bold=True)
                except Exception:
                    self._fonte_dano = None

            if self._fonte_dano is not None:
                for td in self.textos_dano:
                    tx = camera.transform_x(td.x) if camera else td.x
                    ty = camera.transform_y(td.y) if camera else td.y

                    if tx < -40 or tx > largura_janela + 40 or ty < -40 or ty > altura_janela + 40:
                        continue

                    try:
                        if getattr(td, "_surf", None) is None:
                            td._surf = self._fonte_dano.render(td.texto, True, td.cor)
                        surf_t = td._surf
                        screen.blit(surf_t, (int(tx - surf_t.get_width() / 2), int(ty)))
                    except Exception:
                        pass
