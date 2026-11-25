# Protocolo: Batata

Arena shooter 2D top-down em pixel art feito em Python com Pygame-CE e PowerPPlay 2.0. Para detalhes de design, veja o [GDD](docs/GDD_ATUALIZADO.md); para arquitetura e contratos internos, veja o [Catálogo Arquitetural](docs/CATALOGO_ARQUITETURAL.md).

## Requisitos e dependências

- Python `3.10` ou superior
- `pygame-ce>=2.5.0`
- `numpy>=1.26.0`
- Opcionais para empacotamento/build (`dev`): `pillow>=10.0.0` e `pyinstaller>=6.0.0`

Para instalar em um ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate
pip install -e .
```

Se quiser apenas instalar as dependências sem modo editável:

```bash
pip install pygame-ce numpy
```

## Como rodar o jogo

Na raiz do repositório:

```bash
python3 src/main.py
```

Com o pacote instalado via `pip install -e .`, também funciona rodar:

```bash
protocolo-batata
```

Atalhos úteis: `F11` ou `Alt+Enter` alternam tela cheia, `ESC` pausa e `F1` (ou `~`) abre o console de debug em partida.

## Como rodar os testes

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 -m unittest discover -s tests -p "test_*.py"
```

No Windows (PowerShell):

```powershell
$env:SDL_VIDEODRIVER="dummy"; $env:SDL_AUDIODRIVER="dummy"; python -m unittest discover -s tests -p "test_*.py"
```

## Estrutura do projeto

- `src/` — código-fonte (`cenas/`, `entidades/`, `armas/`, `equipamentos/`, `sistemas/`, `ui/`, `utils/`).
- `assets/` — sprites, sons, músicas e arquivos de texto em `assets/locales/`.
- `data/` — arquivo de progresso local (`save.json`, gerado automaticamente e ignorado no Git).
- `docs/` — GDD, catálogo de configurações e documentação técnica.
- `tests/` — suíte de testes automatizados (`unittest`).

## Convenções básicas

- Código em Python seguindo PEP 8 (`snake_case` para funções e variáveis, `PascalCase` para classes, `SCREAMING_SNAKE_CASE` para constantes).
- Textos exibidos ao jogador ficam centralizados em `assets/locales/pt_BR/*.json` (carregados via `src/utils/traducao.py`), evitando strings fixas dentro de `src/`.

## Possíveis problemas

- **Erro `No available video device` ou falha de áudio ao rodar testes:** defina `SDL_VIDEODRIVER=dummy` e `SDL_AUDIODRIVER=dummy` antes do comando de teste, como mostrado acima.
- **`ModuleNotFoundError: No module named 'src'`:** execute os comandos a partir da raiz do projeto, onde ficam `pyproject.toml` e a pasta `src/`.
- **Save antigo causando comportamento estranho:** apague `data/save.json` ou use a opção de reset em duas etapas no menu principal.
- **Jogo sem som no Linux:** verifique se o servidor de áudio do sistema (PipeWire/PulseAudio) está ativo e se o pacote `pygame-ce` está instalado no mesmo ambiente Python usado para rodar `src/main.py`.

## FAQ

**Onde ficam salvos meu recorde e desbloqueios?**
Em `data/save.json`, na raiz do projeto (ou na pasta de dados do usuário, caso rode a versão empacotada).

**Como testo configurações, armas ou o chefe final sem jogar a run inteira?**
Inicie uma partida e aperte `F1` ou `~` para abrir o menu de debug.


## Créditos

    "8-Bits Are Scary" composta por Carl Norén
    Originalmente da Trilha Sonora Oficial do PAYDAY 2 (© Starbreeze AB / OVERKILL Software)
    Usado nesse jogo não-comercial por motivos de gameplay e ambientação. Todos os direitos a música pertecem aos seus respectivos donos.
