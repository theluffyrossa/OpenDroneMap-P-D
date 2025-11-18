import os
import shutil
import hashlib
import zipfile
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image
import logging

logger = logging.getLogger(__name__)


def generate_task_id() -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    random_part = hashlib.md5(os.urandom(16)).hexdigest()[:8]
    return f"task_{timestamp}_{random_part}"


def create_project_directory(task_id: str, base_path: str = "./backend/uploads") -> str:
    project_path = os.path.join(base_path, task_id)
    os.makedirs(project_path, exist_ok=True)
    os.makedirs(os.path.join(project_path, "images"), exist_ok=True)
    os.makedirs(os.path.join(project_path, "results"), exist_ok=True)
    return project_path


def validate_image_file(file_path: str) -> Tuple[bool, str]:
    try:
        valid_extensions = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp'}
        file_ext = Path(file_path).suffix.lower()

        if file_ext not in valid_extensions:
            return False, f"Invalid file extension: {file_ext}"

        try:
            with Image.open(file_path) as img:
                img.verify()

            with Image.open(file_path) as img:
                width, height = img.size
                if width < 100 or height < 100:
                    return False, f"Image too small: {width}x{height}"
                if width > 10000 or height > 10000:
                    return False, f"Image too large: {width}x{height}"

        except Exception as e:
            return False, f"Invalid image file: {str(e)}"

        file_size = os.path.getsize(file_path)
        if file_size > 100 * 1024 * 1024:
            return False, f"File too large: {file_size / (1024*1024):.2f}MB"

        return True, "Valid image"

    except Exception as e:
        logger.error(f"Error validating image: {str(e)}")
        return False, f"Validation error: {str(e)}"


def get_image_metadata(file_path: str) -> dict:
    try:
        with Image.open(file_path) as img:
            exif_data = img._getexif() if hasattr(img, '_getexif') else None

            metadata = {
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "mode": img.mode,
                "size_mb": os.path.getsize(file_path) / (1024 * 1024),
                "has_gps": False,
                "latitude": None,
                "longitude": None,
                "altitude": None,
                "camera_make": None,
                "camera_model": None,
                "datetime": None
            }

            if exif_data:
                from PIL.ExifTags import TAGS, GPSTAGS

                for tag, value in exif_data.items():
                    tag_name = TAGS.get(tag, tag)

                    if tag_name == 'DateTime':
                        metadata['datetime'] = value
                    elif tag_name == 'Make':
                        metadata['camera_make'] = value
                    elif tag_name == 'Model':
                        metadata['camera_model'] = value
                    elif tag_name == 'GPSInfo':
                        gps_data = {}
                        for gps_tag, gps_value in value.items():
                            gps_tag_name = GPSTAGS.get(gps_tag, gps_tag)
                            gps_data[gps_tag_name] = gps_value

                        if 'GPSLatitude' in gps_data and 'GPSLongitude' in gps_data:
                            metadata['has_gps'] = True
                            metadata['latitude'] = convert_gps_to_decimal(
                                gps_data['GPSLatitude'],
                                gps_data.get('GPSLatitudeRef', 'N')
                            )
                            metadata['longitude'] = convert_gps_to_decimal(
                                gps_data['GPSLongitude'],
                                gps_data.get('GPSLongitudeRef', 'E')
                            )
                            if 'GPSAltitude' in gps_data:
                                metadata['altitude'] = float(gps_data['GPSAltitude'])

            return metadata

    except Exception as e:
        logger.error(f"Error extracting metadata: {str(e)}")
        return {
            "error": str(e),
            "width": 0,
            "height": 0,
            "format": "unknown"
        }


def convert_gps_to_decimal(gps_coords: tuple, ref: str) -> float:
    degrees = float(gps_coords[0])
    minutes = float(gps_coords[1]) / 60.0
    seconds = float(gps_coords[2]) / 3600.0

    decimal = degrees + minutes + seconds

    if ref in ['S', 'W']:
        decimal = -decimal

    return decimal


def cleanup_old_files(base_path: str, days: int = 7):
    try:
        cutoff_date = datetime.now() - timedelta(days=days)

        for root, dirs, files in os.walk(base_path):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                if os.path.getctime(dir_path) < cutoff_date.timestamp():
                    try:
                        shutil.rmtree(dir_path)
                        logger.info(f"Deleted old directory: {dir_path}")
                    except Exception as e:
                        logger.error(f"Error deleting directory {dir_path}: {str(e)}")

    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")


def create_results_zip(task_id: str, results_path: str) -> Optional[str]:
    try:
        zip_path = os.path.join(results_path, f"{task_id}_results.zip")

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(results_path):
                for file in files:
                    if file.endswith('.zip'):
                        continue
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, results_path)
                    zipf.write(file_path, arcname)

        return zip_path

    except Exception as e:
        logger.error(f"Error creating zip file: {str(e)}")
        return None


def calculate_processing_time(start_time: datetime, end_time: datetime = None) -> float:
    if end_time is None:
        end_time = datetime.utcnow()
    delta = end_time - start_time
    return delta.total_seconds()


def format_file_size(size_bytes: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def estimate_processing_time(num_images: int, quality: str) -> int:
    base_time_per_image = {
        "low": 30,
        "medium": 60,
        "high": 120,
        "ultra": 180
    }

    base_time = base_time_per_image.get(quality, 60)
    estimated_seconds = num_images * base_time

    estimated_seconds = min(estimated_seconds, 7200)

    return estimated_seconds


def get_odm_options_from_quality(quality: str) -> dict:
    options_map = {
        "low": {
            "feature-quality": "low",
            "mesh-size": 100000,
            "min-num-features": 5000,
            "orthophoto-resolution": 10,
            "fast-orthophoto": True,
            "optimize-disk-space": True
        },
        "medium": {
            "feature-quality": "medium",
            "mesh-size": 200000,
            "min-num-features": 8000,
            "orthophoto-resolution": 5,
            "fast-orthophoto": False,
            "optimize-disk-space": False
        },
        "high": {
            "feature-quality": "high",
            "mesh-size": 400000,
            "min-num-features": 10000,
            "orthophoto-resolution": 2,
            "fast-orthophoto": False,
            "optimize-disk-space": False,
            "pc-quality": "high"
        },
        "ultra": {
            "feature-quality": "ultra",
            "mesh-size": 600000,
            "min-num-features": 15000,
            "orthophoto-resolution": 1,
            "fast-orthophoto": False,
            "optimize-disk-space": False,
            "pc-quality": "ultra",
            "use-3dmesh": True
        }
    }

    return options_map.get(quality, options_map["medium"])