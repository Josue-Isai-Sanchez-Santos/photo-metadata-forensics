from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from defusedxml import ElementTree as DefusedET
from defusedxml.common import DefusedXmlException

from photometa.analysis.privacy import (
    analyze_privacy,
)
from photometa.extractors.gps_ifd import (
    GpsIfdExtractorError,
    extract_gps_ifd_from_jpeg,
)
from photometa.fileinfo import (
    FileInfoError,
    get_jpeg_dimensions,
)
from photometa.hashing import (
    calculate_sha256,
)
from photometa.parsers.iptc import (
    IPTC_DATASET_MARKER,
    IPTC_RESOURCE_ID,
    PHOTOSHOP_IDENTIFIER,
    PHOTOSHOP_RESOURCE_SIGNATURE,
)
from photometa.parsers.tiff import (
    Ifd,
    IfdEntry,
    TiffParserError,
    get_ifd_entry_data_size,
    parse_ifd,
    parse_tiff_header,
)
from photometa.parsers.xmp import (
    EXTENDED_XMP_IDENTIFIER,
    XMP_IDENTIFIER,
)
from photometa.sanitization.jpeg_rewriter import (
    JpegRewriteError,
    RewriteChange,
    SegmentTransform,
    rewrite_jpeg_bytes,
)
from photometa.sanitization.scrub import (
    ScrubError,
    _atomic_write,
    default_output_path,
)

SCRUB_MODE_GPS = "gps"
SCRUB_MODE_PRIVACY = "privacy"


GPS_IFD_POINTER_TAG = 0x8825
EXIF_IFD_POINTER_TAG = 0x8769


#
# IFD0 fields recognized as privacy-sensitive
# by PhotoMeta.
#
PRIVACY_IFD0_TAGS = {
    0x0110,  # Model
    0x0131,  # Software
    0x013B,  # Artist
    0x8298,  # Copyright
}


#
# ExifIFD privacy fields.
#
PRIVACY_EXIF_IFD_TAGS = {
    0x9003,  # DateTimeOriginal
    0xA420,  # ImageUniqueID
    0xA430,  # CameraOwnerName
    0xA431,  # BodySerialNumber
    0xA435,  # LensSerialNumber
}


#
# IPTC fields removed by --privacy.
#
PRIVACY_IPTC_DATASETS = {
    (2, 55),   # DateCreated
    (2, 60),   # TimeCreated

    (2, 80),   # Byline
    (2, 85),   # BylineTitle

    (2, 90),   # City
    (2, 92),   # Sublocation
    (2, 95),   # ProvinceState

    (2, 100),  # CountryCode
    (2, 101),  # CountryName

    (2, 103),  # OriginalTransmissionReference

    (2, 116),  # CopyrightNotice
    (2, 122),  # WriterEditor
}


PRIVACY_XMP_LOCAL_NAMES = {
    "artist",
    "creator",
    "ownername",

    "creatortool",
    "software",

    "rights",
    "copyright",
    "copyrightnotice",

    "documentid",
    "instanceid",
    "originaldocumentid",
    "identifier",
    "imageuniqueid",

    "serialnumber",
    "cameraserialnumber",
    "lensserialnumber",

    "model",

    "datetimeoriginal",
    "datecreated",
    "createdate",

    "location",
    "sublocation",
    "city",
    "state",
    "provincestate",
    "country",
    "countryname",
    "countrycode",

    "locationcreated",
    "locationshown",

    "hasextendedxmp",
}


