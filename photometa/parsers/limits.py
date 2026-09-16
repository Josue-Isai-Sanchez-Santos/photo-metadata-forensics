from __future__ import annotations

from dataclasses import dataclass


MIB = 1024 * 1024
GIB = 1024 * MIB


@dataclass(
    frozen=True
)
class ParserLimits:
    """
    Defensive resource limits for parsing
    potentially hostile metadata.

    These limits are safety policy, not
    claims about the maximum values allowed
    by every image or metadata standard.
    """

    #
    # Whole input.
    #
    max_input_file_bytes: int = 1 * GIB

    #
    # JPEG header traversal.
    #
    max_jpeg_segments: int = 4096

    max_jpeg_marker_fill_bytes: int = 1024

    #
    # JPEG's own 16-bit segment-length field
    # cannot describe a payload larger than
    # 65533 bytes.
    #
    max_jpeg_segment_payload_bytes: int = 65533

    #
    # Prevent a file from using thousands of
    # individually valid APP/COM/etc segments
    # as a cumulative metadata/header bomb.
    #
    max_jpeg_header_payload_bytes: int = 32 * MIB

    #
    # TIFF / EXIF.
    #
    max_ifd_entries: int = 4096

    #
    # Some TIFF value types are decoded into
    # Python tuples. Limiting components also
    # limits object-allocation amplification.
    #
    max_tiff_components: int = 65536

    max_tiff_value_bytes: int = 16 * MIB

    #
    # Used in 29B when guarded IFD traversal
    # is introduced.
    #
    max_ifd_depth: int = 16
    max_ifd_nodes: int = 64

    #
    # Used in 29C.
    #
    max_xmp_packet_bytes: int = 2 * MIB
    max_xmp_xml_nodes: int = 20000
    max_xmp_properties: int = 10000

    max_icc_profile_bytes: int = 32 * MIB
    max_icc_chunks: int = 255
    max_icc_tags: int = 4096

    max_photoshop_resources: int = 4096
    max_photoshop_payload_bytes: int = 16 * MIB
    max_photoshop_resource_bytes: int = 8 * MIB

    max_iptc_data_bytes: int = 16 * MIB
    max_iptc_datasets: int = 10000
    max_iptc_value_bytes: int = 8 * MIB

    #
    # Extended IPTC length descriptors should
    # never be allowed to become arbitrarily
    # large Python integers.
    #
    max_iptc_length_octets: int = 8


DEFAULT_PARSER_LIMITS = ParserLimits()
