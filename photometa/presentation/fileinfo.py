from __future__ import annotations

from datetime import datetime

from photometa.fileinfo import (
    FileInfo,
)


def format_file_info_report(
    info: FileInfo,
) -> str:

    lines = [
        "FILE",
        "-" * 60,
        f"Name:              {info.name}",
        f"Path:              {info.path}",
        f"Size:              {info.size_human}",
        f"Size bytes:        {info.size_bytes}",
        f"SHA256:            {info.sha256}",
        f"Type:              {info.file_type}",
        f"Format:            {info.format}",
        f"Resolution:        {info.resolution}",
        (
            f"Extension:         "
            f"{info.extension or '(none)'}"
        ),
        f"MIME:              {info.mime_type}",
        "",
        "FILESYSTEM TIMESTAMPS",
        "-" * 60,
        (
            "Modified:          "
            + _format_datetime(
                info.modified_at
            )
        ),
        (
            "Accessed:          "
            + _format_datetime(
                info.accessed_at
            )
        ),
    ]

    if (
        info.metadata_changed_at
        is not None
    ):
        lines.append(
            "Metadata changed:  "
            + _format_datetime(
                info.metadata_changed_at
            )
        )

    if info.created_at is not None:
        lines.append(
            "Created:           "
            + _format_datetime(
                info.created_at
            )
        )

    else:
        lines.append(
            "Created:           "
            "Not exposed by filesystem"
        )

    lines.extend(
        (
            "",
            (
                "Note: filesystem timestamps "
                "are not EXIF capture timestamps."
            ),
        )
    )

    return "\n".join(
        lines
    )


def _format_datetime(
    value: datetime,
) -> str:

    return value.isoformat(
        timespec="seconds"
    )
