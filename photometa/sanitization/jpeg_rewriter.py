from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass


class JpegRewriteError(Exception):
    """Base exception for JPEG rewriting errors."""


@dataclass(frozen=True)
class SegmentTransform:
    payload: bytes | None
    reason: str | None = None

    @classmethod
    def preserve(
        cls,
        payload: bytes,
    ) -> "SegmentTransform":

        return cls(
            payload=payload,
        )

    @classmethod
    def remove(
        cls,
        reason: str,
    ) -> "SegmentTransform":

        return cls(
            payload=None,
            reason=reason,
        )

    @classmethod
    def replace(
        cls,
        payload: bytes,
        reason: str,
    ) -> "SegmentTransform":

        return cls(
            payload=payload,
            reason=reason,
        )


@dataclass(frozen=True)
class RewriteChange:
    action: str
    marker: int
    marker_name: str
    offset: int
    original_size: int
    new_size: int
    reason: str


@dataclass(frozen=True)
class RewriteResult:
    data: bytes

    changes: tuple[
        RewriteChange,
        ...
    ]

    trailing_bytes_removed: int

    scan_data_sha256: str


SegmentTransformer = Callable[
    [int, bytes],
    SegmentTransform,
]


STANDALONE_MARKERS = {
    0x01,
    0xD8,
    0xD9,
    *range(
        0xD0,
        0xD8,
    ),
}


TRANSFORMABLE_MARKERS = {
    *range(
        0xE0,
        0xF0,
    ),
    0xFE,
}


