from __future__ import annotations

from dataclasses import (
    dataclass,
    field,
)
from pathlib import Path
from typing import Mapping

from photometa.extractors.exif_ifd import (
    ExifIfdExtractorError,
    extract_exif_ifd_from_jpeg,
)
from photometa.extractors.gps_ifd import (
    GpsIfdExtractorError,
    extract_gps_ifd_from_jpeg,
)
from photometa.extractors.ifd0 import (
    Ifd0ExtractorError,
    extract_ifd0_from_jpeg,
)
from photometa.parsers.iptc import (
    extract_iptc_from_jpeg,
)
from photometa.parsers.xmp import (
    extract_xmp_from_jpeg,
)

SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"
SEVERITY_LOW = "low"


@dataclass(frozen=True)
class PrivacyFinding:
    code: str
    severity: str
    message: str
    sources: tuple[str, ...]
    fields: tuple[str, ...]


@dataclass(frozen=True)
class PrivacyReport:
    findings: tuple[
        PrivacyFinding,
        ...
    ]

    @property
    def has_findings(
        self,
    ) -> bool:

        return bool(
            self.findings
        )

    @property
    def count(
        self,
    ) -> int:

        return len(
            self.findings
        )

    def has(
        self,
        code: str,
    ) -> bool:

        return any(
            finding.code == code
            for finding
            in self.findings
        )

    def get(
        self,
        code: str,
    ) -> PrivacyFinding | None:

        for finding in self.findings:

            if finding.code == code:
                return finding

        return None


@dataclass(frozen=True)
class PrivacyContext:
    ifd0: Mapping[
        str,
        object,
    ] = field(
        default_factory=dict
    )

    exif: Mapping[
        str,
        object,
    ] = field(
        default_factory=dict
    )

    gps: Mapping[
        str,
        object,
    ] = field(
        default_factory=dict
    )

    xmp: Mapping[
        str,
        object,
    ] = field(
        default_factory=dict
    )

    iptc: Mapping[
        str,
        object,
    ] = field(
        default_factory=dict
    )


def analyze_privacy(
    path: str | Path,
) -> PrivacyReport:
    """
    Analiza metadatos potencialmente
    sensibles de un archivo JPEG.

    La presencia de un finding significa
    que el dato está expuesto, no que el
    archivo sea malicioso o manipulado.
    """

    context = (
        build_privacy_context(
            path
        )
    )

    return analyze_privacy_context(
        context
    )


def build_privacy_context(
    path: str | Path,
) -> PrivacyContext:
    """
    Extrae los grupos de metadatos que
    utiliza el analizador de privacidad.

    Un grupo ausente se representa con
    un diccionario vacío.
    """

    file_path = Path(
        path
    )

    ifd0_values: dict[
        str,
        object,
    ] = {}

    exif_values: dict[
        str,
        object,
    ] = {}

    gps_values: dict[
        str,
        object,
    ] = {}

    xmp_values: dict[
        str,
        object,
    ] = {}

    iptc_values: dict[
        str,
        object,
    ] = {}

    try:

        ifd0 = extract_ifd0_from_jpeg(
            file_path
        )

        ifd0_values = (
            ifd0.as_dict()
        )

    except Ifd0ExtractorError:
        pass

    try:

        exif = extract_exif_ifd_from_jpeg(
            file_path
        )

        exif_values = (
            exif.as_dict()
        )

    except ExifIfdExtractorError:
        pass

    try:

        gps = extract_gps_ifd_from_jpeg(
            file_path
        )

        gps_values = (
            gps.as_dict()
        )

    except GpsIfdExtractorError:
        pass

    xmp = extract_xmp_from_jpeg(
        file_path
    )

    if xmp is not None:

        xmp_values = (
            xmp.as_dict()
        )

    iptc = extract_iptc_from_jpeg(
        file_path
    )

    if iptc is not None:

        iptc_values = {
            "Creator": (
                iptc.creators
            ),
            "Copyright": (
                iptc.copyright
            ),
            "Sublocation": (
                iptc.sublocation
            ),
            "City": (
                iptc.city
            ),
            "ProvinceState": (
                iptc.province_state
            ),
            "CountryCode": (
                iptc.country_code
            ),
            "CountryName": (
                iptc.country
            ),
        }

    return PrivacyContext(
        ifd0=ifd0_values,
        exif=exif_values,
        gps=gps_values,
        xmp=xmp_values,
        iptc=iptc_values,
    )


