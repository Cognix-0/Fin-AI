"""
Receipt file storage on the local filesystem.

Files are saved under `settings.upload_dir` with random names, so user-supplied
filenames never touch the filesystem. The real type is detected from the
file's magic bytes rather than trusted from the client.
"""
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import UploadFile, status

from app.core.config import settings
from app.core.errors import AppError

# (magic prefix, content type, extension)
_SIGNATURES: list[tuple[bytes, str, str]] = [
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
    (b"%PDF-", "application/pdf", ".pdf"),
]

_CHUNK = 64 * 1024
DEMO_PREFIX = "demo/"     # shared sample files from seed_demo; never deleted


def detect_type(head: bytes) -> Optional[tuple[str, str]]:
    for magic, ctype, ext in _SIGNATURES:
        if head.startswith(magic):
            return ctype, ext
    # WebP: "RIFF" <4 bytes size> "WEBP"
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None


def _safe_display_name(name: Optional[str], ext: str) -> str:
    base = os.path.basename(name or "").strip() or f"receipt{ext}"
    # Keep it printable and bounded; it's only ever shown back to users
    base = "".join(ch for ch in base if ch.isprintable() and ch not in '"\\/')
    return base[:200] or f"receipt{ext}"


class ReceiptStorage:
    def __init__(self, root: Path | None = None, max_bytes: int | None = None):
        self.root = Path(root or settings.upload_dir).resolve()
        self.max_bytes = max_bytes or settings.max_receipt_bytes

    def ensure_root(self) -> None:
        (self.root / "receipts").mkdir(parents=True, exist_ok=True)

    async def save(self, upload: UploadFile) -> dict:
        """Validate and persist an upload. Returns metadata for the Expense row."""
        self.ensure_root()
        head = await upload.read(16)
        detected = detect_type(head)
        if not detected:
            raise AppError(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                "UNSUPPORTED_FILE_TYPE",
                "Receipt must be an image (PNG, JPG, WebP) or a PDF",
            )
        content_type, ext = detected

        rel_path = f"receipts/{uuid.uuid4().hex}{ext}"
        dest = self.root / rel_path
        size = len(head)
        try:
            with open(dest, "wb") as fh:
                fh.write(head)
                while chunk := await upload.read(_CHUNK):
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise AppError(
                            413,
                            "FILE_TOO_LARGE",
                            f"Receipt must be {self.max_bytes // (1024 * 1024)} MB or smaller",
                        )
                    fh.write(chunk)
        except BaseException:
            dest.unlink(missing_ok=True)
            raise

        return {
            "receipt_path": rel_path,
            "receipt_filename": _safe_display_name(upload.filename, ext),
            "receipt_content_type": content_type,
            "receipt_size": size,
        }

    def resolve(self, rel_path: str) -> Path:
        path = (self.root / rel_path).resolve()
        # Defence in depth: never serve anything outside the upload root
        if self.root not in path.parents:
            raise AppError(status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Receipt not found")
        return path

    def delete(self, rel_path: Optional[str]) -> None:
        if not rel_path or rel_path.startswith(DEMO_PREFIX):
            return
        try:
            self.resolve(rel_path).unlink(missing_ok=True)
        except AppError:
            pass


def get_receipt_storage() -> ReceiptStorage:
    return ReceiptStorage()
