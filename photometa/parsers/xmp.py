from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from photometa.parsers.jpeg import (
    JpegSegment,
    iter_jpeg_segments,
)
from photometa.parsers.limits import (
    DEFAULT_PARSER_LIMITS,
    ParserLimits,
)


XMP_IDENTIFIER = (
    b"http://ns.adobe.com/xap/1.0/\x00"
)

EXTENDED_XMP_IDENTIFIER = (
    b"http://ns.adobe.com/xmp/extension/\x00"
)


RDF_NAMESPACE = (
    "http://www.w3.org/1999/02/"
    "22-rdf-syntax-ns#"
)

DC_NAMESPACE = (
    "http://purl.org/dc/elements/1.1/"
)

XMP_NAMESPACE = (
    "http://ns.adobe.com/xap/1.0/"
)

PHOTOSHOP_NAMESPACE = (
    "http://ns.adobe.com/photoshop/1.0/"
)

CAMERA_RAW_NAMESPACE = (
    "http://ns.adobe.com/"
    "camera-raw-settings/1.0/"
)

XMP_MM_NAMESPACE = (
    "http://ns.adobe.com/xap/1.0/mm/"
)

EXIF_NAMESPACE = (
    "http://ns.adobe.com/exif/1.0/"
)

TIFF_NAMESPACE = (
    "http://ns.adobe.com/tiff/1.0/"
)

GOOGLE_CAMERA_NAMESPACE = (
    "http://ns.google.com/photos/1.0/camera/"
)

NAMESPACE_PREFIXES: dict[str, str] = {
    RDF_NAMESPACE: "rdf",
    DC_NAMESPACE: "dc",
    XMP_NAMESPACE: "xmp",
    PHOTOSHOP_NAMESPACE: "photoshop",
    CAMERA_RAW_NAMESPACE: "crs",
    XMP_MM_NAMESPACE: "xmpMM",
    EXIF_NAMESPACE: "exif",
    TIFF_NAMESPACE: "tiff",
    GOOGLE_CAMERA_NAMESPACE: "gcamera",
}


RDF_DESCRIPTION = (
    f"{{{RDF_NAMESPACE}}}Description"
)

RDF_ALT = (
    f"{{{RDF_NAMESPACE}}}Alt"
)

RDF_SEQ = (
    f"{{{RDF_NAMESPACE}}}Seq"
)

RDF_BAG = (
    f"{{{RDF_NAMESPACE}}}Bag"
)

RDF_LI = (
    f"{{{RDF_NAMESPACE}}}li"
)

RDF_ABOUT = (
    f"{{{RDF_NAMESPACE}}}about"
)

RDF_RESOURCE = (
    f"{{{RDF_NAMESPACE}}}resource"
)

XML_LANG = (
    "{http://www.w3.org/XML/1998/"
    "namespace}lang"
)


XmpValue: TypeAlias = (
    str
    | tuple[str, ...]
)


class XmpParserError(Exception):
    """Base exception for XMP parsing errors."""


@dataclass(frozen=True)
class XmpProperty:
    namespace_uri: str | None
    local_name: str
    qualified_name: str
    value: XmpValue


@dataclass(frozen=True)
class XmpMetadata:
    packet_xml: str
    properties: tuple[XmpProperty, ...]

    def get(
        self,
        name: str,
        default: object | None = None,
    ) -> object:

        for property_ in self.properties:

            if (
                property_.qualified_name
                == name
            ):
                return property_.value

        return default

    def get_text(
        self,
        name: str,
        default: str | None = None,
    ) -> str | None:

        value = self.get(
            name
        )

        if isinstance(value, str):
            return value

        if (
            isinstance(value, tuple)
            and value
        ):
            return value[0]

        return default

    def as_dict(
        self,
    ) -> dict[str, XmpValue]:

        return {
            property_.qualified_name:
            property_.value
            for property_
            in self.properties
        }

    @property
    def creator(
        self,
    ) -> tuple[str, ...]:

        value = self.get(
            "dc:creator"
        )

        if isinstance(value, tuple):
            return value

        if isinstance(value, str):
            return (value,)

        return ()

    @property
    def title(
        self,
    ) -> str | None:

        return self.get_text(
            "dc:title"
        )

    @property
    def description(
        self,
    ) -> str | None:

        return self.get_text(
            "dc:description"
        )

    @property
    def creator_tool(
        self,
    ) -> str | None:

        return self.get_text(
            "xmp:CreatorTool"
        )

    @property
    def modify_date(
        self,
    ) -> str | None:

        return self.get_text(
            "xmp:ModifyDate"
        )

    @property
    def create_date(
        self,
    ) -> str | None:

        return self.get_text(
            "xmp:CreateDate"
        )

    @property
    def metadata_date(
        self,
    ) -> str | None:

        return self.get_text(
            "xmp:MetadataDate"
        )

    @property
    def rating(
        self,
    ) -> int | None:

        value = self.get_text(
            "xmp:Rating"
        )

        if value is None:
            return None

        try:
            return int(value)

        except ValueError:
            return None