@dataclass(frozen=True)
class SelectiveScrubReport:
    mode: str

    input_path: Path
    output_path: Path

    bytes_before: int
    bytes_after: int

    changes: tuple[
        RewriteChange,
        ...
    ]

    trailing_bytes_removed: int

    original_gps: bool
    sanitized_gps: bool

    privacy_findings_before: int
    privacy_findings_after: int

    dimensions_before: tuple[int, int]
    dimensions_after: tuple[int, int]

    original_sha256_before: str
    original_sha256_after: str
    sanitized_sha256: str

    image_data_sha256_before: str
    image_data_sha256_after: str

    @property
    def original_unchanged(
        self,
    ) -> bool:

        return (
            self.original_sha256_before
            == self.original_sha256_after
        )

    @property
    def dimensions_preserved(
        self,
    ) -> bool:

        return (
            self.dimensions_before
            == self.dimensions_after
        )

    @property
    def image_data_preserved(
        self,
    ) -> bool:

        return (
            self.image_data_sha256_before
            == self.image_data_sha256_after
        )

    @property
    def removed_segment_count(
        self,
    ) -> int:

        return sum(
            1
            for change
            in self.changes
            if change.action
            == "removed"
        )

    @property
    def modified_segment_count(
        self,
    ) -> int:

        return sum(
            1
            for change
            in self.changes
            if change.action
            == "modified"
        )

    @property
    def removed_bytes(
        self,
    ) -> int:

        return (
            self.bytes_before
            - self.bytes_after
        )


def scrub_jpeg_selective(
    path: str | Path,
    output: str | Path | None = None,
    *,
    mode: str,
) -> SelectiveScrubReport:

    if mode not in {
        SCRUB_MODE_GPS,
        SCRUB_MODE_PRIVACY,
    }:

        raise ScrubError(
            f"Unsupported selective "
            f"scrub mode: {mode}"
        )

    input_path = Path(
        path
    )

    if not input_path.exists():

        raise ScrubError(
            f"Input file does not exist: "
            f"{input_path}"
        )

    if not input_path.is_file():

        raise ScrubError(
            f"Input path is not a file: "
            f"{input_path}"
        )

    output_path = (
        Path(output)
        if output is not None
        else default_output_path(
            input_path
        )
    )

    input_resolved = (
        input_path.resolve()
    )

    output_resolved = (
        output_path.resolve(
            strict=False
        )
    )

    if (
        input_resolved
        == output_resolved
    ):

        raise ScrubError(
            "Refusing to overwrite "
            "the original file."
        )

    if (
        output_path.exists()
        and os.path.samefile(
            input_path,
            output_path,
        )
    ):

        raise ScrubError(
            "Output refers to the same "
            "file as the input."
        )

    if output_path.exists():

        raise ScrubError(
            f"Output file already exists: "
            f"{output_path}"
        )

    if not output_path.parent.exists():

        raise ScrubError(
            f"Output directory does not exist: "
            f"{output_path.parent}"
        )

    try:

        dimensions_before = (
            get_jpeg_dimensions(
                input_path
            )
        )

    except FileInfoError as exc:

        raise ScrubError(
            "Input JPEG validation "
            f"failed: {exc}"
        ) from exc

    original_sha256_before = (
        calculate_sha256(
            input_path
        )
    )

    original_gps = _has_gps(
        input_path
    )

    privacy_findings_before = (
        _privacy_finding_count(
            input_path
        )
    )

    try:

        original_data = (
            input_path.read_bytes()
        )

    except OSError as exc:

        raise ScrubError(
            "Could not read input file: "
            f"{exc}"
        ) from exc

    try:

        rewrite = rewrite_jpeg_bytes(
            original_data,
            lambda marker, payload: (
                _transform_segment(
                    marker,
                    payload,
                    mode,
                )
            ),
            strip_trailing=(
                mode
                == SCRUB_MODE_PRIVACY
            ),
        )

    except JpegRewriteError as exc:

        raise ScrubError(
            str(exc)
        ) from exc

    #
    # A second scrub must make no changes.
    #
    try:

        verification = rewrite_jpeg_bytes(
            rewrite.data,
            lambda marker, payload: (
                _transform_segment(
                    marker,
                    payload,
                    mode,
                )
            ),
            strip_trailing=(
                mode
                == SCRUB_MODE_PRIVACY
            ),
        )

    except JpegRewriteError as exc:

        raise ScrubError(
            "Selective sanitization "
            f"verification failed: {exc}"
        ) from exc

    if verification.changes:

        raise ScrubError(
            "Selective sanitization is "
            "not idempotent."
        )

    if (
        verification.trailing_bytes_removed
        != 0
    ):

        raise ScrubError(
            "Trailing-data verification "
            "failed."
        )

    if (
        verification.data
        != rewrite.data
    ):

        raise ScrubError(
            "Selective sanitization "
            "changed on second pass."
        )

    if (
        verification.scan_data_sha256
        != rewrite.scan_data_sha256
    ):

        raise ScrubError(
            "Compressed image data changed "
            "during verification."
        )

    _atomic_write(
        output_path,
        rewrite.data,
    )

    try:

        dimensions_after = (
            get_jpeg_dimensions(
                output_path
            )
        )

        sanitized_gps = _has_gps(
            output_path
        )

        privacy_findings_after = (
            _privacy_finding_count(
                output_path
            )
        )

        sanitized_sha256 = (
            calculate_sha256(
                output_path
            )
        )

        original_sha256_after = (
            calculate_sha256(
                input_path
            )
        )

    except Exception as exc:

        output_path.unlink(
            missing_ok=True
        )

        raise ScrubError(
            "Sanitized file verification "
            f"failed: {exc}"
        ) from exc

    if (
        original_sha256_before
        != original_sha256_after
    ):

        output_path.unlink(
            missing_ok=True
        )

        raise ScrubError(
            "Original file changed during "
            "the scrub operation."
        )

    if (
        dimensions_before
        != dimensions_after
    ):

        output_path.unlink(
            missing_ok=True
        )

        raise ScrubError(
            "Image dimensions changed "
            "during sanitization."
        )

    if sanitized_gps:

        output_path.unlink(
            missing_ok=True
        )

        raise ScrubError(
            "GPS metadata is still present "
            "after selective sanitization."
        )

    if (
        mode == SCRUB_MODE_PRIVACY
        and privacy_findings_after
        != 0
    ):

        output_path.unlink(
            missing_ok=True
        )

        raise ScrubError(
            "Supported privacy-sensitive "
            "metadata remains after "
            "sanitization."
        )

    return SelectiveScrubReport(
        mode=mode,
        input_path=input_resolved,
        output_path=(
            output_path.resolve()
        ),
        bytes_before=len(
            original_data
        ),
        bytes_after=len(
            rewrite.data
        ),
        changes=(
            rewrite.changes
        ),
        trailing_bytes_removed=(
            rewrite.trailing_bytes_removed
        ),
        original_gps=(
            original_gps
        ),
        sanitized_gps=(
            sanitized_gps
        ),
        privacy_findings_before=(
            privacy_findings_before
        ),
        privacy_findings_after=(
            privacy_findings_after
        ),
        dimensions_before=(
            dimensions_before
        ),
        dimensions_after=(
            dimensions_after
        ),
        original_sha256_before=(
            original_sha256_before
        ),
        original_sha256_after=(
            original_sha256_after
        ),
        sanitized_sha256=(
            sanitized_sha256
        ),
        image_data_sha256_before=(
            rewrite.scan_data_sha256
        ),
        image_data_sha256_after=(
            verification.scan_data_sha256
        ),
    )


