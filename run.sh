#!/bin/bash
# Script para rodar o servidor do bot

echo "🤖 Iniciando Bot de Cobrança..."

# Verifica se .env existe
if [ ! -f .env ]; then
    echo "❌ Arquivo .env não encontrado!"
    echo "📋 Copie o .env.example e configure suas credenciais:"
    echo "   cp .env.example .env"
    echo "   nano .env"
    exit 1
fi

# Verifica se virtual environment existe
if [ ! -d "venv" ]; then
    echo "📦 Criando virtual environment..."
    python3 -m venv venv
fi

# Ativa virtual environment
echo "🔧 Ativando virtual environment..."
source venv/bin/activate

# Instala/atualiza dependências
echo "📥 Instalando dependências..."
pip install -r requirements.txt

# Roda servidor
echo "🚀 Iniciando servidor..."
echo "📡 API disponível em: http://localhost:8000"
echo "📚 Documentação em: http://localhost:8000/docs"
echo ""

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000