def is_xmp_segment(
    segment: JpegSegment,
) -> bool:
    """
    Detecta un APP1 XMP estándar.
    """

    return (
        segment.marker == 0xE1
        and segment.payload.startswith(
            XMP_IDENTIFIER
        )
    )


def is_extended_xmp_segment(
    segment: JpegSegment,
) -> bool:
    """
    Detecta Extended XMP.

    En este punto sólo lo detectamos.
    El reensamblado de Extended XMP
    queda fuera del alcance inicial.
    """

    return (
        segment.marker == 0xE1
        and segment.payload.startswith(
            EXTENDED_XMP_IDENTIFIER
        )
    )


def parse_xmp_segment(
    segment: JpegSegment,
    *,
    limits: ParserLimits = DEFAULT_PARSER_LIMITS,
) -> XmpMetadata:
    """
    Extrae y analiza un paquete XMP APP1.
    """

    if not is_xmp_segment(
        segment
    ):
        raise XmpParserError(
            "El segmento no contiene "
            "XMP estándar."
        )

    xml_bytes = segment.payload[
        len(XMP_IDENTIFIER):
    ]

    #
    # Algunos archivos pueden añadir
    # NUL padding.
    #
    xml_bytes = xml_bytes.rstrip(
        b"\x00"
    )

    if not xml_bytes:
        raise XmpParserError(
            "El paquete XMP está vacío."
        )

    if (
        len(xml_bytes)
        > limits.max_xmp_packet_bytes
    ):
        raise XmpParserError(
            "El paquete XMP excede el "
            "límite de seguridad: "
            f"{len(xml_bytes)} bytes > "
            f"{limits.max_xmp_packet_bytes} bytes."
        )

    upper_xml = (
        xml_bytes.upper()
    )

    if (
        b"<!DOCTYPE" in upper_xml
        or b"<!ENTITY" in upper_xml
    ):
        raise XmpParserError(
            "El paquete XMP contiene "
            "declaraciones DTD/ENTITY no "
            "permitidas por PhotoMeta."
        )

    try:
        packet_xml = xml_bytes.decode(
            "utf-8-sig"
        )

    except UnicodeDecodeError as exc:
        raise XmpParserError(
            "El paquete XMP no contiene "
            "XML UTF-8 válido."
        ) from exc

    try:
        root = ET.fromstring(
            xml_bytes
        )

    except ET.ParseError as exc:
        raise XmpParserError(
            f"XML XMP inválido: {exc}"
        ) from exc

    node_count = 0

    for _element in root.iter():

        node_count += 1

        if (
            node_count
            > limits.max_xmp_xml_nodes
        ):
            raise XmpParserError(
                "El árbol XMP excede el "
                "límite de nodos XML: "
                f"{node_count} > "
                f"{limits.max_xmp_xml_nodes}."
            )

    properties = (
        _extract_xmp_properties(
            root,
            limits=limits,
        )
    )

    return XmpMetadata(
        packet_xml=packet_xml,
        properties=tuple(
            properties
        ),
    )


def extract_xmp_from_jpeg(
    path: str | Path,
    *,
    limits: ParserLimits = DEFAULT_PARSER_LIMITS,
) -> XmpMetadata | None:
    """
    Devuelve el primer paquete XMP estándar
    encontrado en un JPEG.

    La ausencia de XMP no es un error.
    """

    for segment in iter_jpeg_segments(
        path,
        limits=limits,
    ):

        if is_xmp_segment(
            segment
        ):
            return parse_xmp_segment(
                segment,
                limits=limits,
            )

    return None


def extract_all_xmp_from_jpeg(
    path: str | Path,
    *,
    limits: ParserLimits = DEFAULT_PARSER_LIMITS,
) -> tuple[XmpMetadata, ...]:
    """
    Extrae todos los paquetes XMP estándar
    encontrados antes del SOS.
    """

    metadata: list[
        XmpMetadata
    ] = []

    for segment in iter_jpeg_segments(
        path,
        limits=limits,
    ):

        if is_xmp_segment(
            segment
        ):
            metadata.append(
                parse_xmp_segment(
                    segment,
                    limits=limits,
                )
            )

    return tuple(metadata)


