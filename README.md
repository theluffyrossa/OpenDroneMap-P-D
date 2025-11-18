# 🚁 OpenDroneMap Micro Sistema de Geoprocessamento

Sistema web para processamento de imagens de drone usando OpenDroneMap (ODM), desenvolvido para testes, aprendizado e P&D.

## 📋 Características

- ✅ Upload de múltiplas imagens de drone (JPG/PNG)
- ✅ Processamento automático com OpenDroneMap
- ✅ Geração de ortomosaico e modelo digital de elevação
- ✅ Visualização interativa de resultados
- ✅ Download de produtos processados (GeoTIFF, nuvem de pontos)
- ✅ Armazenamento e listagem de projetos

## 🚀 Início Rápido

### Pré-requisitos

- Docker e Docker Compose instalados
- Python 3.8+ (para desenvolvimento local)
- Mínimo 8GB RAM disponível
- 20GB de espaço em disco

### Instalação

1. **Clone o repositório**
```bash
git clone https://github.com/seu-usuario/OpenDroneMap-P&D.git
cd OpenDroneMap-P&D
```

2. **Configure as variáveis de ambiente**
```bash
cp .env.example .env
# Edite .env com suas configurações
```

3. **Inicie com Docker Compose**
```bash
docker-compose up -d
```

4. **Acesse o sistema**
```
http://localhost:8000
```

## 🏗️ Estrutura do Projeto

```
OpenDroneMap-P&D/
├── backend/            # API FastAPI
│   ├── app.py         # Aplicação principal
│   ├── odm_processor.py # Integração ODM
│   └── uploads/       # Armazenamento temporário
├── frontend/          # Interface web
│   ├── index.html    # Página principal
│   ├── css/          # Estilos
│   └── js/           # Scripts
├── docker/           # Configurações Docker
├── results/          # Resultados processados
└── README.md         # Este arquivo
```

## 🔧 Desenvolvimento Local

### Backend (FastAPI)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

### Frontend

O frontend é servido automaticamente pelo FastAPI. Para desenvolvimento:
- Edite arquivos em `frontend/`
- Atualize o navegador para ver mudanças

### NodeODM Local

```bash
docker run -p 3000:3000 opendronemap/nodeodm
```

## 📸 Como Usar

### 1. Upload de Imagens

- Clique em "Upload de Imagens" ou arraste arquivos
- Suporta múltiplas imagens JPG/PNG
- Mínimo recomendado: 20 imagens com sobreposição

### 2. Configurar Processamento

Opções disponíveis:
- **Qualidade**: Alta/Média/Baixa
- **Produtos**: Ortomosaico, DEM, Nuvem de pontos
- **Resolução**: Auto ou manual (cm/pixel)

### 3. Visualizar Resultados

- Mapa interativo com ortomosaico
- Download de arquivos GeoTIFF
- Estatísticas do processamento

## 🛠️ API Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/upload` | Upload de imagens |
| POST | `/api/process` | Iniciar processamento |
| GET | `/api/status/{task_id}` | Status do processamento |
| GET | `/api/results/{task_id}` | Obter resultados |
| GET | `/api/projects` | Listar projetos |
| GET | `/api/download/{task_id}/{file}` | Download de arquivo |

## ⚙️ Configurações

### Variáveis de Ambiente (.env)

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# NodeODM Settings
ODM_NODE_HOST=localhost
ODM_NODE_PORT=3000
ODM_NODE_TOKEN=

# Storage
MAX_UPLOAD_SIZE=524288000  # 500MB
RESULTS_PATH=./results
UPLOAD_PATH=./backend/uploads

# Processing
MAX_IMAGES=50
PROCESSING_TIMEOUT=1800  # 30 min
DEFAULT_QUALITY=medium
```

## 📊 Requisitos de Sistema

### Mínimo
- CPU: 4 cores
- RAM: 8GB
- Disco: 20GB livres

### Recomendado
- CPU: 8+ cores
- RAM: 16GB+
- Disco: 50GB+ livres
- GPU: NVIDIA (opcional)

## 🐛 Solução de Problemas

### Erro de memória durante processamento
- Reduza o número de imagens
- Diminua a qualidade de processamento
- Aumente a memória Docker

### Upload falha com imagens grandes
- Verifique MAX_UPLOAD_SIZE no .env
- Comprima imagens antes do upload

### Processamento muito lento
- Use qualidade "baixa" para testes
- Processe menos imagens por vez
- Considere usar GPU

## 📝 Licença

Este projeto é para fins educacionais e de pesquisa.

## 🤝 Contribuindo

1. Fork o projeto
2. Crie sua feature branch (`git checkout -b feature/NovaFuncionalidade`)
3. Commit suas mudanças (`git commit -m 'Add: Nova funcionalidade'`)
4. Push para a branch (`git push origin feature/NovaFuncionalidade`)
5. Abra um Pull Request

## 📚 Recursos Adicionais

- [OpenDroneMap Documentation](https://docs.opendronemap.org/)
- [NodeODM API](https://github.com/OpenDroneMap/NodeODM/blob/master/docs/index.adoc)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Leaflet.js Documentation](https://leafletjs.com/)

## ⚠️ Aviso

Este é um sistema para desenvolvimento e testes. **Não use em produção** sem implementar:
- Autenticação robusta
- Rate limiting
- Backup automático
- Monitoramento
- Segurança adicional