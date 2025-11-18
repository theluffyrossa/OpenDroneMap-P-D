# 🚁 Guia de Configuração - OpenDroneMap Micro Sistema

## Índice
1. [Requisitos](#requisitos)
2. [Instalação Rápida com Docker](#instalação-rápida-com-docker)
3. [Instalação para Desenvolvimento Local](#instalação-para-desenvolvimento-local)
4. [Configuração](#configuração)
5. [Primeiro Uso](#primeiro-uso)
6. [Solução de Problemas](#solução-de-problemas)

## Requisitos

### Mínimos
- **CPU**: 4 cores
- **RAM**: 8GB
- **Disco**: 20GB livres
- **SO**: Windows 10/11, Linux, macOS

### Software Necessário

#### Para uso com Docker (Recomendado)
- Docker Desktop (Windows/Mac) ou Docker Engine (Linux)
- Docker Compose

#### Para desenvolvimento local
- Python 3.8+
- Node.js (opcional, para NodeODM local)

## Instalação Rápida com Docker

### Windows

1. **Instale o Docker Desktop**
   - Download: https://www.docker.com/products/docker-desktop/
   - Reinicie o computador após instalação

2. **Clone ou baixe o projeto**
   ```cmd
   git clone https://github.com/seu-usuario/OpenDroneMap-P&D.git
   cd OpenDroneMap-P&D
   ```

3. **Configure o ambiente**
   ```cmd
   copy .env.example .env
   ```

4. **Inicie o sistema**
   ```cmd
   start.bat
   ```
   Ou manualmente:
   ```cmd
   docker-compose up -d
   ```

### Linux/macOS

1. **Instale Docker e Docker Compose**
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install docker.io docker-compose

   # macOS (com Homebrew)
   brew install docker docker-compose
   ```

2. **Clone o projeto**
   ```bash
   git clone https://github.com/seu-usuario/OpenDroneMap-P&D.git
   cd OpenDroneMap-P&D
   ```

3. **Configure e inicie**
   ```bash
   cp .env.example .env
   chmod +x start.sh
   ./start.sh
   ```

## Instalação para Desenvolvimento Local

### 1. Prepare o ambiente Python

#### Windows
```cmd
python -m venv venv
venv\Scripts\activate
cd backend
pip install -r requirements.txt
```

#### Linux/macOS
```bash
python3 -m venv venv
source venv/bin/activate
cd backend
pip install -r requirements.txt
```

### 2. Instale e configure NodeODM

#### Opção A: Via Docker (Recomendado)
```bash
docker run -p 3000:3000 opendronemap/nodeodm
```

#### Opção B: Instalação nativa
```bash
git clone https://github.com/OpenDroneMap/NodeODM
cd NodeODM
npm install
node index.js
```

### 3. Configure o arquivo .env

Edite o arquivo `.env` com suas configurações:

```env
# Configuração local
ODM_NODE_HOST=localhost
ODM_NODE_PORT=3000
API_PORT=8000
```

### 4. Execute o sistema

```bash
# Terminal 1: NodeODM (se não estiver usando Docker)
cd NodeODM && node index.js

# Terminal 2: Backend
cd backend
python app.py

# Acesse: http://localhost:8000
```

## Configuração

### Variáveis de Ambiente Importantes

| Variável | Descrição | Valor Padrão |
|----------|-----------|--------------|
| `ODM_NODE_HOST` | Host do NodeODM | `localhost` |
| `ODM_NODE_PORT` | Porta do NodeODM | `3000` |
| `MAX_UPLOAD_SIZE` | Tamanho máximo de upload | `524288000` (500MB) |
| `MAX_IMAGES` | Máximo de imagens por projeto | `50` |
| `PROCESSING_TIMEOUT` | Timeout de processamento | `1800` (30 min) |

### Configuração de Qualidade

No arquivo `.env`, ajuste as configurações de processamento:

```env
# Qualidade baixa (teste rápido)
DEFAULT_QUALITY=low

# Qualidade média (padrão)
DEFAULT_QUALITY=medium

# Qualidade alta (melhor resultado)
DEFAULT_QUALITY=high
```

## Primeiro Uso

### 1. Verifique a instalação

```bash
# Windows
python test_local.py

# Linux/macOS
python3 test_local.py
```

### 2. Acesse o sistema

Abra o navegador em:
- Sistema principal: http://localhost:8000
- NodeODM Dashboard: http://localhost:3000

### 3. Faça seu primeiro processamento

1. Clique em "Upload" no menu
2. Selecione ou arraste pelo menos 20 imagens de drone
3. Configure as opções de processamento:
   - **Qualidade**: Comece com "Baixa" para testes
   - **DSM/DTM**: Mantenha habilitado
   - **Resolução**: 5 cm/pixel é um bom padrão
4. Clique em "Iniciar Upload e Processamento"
5. Aguarde o processamento (pode levar 5-30 minutos)
6. Veja os resultados em "Visualizador"

## Solução de Problemas

### Erro: "Docker não está instalado"
**Solução**: Instale o Docker Desktop e reinicie o computador

### Erro: "NodeODM connection failed"
**Solução**:
```bash
# Verifique se o NodeODM está rodando
docker ps | grep nodeodm

# Se não estiver, inicie manualmente
docker run -p 3000:3000 opendronemap/nodeodm
```

### Erro: "Insufficient memory"
**Solução**:
1. Aumente a memória do Docker Desktop (Settings > Resources)
2. Reduza o número de imagens ou qualidade

### Upload falha com imagens grandes
**Solução**:
1. Comprima as imagens antes do upload
2. Aumente `MAX_UPLOAD_SIZE` no `.env`

### Processamento muito lento
**Soluções**:
1. Use qualidade "baixa" para testes
2. Processe menos imagens (20-30 para teste)
3. Aumente recursos do Docker

### Sistema não inicia no Windows
**Solução**:
1. Execute como Administrador
2. Verifique se o WSL2 está habilitado
3. Desative temporariamente o antivírus

### Porta já em uso
**Solução**:
```bash
# Mude a porta no .env
API_PORT=8001

# Ou pare o serviço usando a porta
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

## Comandos Úteis

### Docker
```bash
# Ver logs
docker-compose logs -f

# Parar sistema
docker-compose down

# Limpar tudo
docker-compose down -v

# Reconstruir
docker-compose build --no-cache

# Ver status
docker-compose ps
```

### Desenvolvimento
```bash
# Instalar nova dependência
pip install <package>
pip freeze > requirements.txt

# Executar testes
python test_local.py

# Limpar arquivos antigos
rm -rf backend/uploads/* results/*
```

## Suporte

### Documentação
- OpenDroneMap: https://docs.opendronemap.org/
- NodeODM API: https://github.com/OpenDroneMap/NodeODM/blob/master/docs/index.adoc
- FastAPI: https://fastapi.tiangolo.com/

### Problemas Comuns
1. **Memória insuficiente**: Reduza número de imagens ou qualidade
2. **Processamento falha**: Verifique logs em `docker-compose logs nodeodm`
3. **Upload lento**: Use menos imagens ou comprima antes
4. **Resultados ruins**: Use mais imagens com maior sobreposição (70%+)

### Dicas de Performance
1. Use SSD para melhor performance
2. Processe em lotes menores (20-50 imagens)
3. Mantenha 70-80% de sobreposição entre imagens
4. Use imagens com boa iluminação e qualidade

## Próximos Passos

Após configurar com sucesso:
1. Leia o README.md para entender o sistema
2. Teste com diferentes conjuntos de imagens
3. Ajuste configurações de qualidade conforme necessário
4. Explore a API em http://localhost:8000/docs