def analyze_privacy_context(
    context: PrivacyContext,
) -> PrivacyReport:

    findings: list[
        PrivacyFinding
    ] = []

    #
    # GPS coordinates.
    #
    latitude_present = (
        _has_value(
            context.gps.get(
                "GPSLatitude"
            )
        )
    )

    longitude_present = (
        _has_value(
            context.gps.get(
                "GPSLongitude"
            )
        )
    )

    if (
        latitude_present
        and longitude_present
    ):

        findings.append(
            PrivacyFinding(
                code="gps_coordinates",
                severity=SEVERITY_HIGH,
                message=(
                    "GPS coordinates present"
                ),
                sources=("GPS",),
                fields=(
                    "GPSLatitude",
                    "GPSLongitude",
                ),
            )
        )

    #
    # GPS altitude.
    #
    if _has_value(
        context.gps.get(
            "GPSAltitude"
        )
    ):

        findings.append(
            PrivacyFinding(
                code="gps_altitude",
                severity=SEVERITY_MEDIUM,
                message=(
                    "GPS altitude present"
                ),
                sources=("GPS",),
                fields=(
                    "GPSAltitude",
                ),
            )
        )

    #
    # Original capture date.
    #
    if _has_value(
        context.exif.get(
            "DateTimeOriginal"
        )
    ):

        findings.append(
            PrivacyFinding(
                code="original_capture_date",
                severity=SEVERITY_MEDIUM,
                message=(
                    "Original capture "
                    "date exposed"
                ),
                sources=("EXIF",),
                fields=(
                    "DateTimeOriginal",
                ),
            )
        )

    #
    # Device model.
    #
    if _has_value(
        context.ifd0.get(
            "Model"
        )
    ):

        findings.append(
            PrivacyFinding(
                code="device_model",
                severity=SEVERITY_MEDIUM,
                message=(
                    "Device model exposed"
                ),
                sources=("EXIF",),
                fields=("Model",),
            )
        )

    #
    # Device/lens serial numbers.
    #
    serial_fields = (
        _present_fields(
            context.exif,
            (
                "BodySerialNumber",
                "LensSerialNumber",
            ),
        )
    )

    xmp_serial_fields = (
        _find_xmp_local_fields(
            context.xmp,
            {
                "SerialNumber",
                "CameraSerialNumber",
                "LensSerialNumber",
            },
        )
    )

    if (
        serial_fields
        or xmp_serial_fields
    ):

        sources = []

        if serial_fields:
            sources.append(
                "EXIF"
            )

        if xmp_serial_fields:
            sources.append(
                "XMP"
            )

        findings.append(
            PrivacyFinding(
                code="serial_number",
                severity=SEVERITY_HIGH,
                message=(
                    "Device or lens serial "
                    "number exposed"
                ),
                sources=tuple(
                    sources
                ),
                fields=tuple(
                    serial_fields
                    + xmp_serial_fields
                ),
            )
        )

    #
    # Owner/creator information.
    #
    owner_fields: list[str] = []
    owner_sources: list[str] = []

    ifd0_owner_fields = (
        _present_fields(
            context.ifd0,
            (
                "Artist",
            ),
        )
    )

    exif_owner_fields = (
        _present_fields(
            context.exif,
            (
                "CameraOwnerName",
            ),
        )
    )

    xmp_owner_fields = (
        _find_xmp_local_fields(
            context.xmp,
            {
                "creator",
                "Creator",
                "OwnerName",
            },
        )
    )

    iptc_owner_fields = (
        _present_fields(
            context.iptc,
            (
                "Creator",
            ),
        )
    )

    if ifd0_owner_fields:
        owner_sources.append(
            "EXIF"
        )

    if exif_owner_fields:
        if "EXIF" not in owner_sources:
            owner_sources.append(
                "EXIF"
            )

    if xmp_owner_fields:
        owner_sources.append(
            "XMP"
        )

    if iptc_owner_fields:
        owner_sources.append(
            "IPTC"
        )

    owner_fields.extend(
        ifd0_owner_fields
    )

    owner_fields.extend(
        exif_owner_fields
    )

    owner_fields.extend(
        xmp_owner_fields
    )

    owner_fields.extend(
        iptc_owner_fields
    )

    if owner_fields:

        findings.append(
            PrivacyFinding(
                code="owner_information",
                severity=SEVERITY_MEDIUM,
                message=(
                    "Owner or creator "
                    "information present"
                ),
                sources=tuple(
                    owner_sources
                ),
                fields=tuple(
                    owner_fields
                ),
            )
        )

    #
    # Software / processing tool.
    #
    software_fields: list[str] = []
    software_sources: list[str] = []

    ifd0_software = (
        _present_fields(
            context.ifd0,
            (
                "Software",
            ),
        )
    )

    xmp_software = (
        _find_xmp_local_fields(
            context.xmp,
            {
                "CreatorTool",
                "Software",
            },
        )
    )

    if ifd0_software:
        software_sources.append(
            "EXIF"
        )

    if xmp_software:
        software_sources.append(
            "XMP"
        )

    software_fields.extend(
        ifd0_software
    )

    software_fields.extend(
        xmp_software
    )

    if software_fields:

        findings.append(
            PrivacyFinding(
                code="software",
                severity=SEVERITY_LOW,
                message=(
                    "Software information "
                    "exposed"
                ),
                sources=tuple(
                    software_sources
                ),
                fields=tuple(
                    software_fields
                ),
            )
        )

    #
    # Copyright / author information.
    #
    copyright_fields: list[str] = []
    copyright_sources: list[str] = []

    ifd0_copyright = (
        _present_fields(
            context.ifd0,
            (
                "Copyright",
            ),
        )
    )

    xmp_copyright = (
        _find_xmp_local_fields(
            context.xmp,
            {
                "rights",
                "Copyright",
                "CopyrightNotice",
            },
        )
    )

    iptc_copyright = (
        _present_fields(
            context.iptc,
            (
                "Copyright",
            ),
        )
    )

    if ifd0_copyright:
        copyright_sources.append(
            "EXIF"
        )

    if xmp_copyright:
        copyright_sources.append(
            "XMP"
        )

    if iptc_copyright:
        copyright_sources.append(
            "IPTC"
        )

    copyright_fields.extend(
        ifd0_copyright
    )

    copyright_fields.extend(
        xmp_copyright
    )

    copyright_fields.extend(
        iptc_copyright
    )

    if copyright_fields:

        findings.append(
            PrivacyFinding(
                code="copyright_author",
                severity=SEVERITY_MEDIUM,
                message=(
                    "Copyright or author "
                    "metadata present"
                ),
                sources=tuple(
                    copyright_sources
                ),
                fields=tuple(
                    copyright_fields
                ),
            )
        )

    #
    # Unique identifiers.
    #
    unique_fields: list[str] = []
    unique_sources: list[str] = []

    exif_unique = (
        _present_fields(
            context.exif,
            (
                "ImageUniqueID",
            ),
        )
    )

    xmp_unique = (
        _find_xmp_local_fields(
            context.xmp,
            {
                "DocumentID",
                "InstanceID",
                "OriginalDocumentID",
                "Identifier",
                "ImageUniqueID",
            },
        )
    )

    if exif_unique:
        unique_sources.append(
            "EXIF"
        )

    if xmp_unique:
        unique_sources.append(
            "XMP"
        )

    unique_fields.extend(
        exif_unique
    )

    unique_fields.extend(
        xmp_unique
    )

    if unique_fields:

        findings.append(
            PrivacyFinding(
                code="unique_identifier",
                severity=SEVERITY_HIGH,
                message=(
                    "Unique identifier present"
                ),
                sources=tuple(
                    unique_sources
                ),
                fields=tuple(
                    unique_fields
                ),
            )
        )

    #
    # IPTC/XMP editorial location.
    #
    location_fields: list[str] = []
    location_sources: list[str] = []

    iptc_location = (
        _present_fields(
            context.iptc,
            (
                "Sublocation",
                "City",
                "ProvinceState",
                "CountryCode",
                "CountryName",
            ),
        )
    )

    xmp_location = (
        _find_xmp_local_fields(
            context.xmp,
            {
                "Location",
                "Sublocation",
                "City",
                "State",
                "ProvinceState",
                "Country",
                "CountryName",
                "CountryCode",
                "LocationCreated",
                "LocationShown",
                "GPSLatitude",
                "GPSLongitude",
            },
        )
    )

    if iptc_location:
        location_sources.append(
            "IPTC"
        )

    if xmp_location:
        location_sources.append(
            "XMP"
        )

    location_fields.extend(
        iptc_location
    )

    location_fields.extend(
        xmp_location
    )

    if location_fields:

        findings.append(
            PrivacyFinding(
                code="editorial_location",
                severity=SEVERITY_HIGH,
                message=(
                    "IPTC/XMP location "
                    "metadata present"
                ),
                sources=tuple(
                    location_sources
                ),
                fields=tuple(
                    location_fields
                ),
            )
        )

    return PrivacyReport(
        findings=tuple(
            _sort_findings(
                findings
            )
        )
    )