def _transform_segment(
    marker: int,
    payload: bytes,
    mode: str,
) -> SegmentTransform:

    #
    # EXIF.
    #
    if (
        marker == 0xE1
        and payload.startswith(
            b"Exif\x00\x00"
        )
    ):

        sanitized, changed = (
            _sanitize_exif_payload(
                payload,
                mode,
            )
        )

        if not changed:

            return (
                SegmentTransform
                .preserve(
                    payload
                )
            )

        return SegmentTransform.replace(
            sanitized,
            (
                "GPS fields removed "
                "from EXIF"
                if mode
                == SCRUB_MODE_GPS
                else
                "privacy-sensitive fields "
                "removed from EXIF"
            ),
        )

    #
    # Standard XMP.
    #
    if (
        marker == 0xE1
        and payload.startswith(
            XMP_IDENTIFIER
        )
    ):

        sanitized, changed = (
            _sanitize_xmp_payload(
                payload,
                mode,
            )
        )

        if not changed:

            return (
                SegmentTransform
                .preserve(
                    payload
                )
            )

        return SegmentTransform.replace(
            sanitized,
            (
                "GPS fields removed from XMP"
                if mode
                == SCRUB_MODE_GPS
                else
                "privacy-sensitive fields "
                "removed from XMP"
            ),
        )

    #
    # Extended XMP cannot yet be safely
    # reconstructed field-by-field.
    #
    if (
        marker == 0xE1
        and payload.startswith(
            EXTENDED_XMP_IDENTIFIER
        )
    ):

        return SegmentTransform.remove(
            (
                "Extended XMP removed "
                "conservatively during "
                "selective sanitization"
            )
        )

    #
    # IPTC selective privacy filtering.
    #
    if (
        mode == SCRUB_MODE_PRIVACY
        and marker == 0xED
        and payload.startswith(
            PHOTOSHOP_IDENTIFIER
        )
    ):

        sanitized, changed = (
            _sanitize_photoshop_payload(
                payload
            )
        )

        if not changed:

            return (
                SegmentTransform
                .preserve(
                    payload
                )
            )

        return SegmentTransform.replace(
            sanitized,
            (
                "privacy-sensitive IPTC "
                "datasets removed"
            ),
        )

    #
    # JPEG comments are free-form metadata.
    # Privacy mode removes them.
    #
    if (
        mode == SCRUB_MODE_PRIVACY
        and marker == 0xFE
    ):

        return SegmentTransform.remove(
            "JPEG comment removed "
            "in privacy mode"
        )

    return (
        SegmentTransform
        .preserve(
            payload
        )
    )


