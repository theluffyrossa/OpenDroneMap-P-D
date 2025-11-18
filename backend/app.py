from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from typing import List, Optional, Dict
from pathlib import Path
import os
import json
import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from sqlalchemy.orm import Session
from database import get_db, init_db
from models import (
    Project, ProjectCreate, ProjectResponse,
    ProcessingStatus, ProcessingOptions,
    UploadResponse, StatusResponse, ResultsResponse, ErrorResponse
)
from utils import (
    generate_task_id, create_project_directory,
    validate_image_file, get_image_metadata,
    cleanup_old_files, create_results_zip,
    calculate_processing_time, estimate_processing_time,
    get_odm_options_from_quality
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Database initialized")

    cleanup_task = asyncio.create_task(periodic_cleanup())

    yield

    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="OpenDroneMap Micro Sistema",
    description="Sistema de geoprocessamento para imagens de drone",
    version="1.0.0",
    lifespan=lifespan
)

origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

uploads_path = Path(__file__).parent / "uploads"
uploads_path.mkdir(exist_ok=True)

results_path = Path(__file__).parent.parent / "results"
results_path.mkdir(exist_ok=True)

active_websockets: Dict[str, List[WebSocket]] = {}


async def periodic_cleanup():
    while True:
        try:
            await asyncio.sleep(86400)
            cleanup_old_files(str(uploads_path), days=7)
            cleanup_old_files(str(results_path), days=30)
            logger.info("Periodic cleanup completed")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {str(e)}")


@app.get("/")
async def read_root():
    index_file = frontend_path / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "OpenDroneMap Micro Sistema API", "version": "1.0.0"}


