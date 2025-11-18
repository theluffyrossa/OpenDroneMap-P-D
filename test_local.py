#!/usr/bin/env python3
"""
Script de teste para verificar a instalação local do sistema OpenDroneMap
"""

import sys
import os
import subprocess
import time
import requests
import json

def check_python_version():
    print("✓ Verificando versão do Python...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"  Python {version.major}.{version.minor}.{version.micro} ✓")
        return True
    else:
        print(f"  ❌ Python {version.major}.{version.minor} - Requer Python 3.8+")
        return False

def check_dependencies():
    print("\n✓ Verificando dependências Python...")
    try:
        import fastapi
        print("  FastAPI ✓")
        import uvicorn
        print("  Uvicorn ✓")
        import sqlalchemy
        print("  SQLAlchemy ✓")
        import pyodm
        print("  PyODM ✓")
        return True
    except ImportError as e:
        print(f"  ❌ Dependência faltando: {e}")
        print("  Execute: pip install -r backend/requirements.txt")
        return False

def check_docker():
    print("\n✓ Verificando Docker...")
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  {result.stdout.strip()} ✓")
            return True
    except FileNotFoundError:
        pass
    print("  ❌ Docker não instalado")
    return False

def check_docker_compose():
    print("\n✓ Verificando Docker Compose...")
    try:
        result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  {result.stdout.strip()} ✓")
            return True
    except FileNotFoundError:
        pass
    print("  ❌ Docker Compose não instalado")
    return False

def check_directories():
    print("\n✓ Verificando estrutura de diretórios...")
    required_dirs = [
        'backend',
        'backend/uploads',
        'frontend',
        'frontend/css',
        'frontend/js',
        'docker',
        'results'
    ]

    all_exist = True
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"  {dir_path} ✓")
        else:
            print(f"  ❌ {dir_path} não encontrado")
            all_exist = False

    return all_exist

def check_files():
    print("\n✓ Verificando arquivos essenciais...")
    required_files = [
        'backend/app.py',
        'backend/models.py',
        'backend/odm_processor.py',
        'backend/requirements.txt',
        'frontend/index.html',
        'docker-compose.yml',
        '.env.example'
    ]

    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  {file_path} ✓")
        else:
            print(f"  ❌ {file_path} não encontrado")
            all_exist = False

    return all_exist

def check_env_file():
    print("\n✓ Verificando arquivo .env...")
    if os.path.exists('.env'):
        print("  .env existe ✓")
        return True
    elif os.path.exists('.env.example'):
        print("  .env não existe, mas .env.example disponível")
        print("  Execute: cp .env.example .env")
        return False
    else:
        print("  ❌ Nem .env nem .env.example encontrados")
        return False

def test_local_server():
    print("\n✓ Testando servidor local...")
    print("  Iniciando servidor FastAPI...")

    env = os.environ.copy()
    env['PYTHONPATH'] = os.getcwd()

    process = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'backend.app:app', '--host', '0.0.0.0', '--port', '8001'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env
    )

    time.sleep(5)

    try:
        response = requests.get('http://localhost:8001')
        if response.status_code == 200:
            print("  Servidor respondendo ✓")

            response = requests.get('http://localhost:8001/api/projects')
            if response.status_code == 200:
                print("  API endpoint /projects funcionando ✓")

            process.terminate()
            return True
    except requests.exceptions.ConnectionError:
        print("  ❌ Servidor não respondeu")

    process.terminate()
    return False

def check_nodeodm_connection():
    print("\n✓ Verificando conexão com NodeODM...")
    try:
        response = requests.get('http://localhost:3000/info', timeout=5)
        if response.status_code == 200:
            info = response.json()
            print(f"  NodeODM versão {info.get('version', 'unknown')} ✓")
            return True
    except:
        pass

    print("  ⚠ NodeODM não está rodando (normal se usando Docker)")
    return False

def main():
    print("=" * 50)
    print("TESTE DO SISTEMA OPENDRONEMAP MICRO SISTEMA")
    print("=" * 50)

    results = {
        'Python': check_python_version(),
        'Dependências': check_dependencies(),
        'Docker': check_docker(),
        'Docker Compose': check_docker_compose(),
        'Diretórios': check_directories(),
        'Arquivos': check_files(),
        'Arquivo .env': check_env_file(),
    }

    if results['Dependências']:
        results['Servidor Local'] = test_local_server()

    check_nodeodm_connection()

    print("\n" + "=" * 50)
    print("RESUMO DOS TESTES")
    print("=" * 50)

    all_passed = True
    for test, passed in results.items():
        status = "✓" if passed else "❌"
        print(f"{test:20} {status}")
        if not passed:
            all_passed = False

    print("=" * 50)

    if all_passed:
        print("\n✅ TODOS OS TESTES PASSARAM!")
        print("\nPróximos passos:")
        print("1. Se não tiver .env, copie: cp .env.example .env")
        print("2. Para rodar localmente: python backend/app.py")
        print("3. Para rodar com Docker: docker-compose up")
    else:
        print("\n⚠ ALGUNS TESTES FALHARAM")
        print("\nVerifique os erros acima e:")
        print("1. Instale as dependências: pip install -r backend/requirements.txt")
        print("2. Instale Docker Desktop se necessário")
        print("3. Configure o arquivo .env")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())