def _sanitize_exif_payload(
    payload: bytes,
    mode: str,
) -> tuple[
    bytes,
    bool,
]:

    if not payload.startswith(
        b"Exif\x00\x00"
    ):

        return payload, False

    tiff = bytearray(
        payload[6:]
    )

    try:

        header = parse_tiff_header(
            bytes(tiff)
        )

        ifd0 = parse_ifd(
            bytes(tiff),
            header.first_ifd_offset,
            header.byte_order,
        )

    except TiffParserError as exc:

        raise ScrubError(
            "Cannot selectively sanitize "
            f"EXIF: {exc}"
        ) from exc

    changed = False

    #
    # Both GPS and privacy mode remove the
    # complete GPS IFD and its referenced
    # value bytes.
    #
    if mode in {
        SCRUB_MODE_GPS,
        SCRUB_MODE_PRIVACY,
    }:

        changed = (
            _remove_gps_ifd(
                tiff,
                ifd0,
                header.byte_order,
            )
            or changed
        )

    if (
        mode
        == SCRUB_MODE_PRIVACY
    ):

        #
        # Locate ExifIFD before modifying
        # its sensitive fields.
        #
        exif_ifd = (
            _parse_sub_ifd_if_present(
                tiff,
                ifd0,
                EXIF_IFD_POINTER_TAG,
                header.byte_order,
            )
        )

        changed = (
            _redact_ifd_tags(
                tiff,
                ifd0,
                PRIVACY_IFD0_TAGS,
                header.byte_order,
            )
            or changed
        )

        if exif_ifd is not None:

            changed = (
                _redact_ifd_tags(
                    tiff,
                    exif_ifd,
                    PRIVACY_EXIF_IFD_TAGS,
                    header.byte_order,
                )
                or changed
            )

    if not changed:

        return payload, False

    return (
        b"Exif\x00\x00"
        + bytes(tiff),
        True,
    )