@app.post("/api/upload", response_model=UploadResponse)
async def upload_images(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    if len(files) > int(os.getenv("MAX_IMAGES", 50)):
        raise HTTPException(
            status_code=400,
            detail=f"Too many images. Maximum allowed: {os.getenv('MAX_IMAGES', 50)}"
        )

    task_id = generate_task_id()
    project_dir = create_project_directory(task_id, str(uploads_path))
    images_dir = Path(project_dir) / "images"

    uploaded_files = []
    total_size = 0
    max_size = int(os.getenv("MAX_UPLOAD_SIZE", 524288000))

    for file in files:
        file_size = 0
        file_path = images_dir / file.filename

        try:
            with open(file_path, "wb") as f:
                while chunk := await file.read(8192):
                    file_size += len(chunk)
                    total_size += len(chunk)

                    if total_size > max_size:
                        raise HTTPException(
                            status_code=413,
                            detail=f"Total upload size exceeds maximum allowed: {max_size / (1024*1024):.2f}MB"
                        )

                    f.write(chunk)

            is_valid, message = validate_image_file(str(file_path))
            if not is_valid:
                os.remove(file_path)
                logger.warning(f"Invalid image {file.filename}: {message}")
                continue

            uploaded_files.append(file.filename)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error uploading {file.filename}: {str(e)}")
            if file_path.exists():
                os.remove(file_path)
            continue

    if not uploaded_files:
        raise HTTPException(
            status_code=400,
            detail="No valid images were uploaded"
        )

    project = Project(
        task_id=task_id,
        name=f"Project {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        status=ProcessingStatus.PENDING,
        total_images=len(uploaded_files),
        created_at=datetime.utcnow()
    )
    db.add(project)
    db.commit()

    return UploadResponse(
        task_id=task_id,
        uploaded_files=uploaded_files,
        total_files=len(uploaded_files),
        message=f"Successfully uploaded {len(uploaded_files)} images"
    )


@app.post("/api/process/{task_id}")
async def start_processing(
    task_id: str,
    options: ProcessingOptions = ProcessingOptions(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.task_id == task_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status != ProcessingStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start processing. Current status: {project.status}"
        )

    project_dir = uploads_path / task_id
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project files not found")

    images_dir = project_dir / "images"
    image_files = list(images_dir.glob("*"))
    if len(image_files) < 3:
        raise HTTPException(
            status_code=400,
            detail="Minimum 3 images required for processing"
        )

    project.status = ProcessingStatus.PROCESSING
    project.quality = options.quality
    project.processing_options = json.dumps(options.dict())
    project.updated_at = datetime.utcnow()
    db.commit()

    background_tasks.add_task(process_with_odm, task_id, options.dict())

    return {
        "task_id": task_id,
        "status": ProcessingStatus.PROCESSING,
        "message": "Processing started",
        "estimated_time": estimate_processing_time(len(image_files), options.quality)
    }


async def process_with_odm(task_id: str, options: dict):
    from odm_processor import ODMProcessor

    processor = ODMProcessor()
    await processor.process(task_id, options)


@app.get("/api/status/{task_id}", response_model=StatusResponse)
async def get_processing_status(task_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.task_id == task_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    processing_time = None
    if project.status == ProcessingStatus.COMPLETED and project.completed_at:
        processing_time = calculate_processing_time(project.created_at, project.completed_at)
    elif project.status == ProcessingStatus.PROCESSING:
        processing_time = calculate_processing_time(project.created_at)

    console_output = []
    if project.console_output:
        try:
            console_output = json.loads(project.console_output)
        except:
            console_output = project.console_output.split("\n") if project.console_output else []

    return StatusResponse(
        task_id=task_id,
        status=project.status,
        progress=project.progress,
        message=project.error_message if project.status == ProcessingStatus.FAILED else f"Processing: {project.progress}%",
        created_at=project.created_at,
        updated_at=project.updated_at,
        processing_time=processing_time,
        console_output=console_output[-20:] if console_output else None
    )


@app.get("/api/results/{task_id}", response_model=ResultsResponse)
async def get_results(task_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.task_id == task_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status != ProcessingStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Processing not completed. Current status: {project.status}"
        )

    base_url = f"/api/download/{task_id}"

    return ResultsResponse(
        task_id=task_id,
        status=project.status,
        orthophoto_url=f"{base_url}/orthophoto.tif" if project.orthophoto_path else None,
        dem_url=f"{base_url}/dsm.tif" if project.dem_path else None,
        pointcloud_url=f"{base_url}/pointcloud.laz" if project.pointcloud_path else None,
        textured_model_url=f"{base_url}/textured_model.obj" if project.textured_model_path else None,
        processed_area=project.processed_area,
        processing_time=project.processing_time,
        download_all_url=f"{base_url}/all.zip"
    )


@app.get("/api/projects", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    projects = db.query(Project).order_by(Project.created_at.desc()).offset(skip).limit(limit).all()
    return projects


@app.get("/api/download/{task_id}/{file_name}")
async def download_file(task_id: str, file_name: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.task_id == task_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if file_name == "all.zip":
        results_dir = results_path / task_id
        if not results_dir.exists():
            raise HTTPException(status_code=404, detail="Results not found")

        zip_path = create_results_zip(task_id, str(results_dir))
        if zip_path and Path(zip_path).exists():
            return FileResponse(
                zip_path,
                media_type="application/zip",
                filename=f"{task_id}_results.zip"
            )

    file_map = {
        "orthophoto.tif": project.orthophoto_path,
        "dsm.tif": project.dem_path,
        "pointcloud.laz": project.pointcloud_path,
        "textured_model.obj": project.textured_model_path
    }

    file_path = file_map.get(file_name)
    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=file_name
    )


@app.delete("/api/projects/{task_id}")
async def delete_project(task_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.task_id == task_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_upload_dir = uploads_path / task_id
    if project_upload_dir.exists():
        import shutil
        shutil.rmtree(project_upload_dir)

    project_results_dir = results_path / task_id
    if project_results_dir.exists():
        import shutil
        shutil.rmtree(project_results_dir)

    db.delete(project)
    db.commit()

    return {"message": f"Project {task_id} deleted successfully"}


@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await websocket.accept()

    if task_id not in active_websockets:
        active_websockets[task_id] = []
    active_websockets[task_id].append(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_websockets[task_id].remove(websocket)
        if not active_websockets[task_id]:
            del active_websockets[task_id]


async def broadcast_progress(task_id: str, progress_data: dict):
    if task_id in active_websockets:
        disconnected = []
        for websocket in active_websockets[task_id]:
            try:
                await websocket.send_json(progress_data)
            except:
                disconnected.append(websocket)

        for ws in disconnected:
            active_websockets[task_id].remove(ws)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc), "status_code": 500}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )