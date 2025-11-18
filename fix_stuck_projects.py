#!/usr/bin/env python3
"""
Script para corrigir projetos travados em 99%
Verifica o status real no NodeODM e atualiza o banco de dados
"""

import sys
import os
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from database import get_db_context
from models import Project, ProcessingStatus

NODEODM_URL = "http://localhost:3000"

def check_nodeodm_task(task_uuid):
    try:
        response = requests.get(f"{NODEODM_URL}/task/{task_uuid}/info")
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error checking task {task_uuid}: {e}")
    return None

def fix_stuck_projects():
    print("Verificando projetos travados...\n")

    with get_db_context() as db:
        # Find all processing projects
        stuck_projects = db.query(Project).filter(
            Project.status == ProcessingStatus.PROCESSING
        ).all()

        print(f"Encontrados {len(stuck_projects)} projetos em processamento\n")

        for project in stuck_projects:
            print(f"Projeto: {project.task_id}")
            print(f"   Status atual: {project.status}")
            print(f"   Progresso: {project.progress}%")
            print(f"   Imagens: {project.total_images}")

            # Get all NodeODM tasks
            try:
                tasks_response = requests.get(f"{NODEODM_URL}/task/list")
                if tasks_response.status_code != 200:
                    print("   [ERRO] Erro ao conectar com NodeODM\n")
                    continue

                tasks = tasks_response.json()

                # Try to find matching task by name
                matching_task = None
                for task in tasks:
                    task_info = check_nodeodm_task(task['uuid'])
                    if task_info and task_info.get('name') == project.task_id:
                        matching_task = task_info
                        break

                if matching_task:
                    status = matching_task.get('status', {})
                    status_code = status.get('code', 0)
                    error_message = status.get('errorMessage', '')

                    print(f"   NodeODM status code: {status_code}")

                    # Status codes: 30=FAILED, 40=COMPLETED
                    if status_code == 30:
                        print(f"   [FAILED] {error_message}")
                        project.status = ProcessingStatus.FAILED
                        project.error_message = error_message
                        project.progress = 0
                        db.commit()
                        print(f"   [OK] Status atualizado para FAILED\n")

                    elif status_code == 40:
                        print(f"   [OK] COMPLETADO")
                        project.status = ProcessingStatus.COMPLETED
                        project.progress = 100
                        db.commit()
                        print(f"   [OK] Status atualizado para COMPLETED\n")

                    else:
                        print(f"   [WARN] Status desconhecido: {status_code}\n")
                else:
                    print(f"   [WARN] Tarefa nao encontrada no NodeODM\n")

            except Exception as e:
                print(f"   [ERRO] {e}\n")

    print("[OK] Verificacao concluida!")

if __name__ == "__main__":
    fix_stuck_projects()