def has_extended_xmp(
    path: str | Path,
    *,
    limits: ParserLimits = DEFAULT_PARSER_LIMITS,
) -> bool:

    return any(
        is_extended_xmp_segment(
            segment
        )
        for segment
        in iter_jpeg_segments(
            path,
            limits=limits,
        )
    )


def _extract_xmp_properties(
    root: ET.Element,
    *,
    limits: ParserLimits = DEFAULT_PARSER_LIMITS,
) -> list[XmpProperty]:

    properties: list[
        XmpProperty
    ] = []

    def add_property(
        property_: XmpProperty,
    ) -> None:

        if (
            len(properties)
            >= limits.max_xmp_properties
        ):
            raise XmpParserError(
                "El paquete XMP excede el "
                "límite de propiedades: "
                f"{limits.max_xmp_properties}."
            )

        properties.append(
            property_
        )

    for description in root.iter(
        RDF_DESCRIPTION
    ):

        #
        # Muchas propiedades XMP aparecen
        # directamente como atributos de
        # rdf:Description.
        #
        for (
            attribute_name,
            attribute_value,
        ) in description.attrib.items():

            if attribute_name == RDF_ABOUT:
                continue

            add_property(
                _create_property(
                    attribute_name,
                    attribute_value,
                )
            )

        #
        # Otras aparecen como elementos.
        #
        for child in description:

            value = (
                _extract_element_value(
                    child
                )
            )

            if value is None:
                continue

            add_property(
                _create_property(
                    child.tag,
                    value,
                )
            )

    return properties

def _extract_element_value(
    element: ET.Element,
) -> XmpValue | None:

    resource = element.attrib.get(
        RDF_RESOURCE
    )

    if resource:
        return resource

    alt = element.find(
        RDF_ALT
    )

    if alt is not None:
        return _extract_alt_value(
            alt
        )

    seq = element.find(
        RDF_SEQ
    )

    if seq is not None:
        return _extract_container_values(
            seq
        )

    bag = element.find(
        RDF_BAG
    )

    if bag is not None:
        return _extract_container_values(
            bag
        )

    text = "".join(
        element.itertext()
    ).strip()

    if text:
        return text

    return None


def _extract_alt_value(
    alt: ET.Element,
) -> str | None:

    items: list[
        tuple[str | None, str]
    ] = []

    for item in alt.findall(
        RDF_LI
    ):

        text = "".join(
            item.itertext()
        ).strip()

        if not text:
            continue

        language = item.attrib.get(
            XML_LANG
        )

        items.append(
            (
                language,
                text,
            )
        )

    for language, text in items:

        if language == "x-default":
            return text

    if items:
        return items[0][1]

    return None


def _extract_container_values(
    container: ET.Element,
) -> tuple[str, ...] | None:

    values: list[str] = []

    for item in container.findall(
        RDF_LI
    ):

        text = "".join(
            item.itertext()
        ).strip()

        if text:
            values.append(
                text
            )

    if not values:
        return None

    return tuple(values)


def _create_property(
    expanded_name: str,
    value: XmpValue,
) -> XmpProperty:

    namespace_uri, local_name = (
        _split_expanded_name(
            expanded_name
        )
    )

    qualified_name = (
        _qualified_name(
            namespace_uri,
            local_name,
        )
    )

    return XmpProperty(
        namespace_uri=namespace_uri,
        local_name=local_name,
        qualified_name=qualified_name,
        value=value,
    )


def _split_expanded_name(
    name: str,
) -> tuple[str | None, str]:

    if (
        name.startswith("{")
        and "}" in name
    ):

        namespace_uri, local_name = (
            name[1:].split(
                "}",
                1,
            )
        )

        return (
            namespace_uri,
            local_name,
        )

    return (
        None,
        name,
    )


def _qualified_name(
    namespace_uri: str | None,
    local_name: str,
) -> str:

    if namespace_uri is None:
        return local_name

    prefix = NAMESPACE_PREFIXES.get(
        namespace_uri
    )

    if prefix is not None:
        return (
            f"{prefix}:"
            f"{local_name}"
        )

    #
    # ElementTree no conserva necesariamente
    # el prefijo XML original.
    # Para namespaces desconocidos usamos
    # la forma expandida sin inventar uno.
    #
    return (
        f"{{{namespace_uri}}}"
        f"{local_name}"
    )
