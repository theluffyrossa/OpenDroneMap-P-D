import os
import asyncio
import aiofiles
import httpx
import json
import logging
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
from pyodm import Node, exceptions
from sqlalchemy.orm import Session

from database import get_db_context
from models import Project, ProcessingStatus
from utils import get_odm_options_from_quality

logger = logging.getLogger(__name__)


class ODMProcessor:
    def __init__(self):
        self.node_host = os.getenv("ODM_NODE_HOST", "localhost")
        self.node_port = int(os.getenv("ODM_NODE_PORT", 3000))
        self.node_token = os.getenv("ODM_NODE_TOKEN", "")

        try:
            self.node = Node(self.node_host, self.node_port, self.node_token)
            info = self.node.info()
            logger.info(f"Connected to NodeODM: {info}")
        except Exception as e:
            logger.error(f"Failed to connect to NodeODM: {str(e)}")
            self.node = None

    async def process(self, task_id: str, options: dict):
        try:
            with get_db_context() as db:
                project = db.query(Project).filter(Project.task_id == task_id).first()
                if not project:
                    logger.error(f"Project {task_id} not found")
                    return

                project.status = ProcessingStatus.PROCESSING
                project.progress = 0
                project.updated_at = datetime.utcnow()
                db.commit()

            if not self.node:
                await self._update_project_status(
                    task_id,
                    ProcessingStatus.FAILED,
                    error_message="NodeODM connection failed"
                )
                return

            uploads_dir = Path("backend/uploads") / task_id / "images"
            if not uploads_dir.exists():
                await self._update_project_status(
                    task_id,
                    ProcessingStatus.FAILED,
                    error_message="Image files not found"
                )
                return

            image_files = list(uploads_dir.glob("*"))
            if len(image_files) < 3:
                await self._update_project_status(
                    task_id,
                    ProcessingStatus.FAILED,
                    error_message="Insufficient images for processing (minimum 3)"
                )
                return

            quality = options.get("quality", "medium")
            odm_options = get_odm_options_from_quality(quality)

            odm_options.update({
                "dsm": options.get("dsm", True),
                "dtm": options.get("dtm", True),
                "orthophoto-resolution": options.get("orthophoto_resolution", 5.0),
                "min-num-features": options.get("min_num_features", 8000),
                "auto-boundary": options.get("auto_boundary", True),
            })

            logger.info(f"Starting ODM processing for {task_id} with options: {odm_options}")

            task = self.node.create_task(
                files=[str(f) for f in image_files],
                options=odm_options,
                name=task_id
            )

            logger.info(f"Created ODM task {task.uuid} for project {task_id}")

            await self._monitor_task(task_id, task)

        except exceptions.NodeConnectionError as e:
            logger.error(f"NodeODM connection error: {str(e)}")
            await self._update_project_status(
                task_id,
                ProcessingStatus.FAILED,
                error_message=f"Connection error: {str(e)}"
            )
        except exceptions.TaskFailedError as e:
            logger.error(f"ODM task failed: {str(e)}")
            await self._update_project_status(
                task_id,
                ProcessingStatus.FAILED,
                error_message=f"Processing failed: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error processing {task_id}: {str(e)}")
            await self._update_project_status(
                task_id,
                ProcessingStatus.FAILED,
                error_message=f"Unexpected error: {str(e)}"
            )

    async def _monitor_task(self, project_id: str, task):
        last_progress = 0
        console_output = []

        try:
            while True:
                await asyncio.sleep(5)

                try:
                    info = task.info()
                    status = info.status
                    progress = info.progress if hasattr(info, 'progress') else 0

                    if progress != last_progress:
                        await self._update_progress(project_id, progress, console_output)
                        last_progress = progress

                    if hasattr(info, 'output') and info.output:
                        new_lines = info.output[-10:]
                        console_output.extend(new_lines)
                        console_output = console_output[-100:]

                    if status == "completed":
                        logger.info(f"Task {task.uuid} completed successfully")
                        await self._download_results(project_id, task)
                        break

                    elif status == "failed":
                        error_msg = info.last_error if hasattr(info, 'last_error') else "Task failed"
                        logger.error(f"Task {task.uuid} failed: {error_msg}")
                        await self._update_project_status(
                            project_id,
                            ProcessingStatus.FAILED,
                            error_message=error_msg
                        )
                        break

                    elif status == "canceled":
                        logger.info(f"Task {task.uuid} was cancelled")
                        await self._update_project_status(
                            project_id,
                            ProcessingStatus.CANCELLED,
                            error_message="Task cancelled by user"
                        )
                        break

                except Exception as e:
                    logger.error(f"Error monitoring task: {str(e)}")

        except asyncio.CancelledError:
            logger.info(f"Monitoring cancelled for task {task.uuid}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in task monitoring: {str(e)}")
            await self._update_project_status(
                project_id,
                ProcessingStatus.FAILED,
                error_message=f"Monitoring error: {str(e)}"
            )

    async def _download_results(self, project_id: str, task):
        try:
            results_dir = Path("results") / project_id
            results_dir.mkdir(parents=True, exist_ok=True)

            download_paths = {}

            available_assets = task.download_zip(str(results_dir / "all_results.zip"))
            logger.info(f"Downloaded all results to {results_dir}")

            import zipfile
            with zipfile.ZipFile(results_dir / "all_results.zip", 'r') as zip_ref:
                zip_ref.extractall(results_dir)

            if (results_dir / "odm_orthophoto" / "odm_orthophoto.tif").exists():
                download_paths["orthophoto_path"] = str(results_dir / "odm_orthophoto" / "odm_orthophoto.tif")

            if (results_dir / "odm_dem" / "dsm.tif").exists():
                download_paths["dem_path"] = str(results_dir / "odm_dem" / "dsm.tif")

            if (results_dir / "odm_georeferencing" / "odm_georeferenced_model.laz").exists():
                download_paths["pointcloud_path"] = str(results_dir / "odm_georeferencing" / "odm_georeferenced_model.laz")

            if (results_dir / "odm_texturing" / "odm_textured_model_geo.obj").exists():
                download_paths["textured_model_path"] = str(results_dir / "odm_texturing" / "odm_textured_model_geo.obj")

            with get_db_context() as db:
                project = db.query(Project).filter(Project.task_id == project_id).first()
                if project:
                    project.status = ProcessingStatus.COMPLETED
                    project.progress = 100
                    project.completed_at = datetime.utcnow()

                    for key, value in download_paths.items():
                        setattr(project, key, value)

                    if project.created_at and project.completed_at:
                        delta = project.completed_at - project.created_at
                        project.processing_time = delta.total_seconds()

                    db.commit()

            logger.info(f"Successfully downloaded results for project {project_id}")

        except Exception as e:
            logger.error(f"Error downloading results: {str(e)}")
            await self._update_project_status(
                project_id,
                ProcessingStatus.FAILED,
                error_message=f"Failed to download results: {str(e)}"
            )

    async def _update_progress(self, project_id: str, progress: int, console_output: List[str]):
        try:
            with get_db_context() as db:
                project = db.query(Project).filter(Project.task_id == project_id).first()
                if project:
                    project.progress = min(progress, 99)
                    project.updated_at = datetime.utcnow()
                    if console_output:
                        project.console_output = json.dumps(console_output)
                    db.commit()

            from app import broadcast_progress
            await broadcast_progress(project_id, {
                "task_id": project_id,
                "progress": progress,
                "status": "processing",
                "console_output": console_output[-5:] if console_output else []
            })

        except Exception as e:
            logger.error(f"Error updating progress: {str(e)}")

    async def _update_project_status(
        self,
        project_id: str,
        status: ProcessingStatus,
        error_message: Optional[str] = None
    ):
        try:
            with get_db_context() as db:
                project = db.query(Project).filter(Project.task_id == project_id).first()
                if project:
                    project.status = status
                    project.updated_at = datetime.utcnow()

                    if error_message:
                        project.error_message = error_message

                    if status == ProcessingStatus.COMPLETED:
                        project.completed_at = datetime.utcnow()
                        project.progress = 100

                    db.commit()

            from app import broadcast_progress
            await broadcast_progress(project_id, {
                "task_id": project_id,
                "status": status,
                "progress": 100 if status == ProcessingStatus.COMPLETED else project.progress,
                "error": error_message
            })

        except Exception as e:
            logger.error(f"Error updating project status: {str(e)}")