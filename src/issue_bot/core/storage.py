import re
import struct
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from issue_bot.config import settings

logger = logging.getLogger(__name__)

def sanitize_filename(name: str) -> str:
    """Sanitize filename to prevent directory traversal and illegal characters."""
    basename = Path(name).name
    stem = Path(basename).stem
    ext = Path(basename).suffix
    clean_stem = re.sub(r'[^a-zA-Z0-9_\-]', '_', stem)
    clean_stem = re.sub(r'_+', '_', clean_stem).strip('_')
    clean_ext = re.sub(r'[^a-zA-Z0-9_\.]', '', ext)
    if not clean_stem:
        clean_stem = "unnamed_image"
    return f"{clean_stem}{clean_ext or '.png'}"

def get_target_filepath(original_name: Optional[str] = None, ext: str = ".png") -> Path:
    """
    Generate a collision-resistant timestamped file path in STORAGE_DIR.
    Example: 20260917_121530_screenshot.png
    """
    settings.init_directories()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if original_name:
        sanitized = sanitize_filename(original_name)
        stem = Path(sanitized).stem[:40]
        file_ext = Path(sanitized).suffix or ext
        if file_ext.lower() not in settings.IMAGE_EXTENSIONS:
            file_ext = ext
        candidate_name = f"{timestamp}_{stem}{file_ext}"
    else:
        candidate_name = f"{timestamp}_qa_shot{ext}"

    dest_path = settings.STORAGE_DIR / candidate_name
    counter = 1
    while dest_path.exists():
        dest_path = settings.STORAGE_DIR / f"{dest_path.stem}_{counter}{dest_path.suffix}"
        counter += 1

    return dest_path

def inspect_image_file(file_path: Path) -> Dict[str, Any]:
    """
    Inspect image format, dimensions, and aspect ratio without external heavy libraries
    (pure Python binary header unpacker for PNG, JPEG, and WEBP).
    """
    if not file_path.exists() or file_path.stat().st_size < 100:
        return {"valid": False, "error": "file_too_small_or_missing"}

    size = file_path.stat().st_size
    width, height = 0, 0
    img_type = "unknown"

    try:
        with open(file_path, "rb") as f:
            data = f.read(4096)
            if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
                img_type = "png"
                width, height = struct.unpack(">II", data[16:24])
            elif data.startswith(b"\xff\xd8"):
                img_type = "jpeg"
                f.seek(2)
                full_data = f.read(131072)
                pos = 0
                while pos < len(full_data) - 9:
                    if full_data[pos] == 0xFF:
                        marker = full_data[pos + 1]
                        if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                            height, width = struct.unpack(">HH", full_data[pos + 5:pos + 9])
                            break
                        elif marker in (0xD9, 0xDA):
                            break
                        elif marker not in (0x00, 0xFF):
                            length = struct.unpack(">H", full_data[pos + 2:pos + 4])[0]
                            pos += 2 + length
                            continue
                    pos += 1
            elif data.startswith(b"RIFF") and len(data) >= 30 and data[8:12] == b"WEBP":
                img_type = "webp"
                vp_tag = data[12:16]
                if vp_tag == b"VP8 " and len(data) >= 30:
                    width = struct.unpack("<H", data[26:28])[0] & 0x3FFF
                    height = struct.unpack("<H", data[28:30])[0] & 0x3FFF
                elif vp_tag == b"VP8L" and len(data) >= 25:
                    b1, b2, b3, b4 = data[21], data[22], data[23], data[24]
                    width = 1 + (((b2 & 0x3F) << 8) | b1)
                    height = 1 + (((b4 & 0x0F) << 10) | (b3 << 2) | ((b2 & 0xC0) >> 6))
                elif vp_tag == b"VP8X" and len(data) >= 30:
                    width = 1 + struct.unpack("<I", data[24:27] + b"\x00")[0]
                    height = 1 + struct.unpack("<I", data[27:30] + b"\x00")[0]
    except Exception as e:
        logger.warning(f"Could not parse image header {file_path}: {e}")

    if img_type == "unknown":
        return {"valid": False, "error": "unsupported_or_corrupted_format"}

    if width > 0 and height > 0 and (width < 100 or height < 100):
        return {"valid": False, "error": "dimensions_too_small", "width": width, "height": height}

    aspect_ratio = round(height / width, 2) if width > 0 else 0.0
    is_portrait = height >= width
    return {
        "valid": True,
        "type": img_type,
        "width": width,
        "height": height,
        "aspect_ratio": aspect_ratio,
        "is_portrait": is_portrait,
        "file_size": size
    }
