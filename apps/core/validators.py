"""Валидаторы безопасности для загружаемых файлов."""

import os
from collections.abc import Collection

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
DOCUMENT_EXTENSIONS = {"pdf", "doc", "docx", "jpg", "jpeg", "png"}
MAX_IMAGE_SIZE_MB = 5
MAX_DOCUMENT_SIZE_MB = 10


def _validate_file(
    file,
    allowed_extensions: Collection[str],
    max_size_mb: int,
    error_type_msg: str,
    error_size_msg: str,
) -> None:
    ext = os.path.splitext(getattr(file, "name", ""))[1].lstrip(".").lower()
    if ext not in allowed_extensions:
        allowed_list = ", ".join(f".{e}" for e in sorted(allowed_extensions))
        raise ValidationError(f"{error_type_msg} ({allowed_list}).")

    size = getattr(file, "size", 0)
    max_bytes = max_size_mb * 1024 * 1024
    if size > max_bytes:
        raise ValidationError(f"{error_size_msg} ({max_size_mb} МБ).")


def validate_image_file(file) -> None:
    """Ограничение форматов (jpg, jpeg, png, webp, gif) и размера изображений (до 5 МБ)."""
    _validate_file(
        file=file,
        allowed_extensions=IMAGE_EXTENSIONS,
        max_size_mb=MAX_IMAGE_SIZE_MB,
        error_type_msg=str(_("Недопустимый формат изображения. Разрешены форматы:")),
        error_size_msg=str(_("Размер изображения превышает максимально допустимый")),
    )


def validate_document_file(file) -> None:
    """Ограничение форматов (pdf, doc, docx, jpg, jpeg, png) и размера документов (до 10 МБ)."""
    _validate_file(
        file=file,
        allowed_extensions=DOCUMENT_EXTENSIONS,
        max_size_mb=MAX_DOCUMENT_SIZE_MB,
        error_type_msg=str(_("Недопустимый формат документа. Разрешены форматы:")),
        error_size_msg=str(_("Размер документа превышает максимально допустимый")),
    )
