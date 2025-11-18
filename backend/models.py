from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from enum import Enum

Base = declarative_base()


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingQuality(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(100), unique=True, index=True)
    name = Column(String(255))
    description = Column(Text, nullable=True)
    status = Column(String(50), default=ProcessingStatus.PENDING)
    quality = Column(String(20), default=ProcessingQuality.MEDIUM)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    total_images = Column(Integer, default=0)
    processed_area = Column(Float, nullable=True)
    processing_time = Column(Float, nullable=True)

    orthophoto_path = Column(String(500), nullable=True)
    dem_path = Column(String(500), nullable=True)
    pointcloud_path = Column(String(500), nullable=True)
    textured_model_path = Column(String(500), nullable=True)

    error_message = Column(Text, nullable=True)
    processing_options = Column(Text, nullable=True)

    progress = Column(Integer, default=0)
    console_output = Column(Text, nullable=True)


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    quality: ProcessingQuality = ProcessingQuality.MEDIUM
    options: Optional[Dict] = None


class ProjectResponse(BaseModel):
    id: int
    task_id: str
    name: str
    description: Optional[str]
    status: ProcessingStatus
    quality: ProcessingQuality
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    total_images: int
    processed_area: Optional[float]
    processing_time: Optional[float]
    progress: int
    error_message: Optional[str]

    class Config:
        from_attributes = True


class ProcessingOptions(BaseModel):
    quality: ProcessingQuality = ProcessingQuality.MEDIUM
    feature_quality: str = "high"
    mesh_size: int = 200000
    dsm: bool = True
    dtm: bool = True
    orthophoto_resolution: float = 5.0
    min_num_features: int = 8000
    pc_classify: bool = False
    pc_rectify: bool = False
    use_3dmesh: bool = False
    auto_boundary: bool = True
    fast_orthophoto: bool = False
    optimize_disk_space: bool = False


class UploadResponse(BaseModel):
    task_id: str
    uploaded_files: List[str]
    total_files: int
    message: str


class StatusResponse(BaseModel):
    task_id: str
    status: ProcessingStatus
    progress: int
    message: str
    created_at: datetime
    updated_at: datetime
    processing_time: Optional[float]
    console_output: Optional[List[str]]


class ResultsResponse(BaseModel):
    task_id: str
    status: ProcessingStatus
    orthophoto_url: Optional[str]
    dem_url: Optional[str]
    pointcloud_url: Optional[str]
    textured_model_url: Optional[str]
    processed_area: Optional[float]
    processing_time: Optional[float]
    download_all_url: Optional[str]


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    status_code: int = 400