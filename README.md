# 🎮 BombInsper Online

**Um jogo Bomberman multiplayer online desenvolvido em Python com Pygame e FastAPI**

## 📖 Descrição do Jogo

BombInsper Online é uma versão moderna e multiplayer do clássico jogo Bomberman. Os jogadores competem em arenas destructíveis, colocando bombas estrategicamente para eliminar oponentes e destruir obstáculos. O jogo combina ação rápida com elementos estratégicos, oferecendo uma experiência competitiva online.

### 🎯 Características Principais

- **Multiplayer Online Real-Time**: Partidas 1v1 com sincronização em tempo real via WebSockets
- **Sistema de Matchmaking**: Sistema automático de emparelhamento de jogadores
- **Física de Explosão Realista**: Explosões propagam em cruz, destruindo blocos e afetando jogadores
- **Animações Suaves**: Interpolação de movimento para experiência visual fluida
- **Interface Moderna**: HUD elegante com informações dos jogadores e métricas de conexão
- **Leaderboard Global**: Sistema de ranking com estatísticas persistentes
- **Assets Customizados**: Diferentes skins de personagens (Carlitos e Rogério)
- **Cross-Platform**: Builds automáticos para Windows, macOS e Linux

## 🏗️ Arquitetura do Sistema

### 🖥️ Cliente (`client/`)
- **`app.py`**: Factory principal da aplicação cliente
- **`scenes/`**: Sistema de cenas (login, menu, jogo, matchmaking)
- **`game/`**: Entidades do jogo (jogador, bomba, partículas)
- **`services/`**: Serviços de autenticação, matchmaking e jogo
- **`assets/`**: Recursos visuais e sonoros

### 🌐 Servidor (`server/`)
- **`app.py`**: Aplicação FastAPI com middleware CORS
- **`api/`**: Endpoints REST e WebSocket
  - `auth.py`: Autenticação JWT
  - `match.py`: Estatísticas de partidas
  - `ws.py`: WebSockets para matchmaking e jogo
- **`services/`**: Lógica de negócio
  - `game.py`: Gerenciamento de estado de jogo
  - `auth.py`: Serviços de autenticação
- **`utils/`**: Utilitários (compressão de estado)

### 🗄️ Core (`core/`)
- **`models/`**: Modelos Pydantic compartilhados
- **`constants.py`**: Constantes do jogo e assets
- **`config.py`**: Configurações via Pydantic Settings
- **`abstract.py`**: Classes abstratas base

## 🚀 Como Executar

### 📋 Pré-requisitos
- Python 3.11+
- PostgreSQL (para produção) ou SQLite (desenvolvimento)
- Docker (opcional, para deployment)

### 🔧 Instalação Local

1. **Clone o repositório**
```bash
git clone <repository-url>
cd bomb
```

2. **Instale as dependências**
```bash
pip install -r requirements.txt
```

3. **Configure o banco de dados**
```bash
# Gera o Prisma Client
python -m prisma generate

# Executa as migrations
python -m prisma migrate deploy
```

4. **Configure variáveis de ambiente**
```bash
# Crie um arquivo .env com:
SERVER_SECRET_KEY=your-secret-key-here
SERVER_DEBUG=true
```

### 🎮 Executando o Jogo

**Servidor:**
```bash
python main.py -m server
```

**Cliente:**
```bash
python main.py -m client
```

### 📦 Downloads dos Executáveis

O projeto oferece builds automáticos para múltiplas plataformas via GitHub Releases:

- **Windows**: `bomb.exe` - Executável standalone
- **Linux**: `bomb-linux` - Binário para distribuições Linux
- **macOS**: `bomb-macos` - Aplicação para sistemas Apple

> **Nota**: Os executáveis são gerados automaticamente via GitHub Actions a cada tag de release (`v*`)

### 🐳 Docker Deployment

O projeto inclui configuração completa para deployment via Docker:

```bash
# Build da imagem
docker build -t bombinsper:latest .

# Execução com volume persistente
docker run -d \
  --name bombinsper-server \
  -p 8000:8000 \
  -e SERVER_SECRET_KEY=your-secret-key \
  -v bomb_db:/app \
  bombinsper:latest
```

## 🎮 Como Jogar

### 🎯 Controles
- **Setas (↑↓←→)**: Movimento do personagem
- **Espaço**: Colocar bomba
- **ESC/Enter**: Sair da partida

### 📈 Mecânicas do Jogo

1. **Matchmaking**: Entre na fila e aguarde um oponente
2. **Movimento**: Navegue pelo mapa evitando obstáculos
3. **Bombas**: Coloque bombas estrategicamente (2 segundos para explosão)
4. **Explosões**: Raio de 3 tiles em cruz, destrói blocos e elimina jogadores
5. **Vitória**: Seja o último jogador sobrevivente

### 🏆 Sistema de Pontuação
- **Vitórias**: Registradas no leaderboard global
- **Estatísticas**: Bombas colocadas, kills, tempo de partida
- **Ranking**: Sistema de classificação baseado em vitórias

## 🛠️ Tecnologias Utilizadas

### 🖥️ Backend
- **FastAPI**: Framework web assíncrono
- **Prisma**: ORM moderno para Python
- **WebSockets**: Comunicação real-time
- **JWT**: Autenticação segura
- **PostgreSQL/SQLite**: Banco de dados
- **Uvicorn**: Servidor ASGI

### 🎨 Frontend
- **Pygame**: Engine de jogo 2D
- **Pydantic**: Validação de dados
- **asyncio**: Programação assíncrona
- **gzip**: Compressão de estado

### 🚀 DevOps
- **Docker**: Containerização
- **GitHub Actions**: CI/CD automatizado
- **PyInstaller**: Geração de executáveis
- **Self-hosted runners**: Deploy automático

## 🔧 CI/CD Pipeline

O projeto possui dois workflows automatizados via GitHub Actions:

### 🚀 Deploy Workflow (`deploy.yml`)
1. **Trigger**: Push para branch `main`
2. **Build**: Criação da imagem Docker
3. **Deploy**: Deployment automático em servidor self-hosted
4. **Health Check**: Verificação de saúde do serviço

### 📦 Build & Release Workflow (`build.yml`)
1. **Trigger**: Push de tags `v*`
2. **Multi-Platform Build**: 
   - **Windows**: `bomb.exe` via PyInstaller
   - **Linux**: `bomb-linux` via PyInstaller + binutils
   - **macOS**: `bomb-macos` via PyInstaller
3. **Assets Bundle**: Inclusão automática de `client/assets`
4. **GitHub Release**: Publicação automática dos executáveis

### 📁 Configuração do Deploy
- **Dockerfile**: Multi-stage build otimizado
- **Volume persistente**: `bomb_db` para dados
- **Variáveis**: `EXTERNAL_PORT` e `SERVER_SECRET_KEY`
- **Auto-restart**: Container reinicia automaticamente

## 🌐 API Endpoints

### 🔐 Autenticação
- `POST /api/auth/register`: Registro de usuário
- `POST /api/auth/login`: Login e obtenção de token
- `GET /api/auth/me`: Informações do usuário atual

### 🎮 Jogo
- `GET /api/match/{match_id}/stats`: Estatísticas da partida
- `WS /ws/matchmaking`: WebSocket para matchmaking
- `WS /ws/game/{game_id}`: WebSocket para gameplay
- `WS /ws/leaderboard`: WebSocket para leaderboard real-time

## 🎨 Assets e Design

### 🎭 Personagens
- **Carlitos Player**: Sprites animados com 4 direções
- **Rogério Player**: Alternativa visual para o segundo jogador

### 🧱 Blocos
- **Areia**: Bloco destrutível básico
- **Caixa**: Obstáculo de madeira
- **Metal**: Bloco indestrutível
- **Diamante**: Decoração especial

### 💥 Efeitos
- **Bomba**: 5 frames de animação progressiva
- **Explosão**: Sistema de partículas (core, tail, tip)
- **Interpolação**: Movimento suave entre posições

## 📊 Métricas e Otimizações

### 🚀 Performance
- **Compressão de Estado**: Redução de 70-90% no tráfego de rede
- **Event Prioritization**: Sistema de priorização de eventos críticos
- **Movement Throttling**: Limitação de spam de movimentos (20 FPS)
- **Cache de Assets**: Pré-carregamento para melhor performance

### 📈 Monitoramento
- **FPS Counter**: Indicador de performance visual
- **Ping Indicator**: Latência de rede em tempo real
- **Connection Quality**: Qualidade da conexão (Excelente/Boa/Regular/Ruim)
- **Event Metrics**: Contadores de eventos processados

## 🧪 Debugging e Desenvolvimento

### 🔍 Ferramentas
- **icecream**: Debug logging elegante
- **Hot Reload**: Recarga automática durante desenvolvimento
- **Error Handling**: Sistema robusto de tratamento de erros
- **Graceful Degradation**: Fallbacks para perda de conexão

### 📝 Logging
- **Structured Logging**: Logs organizados por módulo
- **Performance Metrics**: Métricas de tempo de processamento
- **Error Tracking**: Rastreamento detalhado de erros

## 🤝 Contribuição

Este projeto foi desenvolvido como parte de um trabalho acadêmico no Insper. Para contribuir:

1. Fork o repositório
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Abra um Pull Request

## 📄 Licença

Projeto acadêmico - Insper Instituto de Ensino e Pesquisa.

---

**Desenvolvido com ❤️ para a disciplina Developer Life**