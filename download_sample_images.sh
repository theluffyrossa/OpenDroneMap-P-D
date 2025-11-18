#!/bin/bash

# Script para baixar imagens de exemplo do OpenDroneMap

echo "Baixando imagens de exemplo do OpenDroneMap..."

# Criar diretório para samples
mkdir -p sample_images
cd sample_images

# Dataset pequeno (Brighton Beach - 25 imagens)
echo "Baixando dataset Brighton Beach (25 imagens)..."
wget https://github.com/OpenDroneMap/ODM/releases/download/v0.3.1/brighton_beach.zip

echo "Extraindo imagens..."
unzip brighton_beach.zip

echo "Pronto! Imagens em: sample_images/brighton_beach/"
echo ""
echo "Para usar:"
echo "1. Acesse http://localhost:8000"
echo "2. Faça upload das imagens da pasta sample_images/brighton_beach/images/"
echo "3. Inicie o processamento"