def _remove_gps_ifd(
    tiff: bytearray,
    ifd0: Ifd,
    byte_order: str,
) -> bool:

    found = _find_ifd_entry(
        ifd0,
        GPS_IFD_POINTER_TAG,
    )

    if found is None:

        return False

    entry_index, pointer_entry = (
        found
    )

    gps_offset = _pointer_value(
        pointer_entry,
        byte_order,
    )

    snapshot = bytes(
        tiff
    )

    try:

        gps_ifd = parse_ifd(
            snapshot,
            gps_offset,
            byte_order,
        )

    except TiffParserError as exc:

        raise ScrubError(
            "Cannot safely remove GPS IFD: "
            f"{exc}"
        ) from exc

    #
    # Wipe all externally stored GPS
    # values before wiping the directory.
    #
    for entry in gps_ifd.entries:

        _zero_external_value(
            tiff,
            entry,
            byte_order,
        )

    directory_end = (
        gps_ifd.offset
        + 2
        + (
            len(
                gps_ifd.entries
            )
            * 12
        )
        + 4
    )

    if directory_end > len(tiff):

        raise ScrubError(
            "GPS IFD directory exceeds "
            "TIFF boundaries."
        )

    tiff[
        gps_ifd.offset:
        directory_end
    ] = (
        b"\x00"
        * (
            directory_end
            - gps_ifd.offset
        )
    )

    #
    # Detach GPSInfoIFDPointer from IFD0.
    #
    _redact_single_ifd_entry(
        tiff,
        ifd0,
        entry_index,
        pointer_entry,
        byte_order,
    )

    return True


def _parse_sub_ifd_if_present(
    tiff: bytearray,
    parent_ifd: Ifd,
    pointer_tag: int,
    byte_order: str,
) -> Ifd | None:

    found = _find_ifd_entry(
        parent_ifd,
        pointer_tag,
    )

    if found is None:

        return None

    _, entry = found

    offset = _pointer_value(
        entry,
        byte_order,
    )

    try:

        return parse_ifd(
            bytes(tiff),
            offset,
            byte_order,
        )

    except TiffParserError as exc:

        raise ScrubError(
            "Cannot parse referenced "
            f"EXIF IFD: {exc}"
        ) from exc


def _redact_ifd_tags(
    tiff: bytearray,
    ifd: Ifd,
    target_tags: set[int],
    byte_order: str,
) -> bool:

    changed = False

    for index, entry in enumerate(
        ifd.entries
    ):

        if (
            entry.tag
            not in target_tags
        ):

            continue

        _redact_single_ifd_entry(
            tiff,
            ifd,
            index,
            entry,
            byte_order,
        )

        changed = True

    return changed


def _redact_single_ifd_entry(
    tiff: bytearray,
    ifd: Ifd,
    entry_index: int,
    entry: IfdEntry,
    byte_order: str,
) -> None:

    try:

        data_size = (
            get_ifd_entry_data_size(
                entry
            )
        )

    except TiffParserError as exc:

        raise ScrubError(
            "Cannot determine EXIF field "
            f"size: {exc}"
        ) from exc

    if data_size > 4:

        _zero_external_value(
            tiff,
            entry,
            byte_order,
        )

    entry_position = (
        ifd.offset
        + 2
        + (
            entry_index
            * 12
        )
    )

    entry_end = (
        entry_position
        + 12
    )

    if entry_end > len(tiff):

        raise ScrubError(
            "EXIF entry exceeds TIFF "
            "boundaries."
        )

    #
    # Replace tag identifier with an
    # unknown tombstone tag.
    #
    tiff[
        entry_position:
        entry_position + 2
    ] = (
        0xFFFF
    ).to_bytes(
        2,
        byte_order,
    )

    #
    # Inline values must be wiped here.
    # External values keep their pointer,
    # but the referenced bytes were zeroed.
    #
    if data_size <= 4:

        tiff[
            entry_position + 8:
            entry_position + 12
        ] = b"\x00\x00\x00\x00"


def _zero_external_value(
    tiff: bytearray,
    entry: IfdEntry,
    byte_order: str,
) -> None:

    try:

        data_size = (
            get_ifd_entry_data_size(
                entry
            )
        )

    except TiffParserError as exc:

        raise ScrubError(
            "Cannot determine TIFF value "
            f"size: {exc}"
        ) from exc

    if data_size <= 4:
        return

    value_offset = int.from_bytes(
        entry.value_or_offset,
        byteorder=byte_order,
    )

    value_end = (
        value_offset
        + data_size
    )

    if (
        value_offset < 8
        or value_end
        > len(tiff)
    ):

        raise ScrubError(
            "External TIFF value points "
            "outside safe boundaries."
        )

    tiff[
        value_offset:
        value_end
    ] = (
        b"\x00"
        * data_size
    )


