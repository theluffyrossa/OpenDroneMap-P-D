#!/bin/bash

echo "🚁 OpenDroneMap Micro Sistema - Iniciando..."
echo "============================================"

if ! command -v docker &> /dev/null; then
    echo "❌ Docker não está instalado. Por favor, instale o Docker primeiro."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose não está instalado. Por favor, instale o Docker Compose primeiro."
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "📝 Criando arquivo .env a partir do template..."
    cp .env.example .env
    echo "✅ Arquivo .env criado. Por favor, edite as configurações se necessário."
fi

echo "📦 Construindo imagens Docker..."
docker-compose build

echo "🚀 Iniciando serviços..."
docker-compose up -d

echo "⏳ Aguardando serviços iniciarem..."
sleep 10

echo "🔍 Verificando status dos serviços..."
docker-compose ps

echo ""
echo "============================================"
echo "✅ Sistema iniciado com sucesso!"
echo ""
echo "🌐 Acesse o sistema em:"
echo "   http://localhost:8000 (via Python)"
echo "   http://localhost (via Nginx)"
echo ""
echo "📊 NodeODM Dashboard:"
echo "   http://localhost:3000"
echo ""
echo "🛑 Para parar o sistema, execute:"
echo "   docker-compose down"
echo ""
echo "📋 Para ver os logs, execute:"
echo "   docker-compose logs -f"
echo "============================================"