def _has_value(
    value: object,
) -> bool:

    if value is None:
        return False

    if isinstance(
        value,
        str,
    ):
        return bool(
            value.strip()
        )

    if isinstance(
        value,
        (
            bytes,
            tuple,
            list,
            set,
            dict,
        ),
    ):
        return bool(
            value
        )

    return True


def _present_fields(
    values: Mapping[
        str,
        object,
    ],
    field_names: tuple[
        str,
        ...
    ],
) -> list[str]:

    return [
        field_name
        for field_name
        in field_names
        if _has_value(
            values.get(
                field_name
            )
        )
    ]


def _find_xmp_local_fields(
    values: Mapping[
        str,
        object,
    ],
    local_names: set[str],
) -> list[str]:

    found: list[str] = []

    normalized_names = {
        name.lower()
        for name
        in local_names
    }

    for key, value in (
        values.items()
    ):

        if not _has_value(
            value
        ):
            continue

        local_name = (
            _xmp_local_name(
                key
            )
        )

        if (
            local_name.lower()
            in normalized_names
        ):
            found.append(
                key
            )

    return found


def _xmp_local_name(
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


def _sort_findings(
    findings: list[
        PrivacyFinding
    ],
) -> list[
    PrivacyFinding
]:

    severity_order = {
        SEVERITY_HIGH: 0,
        SEVERITY_MEDIUM: 1,
        SEVERITY_LOW: 2,
    }

    return sorted(
        findings,
        key=lambda finding: (
            severity_order.get(
                finding.severity,
                99,
            ),
            finding.code,
        ),
    )