def _pointer_value(
    entry: IfdEntry,
    byte_order: str,
) -> int:

    if (
        entry.field_type != 4
        or entry.count != 1
    ):

        raise ScrubError(
            "EXIF IFD pointer is not "
            "a LONG count=1 field."
        )

    value = int.from_bytes(
        entry.value_or_offset,
        byteorder=byte_order,
    )

    if value <= 0:

        raise ScrubError(
            "EXIF IFD pointer contains "
            "an invalid offset."
        )

    return value


def _find_ifd_entry(
    ifd: Ifd,
    tag: int,
) -> tuple[
    int,
    IfdEntry,
] | None:

    for index, entry in enumerate(
        ifd.entries
    ):

        if entry.tag == tag:

            return (
                index,
                entry,
            )

    return None


def _sanitize_xmp_payload(
    payload: bytes,
    mode: str,
) -> tuple[
    bytes,
    bool,
]:

    xml_data = payload[
        len(
            XMP_IDENTIFIER
        ):
    ]

    try:

        root = DefusedET.fromstring(
            xml_data,
            forbid_dtd=True,
            forbid_entities=True,
            forbid_external=True,
        )

    except (
        ET.ParseError,
        DefusedXmlException,
    ) as exc:

        raise ScrubError(
            "Cannot selectively sanitize "
            f"XMP: {exc}"
        ) from exc

    changed = _sanitize_xmp_element(
        root,
        mode,
    )

    if not changed:

        return payload, False

    sanitized_xml = ET.tostring(
        root,
        encoding="utf-8",
        xml_declaration=False,
    )

    return (
        XMP_IDENTIFIER
        + sanitized_xml,
        True,
    )


def _sanitize_xmp_element(
    element: ET.Element,
    mode: str,
) -> bool:

    changed = False

    for attribute in list(
        element.attrib
    ):

        if _remove_xmp_name(
            attribute,
            mode,
        ):

            del element.attrib[
                attribute
            ]

            changed = True

    for child in list(
        element
    ):

        if _remove_xmp_name(
            child.tag,
            mode,
        ):

            element.remove(
                child
            )

            changed = True
            continue

        if _sanitize_xmp_element(
            child,
            mode,
        ):

            changed = True

    return changed


def _remove_xmp_name(
    qualified_name: str,
    mode: str,
) -> bool:

    local_name = (
        _xml_local_name(
            qualified_name
        )
    )

    normalized = (
        local_name.lower()
    )

    #
    # All GPS-prefixed XMP fields.
    #
    if normalized.startswith(
        "gps"
    ):

        return True

    if normalized == (
        "hasextendedxmp"
    ):

        return True

    if mode == SCRUB_MODE_GPS:

        return False

    return (
        normalized
        in PRIVACY_XMP_LOCAL_NAMES
    )


def _xml_local_name(
    name: str,
) -> str:

    if (
        name.startswith("{")
        and "}" in name
    ):

        return name.split(
            "}",
            1,
        )[1]

    if ":" in name:

        return name.split(
            ":",
            1,
        )[1]

    return name