def rewrite_jpeg_bytes(
    data: bytes,
    transformer: SegmentTransformer,
    *,
    strip_trailing: bool,
) -> RewriteResult:
    """
    Rewrites a complete JPEG.

    Segment transformation is allowed only
    for APP0-APP15 and COM.

    Entropy-coded image data is never
    decoded or re-encoded.
    """

    if (
        len(data) < 4
        or data[0:2]
        != b"\xFF\xD8"
    ):

        raise JpegRewriteError(
            "File does not begin with "
            "JPEG SOI FF D8."
        )

    output = bytearray(
        data[0:2]
    )

    changes: list[
        RewriteChange
    ] = []

    scan_hasher = (
        hashlib.sha256()
    )

    position = 2

    in_scan = False
    resume_scan = False

    saw_sos = False
    saw_eoi = False

    while position < len(data):

        if in_scan:

            marker_start = data.find(
                b"\xFF",
                position,
            )

            if marker_start == -1:

                raise JpegRewriteError(
                    "JPEG scan data ended "
                    "without a marker."
                )

            scan_data = data[
                position:
                marker_start
            ]

            output += scan_data

            scan_hasher.update(
                scan_data
            )

            code_position = (
                marker_start
            )

            while (
                code_position
                < len(data)
                and data[
                    code_position
                ] == 0xFF
            ):

                code_position += 1

            if (
                code_position
                >= len(data)
            ):

                raise JpegRewriteError(
                    "Truncated marker at "
                    "end of JPEG scan."
                )

            marker = data[
                code_position
            ]

            #
            # Byte stuffing FF00.
            #
            if marker == 0x00:

                raw = data[
                    marker_start:
                    code_position + 1
                ]

                output += raw

                scan_hasher.update(
                    raw
                )

                position = (
                    code_position + 1
                )

                continue

            #
            # Restart markers and TEM.
            #
            if (
                marker == 0x01
                or 0xD0
                <= marker
                <= 0xD7
            ):

                raw = data[
                    marker_start:
                    code_position + 1
                ]

                output += raw

                scan_hasher.update(
                    raw
                )

                position = (
                    code_position + 1
                )

                continue

            in_scan = False

            #
            # DNL can interrupt a scan and
            # then scan data continues.
            #
            resume_scan = (
                marker == 0xDC
            )

            position = (
                marker_start
            )

            continue

        marker_start = (
            position
        )

        if (
            data[position]
            != 0xFF
        ):

            raise JpegRewriteError(
                (
                    "Expected JPEG marker "
                    f"at offset "
                    f"0x{position:08X}."
                )
            )

        code_position = (
            position
        )

        while (
            code_position
            < len(data)
            and data[
                code_position
            ] == 0xFF
        ):

            code_position += 1

        if (
            code_position
            >= len(data)
        ):

            raise JpegRewriteError(
                "Truncated JPEG marker."
            )

        marker = data[
            code_position
        ]

        if marker == 0x00:

            raise JpegRewriteError(
                (
                    "Found FF00 outside "
                    "entropy-coded data at "
                    f"offset "
                    f"0x{marker_start:08X}."
                )
            )

        marker_end = (
            code_position + 1
        )

        if (
            marker
            in STANDALONE_MARKERS
        ):

            raw = data[
                marker_start:
                marker_end
            ]

            output += raw

            position = (
                marker_end
            )

            if marker == 0xD9:

                saw_eoi = True
                break

            continue

        if (
            code_position + 3
            > len(data)
        ):

            raise JpegRewriteError(
                "Truncated JPEG segment "
                "length."
            )

        declared_length = (
            int.from_bytes(
                data[
                    code_position + 1:
                    code_position + 3
                ],
                byteorder="big",
            )
        )

        if declared_length < 2:

            raise JpegRewriteError(
                (
                    "Invalid JPEG segment "
                    f"length "
                    f"{declared_length}."
                )
            )

        segment_end = (
            code_position
            + 1
            + declared_length
        )

        if segment_end > len(data):

            raise JpegRewriteError(
                (
                    "JPEG segment at offset "
                    f"0x{marker_start:08X} "
                    "is truncated."
                )
            )

        payload = data[
            code_position + 3:
            segment_end
        ]

        raw_segment = data[
            marker_start:
            segment_end
        ]

        decision = transformer(
            marker,
            payload,
        )

        changed = (
            decision.payload
            != payload
        )

        if (
            changed
            and marker
            not in TRANSFORMABLE_MARKERS
        ):

            raise JpegRewriteError(
                (
                    "Transformer attempted "
                    "to modify non-metadata "
                    f"marker {_marker_name(marker)}."
                )
            )

        if decision.payload is None:

            reason = (
                decision.reason
                or "metadata removed"
            )

            changes.append(
                RewriteChange(
                    action="removed",
                    marker=marker,
                    marker_name=(
                        _marker_name(
                            marker
                        )
                    ),
                    offset=marker_start,
                    original_size=len(
                        raw_segment
                    ),
                    new_size=0,
                    reason=reason,
                )
            )

        elif changed:

            new_payload = (
                decision.payload
            )

            if len(new_payload) > 65533:

                raise JpegRewriteError(
                    "Transformed JPEG payload "
                    "is too large."
                )

            marker_prefix = data[
                marker_start:
                code_position + 1
            ]

            new_segment = (
                marker_prefix
                + (
                    len(new_payload)
                    + 2
                ).to_bytes(
                    2,
                    "big",
                )
                + new_payload
            )

            output += new_segment

            changes.append(
                RewriteChange(
                    action="modified",
                    marker=marker,
                    marker_name=(
                        _marker_name(
                            marker
                        )
                    ),
                    offset=marker_start,
                    original_size=len(
                        raw_segment
                    ),
                    new_size=len(
                        new_segment
                    ),
                    reason=(
                        decision.reason
                        or "metadata modified"
                    ),
                )
            )

        else:

            output += raw_segment

        position = (
            segment_end
        )

        if marker == 0xDA:

            saw_sos = True
            in_scan = True
            resume_scan = False

        elif (
            resume_scan
            and marker == 0xDC
        ):

            in_scan = True
            resume_scan = False

        else:

            resume_scan = False

    if not saw_sos:

        raise JpegRewriteError(
            "JPEG does not contain "
            "a Start Of Scan marker."
        )

    if not saw_eoi:

        raise JpegRewriteError(
            "JPEG does not contain "
            "an End Of Image marker."
        )

    trailing = data[
        position:
    ]

    if strip_trailing:

        trailing_bytes_removed = (
            len(trailing)
        )

    else:

        output += trailing

        trailing_bytes_removed = 0

    return RewriteResult(
        data=bytes(
            output
        ),
        changes=tuple(
            changes
        ),
        trailing_bytes_removed=(
            trailing_bytes_removed
        ),
        scan_data_sha256=(
            scan_hasher.hexdigest()
        ),
    )


def _marker_name(
    marker: int,
) -> str:

    if (
        0xE0
        <= marker
        <= 0xEF
    ):

        return (
            f"APP"
            f"{marker - 0xE0}"
        )

    if marker == 0xFE:
        return "COM"

    if marker == 0xDA:
        return "SOS"

    if marker == 0xD9:
        return "EOI"

    return (
        f"FF{marker:02X}"
    )
