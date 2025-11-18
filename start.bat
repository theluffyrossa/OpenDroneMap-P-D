@echo off
echo ========================================
echo  OpenDroneMap Micro Sistema - Iniciando
echo ========================================

where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERRO] Docker nao esta instalado. Por favor, instale o Docker Desktop.
    pause
    exit /b 1
)

where docker-compose >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERRO] Docker Compose nao esta instalado.
    pause
    exit /b 1
)

if not exist ".env" (
    echo [INFO] Criando arquivo .env...
    copy .env.example .env
    echo [OK] Arquivo .env criado. Edite as configuracoes se necessario.
)

echo.
echo [INFO] Construindo imagens Docker...
docker-compose build

echo.
echo [INFO] Iniciando servicos...
docker-compose up -d

echo.
echo [INFO] Aguardando servicos iniciarem...
timeout /t 10 /nobreak > nul

echo.
echo [INFO] Verificando status dos servicos...
docker-compose ps

echo.
echo ========================================
echo  Sistema iniciado com sucesso!
echo ========================================
echo.
echo Acesse o sistema em:
echo   - http://localhost:8000 (API)
echo   - http://localhost (Nginx)
echo.
echo NodeODM Dashboard:
echo   - http://localhost:3000
echo.
echo Para parar o sistema:
echo   docker-compose down
echo.
echo Para ver os logs:
echo   docker-compose logs -f
echo ========================================
pause