def _sanitize_photoshop_payload(
    payload: bytes,
) -> tuple[
    bytes,
    bool,
]:

    if not payload.startswith(
        PHOTOSHOP_IDENTIFIER
    ):

        return payload, False

    position = len(
        PHOTOSHOP_IDENTIFIER
    )

    output = bytearray(
        PHOTOSHOP_IDENTIFIER
    )

    changed = False

    while position < len(payload):

        block_start = (
            position
        )

        if (
            len(payload)
            - position
            < 7
        ):

            raise ScrubError(
                "Photoshop APP13 resource "
                "is truncated."
            )

        signature = payload[
            position:
            position + 4
        ]

        if (
            signature
            != PHOTOSHOP_RESOURCE_SIGNATURE
        ):

            raise ScrubError(
                "Invalid Photoshop APP13 "
                "resource signature."
            )

        position += 4

        resource_id = (
            int.from_bytes(
                payload[
                    position:
                    position + 2
                ],
                "big",
            )
        )

        position += 2

        name_length = payload[
            position
        ]

        position += 1

        name_end = (
            position
            + name_length
        )

        if name_end > len(payload):

            raise ScrubError(
                "Photoshop resource name "
                "is truncated."
            )

        position = (
            name_end
        )

        if (
            (1 + name_length)
            % 2
            != 0
        ):

            position += 1

        if (
            position + 4
            > len(payload)
        ):

            raise ScrubError(
                "Photoshop resource size "
                "is truncated."
            )

        size_position = (
            position
        )

        resource_size = (
            int.from_bytes(
                payload[
                    position:
                    position + 4
                ],
                "big",
            )
        )

        position += 4

        resource_start = (
            position
        )

        resource_end = (
            resource_start
            + resource_size
        )

        if resource_end > len(payload):

            raise ScrubError(
                "Photoshop resource data "
                "is truncated."
            )

        resource_data = payload[
            resource_start:
            resource_end
        ]

        position = (
            resource_end
        )

        if resource_size % 2:

            position += 1

        if position > len(payload):

            raise ScrubError(
                "Photoshop resource padding "
                "is truncated."
            )

        block_end = (
            position
        )

        if (
            resource_id
            != IPTC_RESOURCE_ID
        ):

            output += payload[
                block_start:
                block_end
            ]

            continue

        filtered, filtered_changed = (
            _filter_iptc_datasets(
                resource_data
            )
        )

        if not filtered_changed:

            output += payload[
                block_start:
                block_end
            ]

            continue

        changed = True

        #
        # If no IPTC datasets remain, omit
        # only the IPTC resource block.
        #
        if not filtered:

            continue

        output += payload[
            block_start:
            size_position
        ]

        output += len(
            filtered
        ).to_bytes(
            4,
            "big",
        )

        output += filtered

        if len(filtered) % 2:

            output += b"\x00"

    return (
        bytes(output),
        changed,
    )


def _filter_iptc_datasets(
    data: bytes,
) -> tuple[
    bytes,
    bool,
]:

    position = 0

    output = bytearray()

    changed = False

    while position < len(data):

        dataset_start = (
            position
        )

        if (
            len(data)
            - position
            < 5
        ):

            raise ScrubError(
                "IPTC DataSet is truncated."
            )

        if (
            data[position]
            != IPTC_DATASET_MARKER
        ):

            raise ScrubError(
                "Invalid IPTC DataSet marker."
            )

        record_number = data[
            position + 1
        ]

        dataset_number = data[
            position + 2
        ]

        length_field = (
            int.from_bytes(
                data[
                    position + 3:
                    position + 5
                ],
                "big",
            )
        )

        position += 5

        if (
            length_field
            & 0x8000
            == 0
        ):

            value_length = (
                length_field
            )

        else:

            length_octets = (
                length_field
                & 0x7FFF
            )

            if length_octets == 0:

                raise ScrubError(
                    "Invalid extended IPTC "
                    "length."
                )

            if (
                position
                + length_octets
                > len(data)
            ):

                raise ScrubError(
                    "Extended IPTC length "
                    "is truncated."
                )

            value_length = (
                int.from_bytes(
                    data[
                        position:
                        position
                        + length_octets
                    ],
                    "big",
                )
            )

            position += (
                length_octets
            )

        value_end = (
            position
            + value_length
        )

        if value_end > len(data):

            raise ScrubError(
                "IPTC DataSet value "
                "is truncated."
            )

        position = (
            value_end
        )

        dataset_id = (
            record_number,
            dataset_number,
        )

        if (
            dataset_id
            in PRIVACY_IPTC_DATASETS
        ):

            changed = True
            continue

        output += data[
            dataset_start:
            value_end
        ]

    return (
        bytes(output),
        changed,
    )


def _privacy_finding_count(
    path: Path,
) -> int:

    report = analyze_privacy(
        path
    )

    return report.count


def _has_gps(
    path: Path,
) -> bool:

    try:

        extract_gps_ifd_from_jpeg(
            path
        )

    except GpsIfdExtractorError:

        return False

    return True
