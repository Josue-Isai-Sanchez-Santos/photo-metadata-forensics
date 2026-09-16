from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from photometa.parsers.jpeg import (
    JpegParserError,
    iter_jpeg_segments,
)
from photometa.parsers.limits import (
    DEFAULT_PARSER_LIMITS,
)
from photometa.parsers.tiff import (
    IfdEntry,
    TiffParserError,
    get_ifd_entry_data_size,
    get_ifd_entry_raw_value,
    parse_ifd,
)


class TestJpegSecurityLimits(
    unittest.TestCase
):

    def make_root(
        self,
    ) -> Path:

        temp = (
            tempfile.TemporaryDirectory()
        )

        self.addCleanup(
            temp.cleanup
        )

        return Path(
            temp.name
        )

    def test_rejects_file_over_size_limit(
        self,
    ):

        root = self.make_root()

        path = (
            root / "large.jpg"
        )

        path.write_bytes(
            b"\xFF\xD8"
            + b"\xFF\xD9"
        )

        limits = replace(
            DEFAULT_PARSER_LIMITS,
            max_input_file_bytes=3,
        )

        with self.assertRaises(
            JpegParserError
        ):

            tuple(
                iter_jpeg_segments(
                    path,
                    limits=limits,
                )
            )

    def test_rejects_too_many_segments(
        self,
    ):

        root = self.make_root()

        path = (
            root / "many.jpg"
        )

        path.write_bytes(
            b"\xFF\xD8"
            + b"\xFF\xE0\x00\x02"
            + b"\xFF\xE1\x00\x02"
            + b"\xFF\xD9"
        )

        limits = replace(
            DEFAULT_PARSER_LIMITS,
            max_jpeg_segments=3,
        )

        with self.assertRaises(
            JpegParserError
        ):

            tuple(
                iter_jpeg_segments(
                    path,
                    limits=limits,
                )
            )

    def test_rejects_excessive_marker_fill(
        self,
    ):

        root = self.make_root()

        path = (
            root / "fill.jpg"
        )

        path.write_bytes(
            b"\xFF\xD8"
            + b"\xFF"
            + b"\xFF" * 5
            + b"\xD9"
        )

        limits = replace(
            DEFAULT_PARSER_LIMITS,
            max_jpeg_marker_fill_bytes=2,
        )

        with self.assertRaises(
            JpegParserError
        ):

            tuple(
                iter_jpeg_segments(
                    path,
                    limits=limits,
                )
            )

    def test_rejects_cumulative_header_bomb(
        self,
    ):

        root = self.make_root()

        path = (
            root / "metadata-bomb.jpg"
        )

        payload = (
            b"A" * 10
        )

        segment = (
            b"\xFF\xE1"
            + (12).to_bytes(
                2,
                "big",
            )
            + payload
        )

        path.write_bytes(
            b"\xFF\xD8"
            + segment
            + segment
            + b"\xFF\xD9"
        )

        limits = replace(
            DEFAULT_PARSER_LIMITS,
            max_jpeg_header_payload_bytes=15,
        )

        with self.assertRaises(
            JpegParserError
        ):

            tuple(
                iter_jpeg_segments(
                    path,
                    limits=limits,
                )
            )


class TestTiffSecurityLimits(
    unittest.TestCase
):

    def test_rejects_ifd_inside_tiff_header(
        self,
    ):

        data = (
            b"II"
            b"\x2A\x00"
            b"\x08\x00\x00\x00"
            + b"\x00" * 16
        )

        with self.assertRaises(
            TiffParserError
        ):

            parse_ifd(
                data,
                4,
                "little",
            )

    def test_rejects_absurd_ifd_entry_count(
        self,
    ):

        data = (
            b"\x00" * 8
            + (5000).to_bytes(
                2,
                "little",
            )
            + b"\x00" * 16
        )

        limits = replace(
            DEFAULT_PARSER_LIMITS,
            max_ifd_entries=100,
        )

        with self.assertRaises(
            TiffParserError
        ):

            parse_ifd(
                data,
                8,
                "little",
                limits=limits,
            )

    def test_rejects_tiff_component_bomb(
        self,
    ):

        entry = IfdEntry(
            tag=0x0001,
            field_type=1,
            count=1000,
            value_or_offset=(
                b"\x00\x00\x00\x00"
            ),
        )

        limits = replace(
            DEFAULT_PARSER_LIMITS,
            max_tiff_components=100,
        )

        with self.assertRaises(
            TiffParserError
        ):

            get_ifd_entry_data_size(
                entry,
                limits=limits,
            )

    def test_rejects_tiff_value_byte_bomb(
        self,
    ):

        entry = IfdEntry(
            tag=0x0001,
            field_type=12,
            count=100,
            value_or_offset=(
                b"\x00\x00\x00\x00"
            ),
        )

        limits = replace(
            DEFAULT_PARSER_LIMITS,
            max_tiff_value_bytes=128,
        )

        with self.assertRaises(
            TiffParserError
        ):

            get_ifd_entry_data_size(
                entry,
                limits=limits,
            )

    def test_rejects_external_value_outside_data(
        self,
    ):

        data = (
            b"\x00" * 32
        )

        entry = IfdEntry(
            tag=0x010F,
            field_type=2,
            count=8,
            value_or_offset=(
                (30).to_bytes(
                    4,
                    "little",
                )
            ),
        )

        with self.assertRaises(
            TiffParserError
        ):

            get_ifd_entry_raw_value(
                data,
                entry,
                "little",
            )

    def test_rejects_self_referential_next_ifd(
        self,
    ):

        data = (
            b"\x00" * 8

            #
            # IFD at offset 8.
            #
            + b"\x00\x00"

            #
            # next_ifd_offset -> itself.
            #
            + (8).to_bytes(
                4,
                "little",
            )
        )

        with self.assertRaises(
            TiffParserError
        ):

            parse_ifd(
                data,
                8,
                "little",
            )


if __name__ == "__main__":

    unittest.main()


class TestIfdTraversalSecurity(
    unittest.TestCase
):

    def test_guarded_ifd_rejects_revisited_offset(
        self,
    ):

        from photometa.parsers.tiff import (
            IfdTraversalState,
            parse_ifd_guarded,
        )

        data = (
            b"\x00" * 8
            + b"\x00\x00"
            + b"\x00\x00\x00\x00"
        )

        state = (
            IfdTraversalState.create()
        )

        parse_ifd_guarded(
            data,
            8,
            "little",
            state=state,
            depth=0,
        )

        with self.assertRaises(
            TiffParserError
        ):

            parse_ifd_guarded(
                data,
                8,
                "little",
                state=state,
                depth=1,
            )

    def test_guarded_ifd_rejects_depth_limit(
        self,
    ):

        from photometa.parsers.tiff import (
            IfdTraversalState,
            parse_ifd_guarded,
        )

        data = (
            b"\x00" * 8
            + b"\x00\x00"
            + b"\x00\x00\x00\x00"
        )

        limits = replace(
            DEFAULT_PARSER_LIMITS,
            max_ifd_depth=2,
        )

        state = (
            IfdTraversalState.create()
        )

        with self.assertRaises(
            TiffParserError
        ):

            parse_ifd_guarded(
                data,
                8,
                "little",
                state=state,
                depth=3,
                limits=limits,
            )

    def test_guarded_ifd_rejects_node_budget(
        self,
    ):

        from photometa.parsers.tiff import (
            IfdTraversalState,
            parse_ifd_guarded,
        )

        data = (
            b"\x00" * 64
        )

        limits = replace(
            DEFAULT_PARSER_LIMITS,
            max_ifd_nodes=1,
        )

        state = (
            IfdTraversalState.create()
        )

        parse_ifd_guarded(
            data,
            8,
            "little",
            state=state,
            depth=0,
            limits=limits,
        )

        with self.assertRaises(
            TiffParserError
        ):

            parse_ifd_guarded(
                data,
                16,
                "little",
                state=state,
                depth=1,
                limits=limits,
            )

    def test_detects_two_node_cycle(
        self,
    ):

        from photometa.parsers.tiff import (
            IfdTraversalState,
            parse_ifd_guarded,
        )

        #
        # IFD A at 8:
        # zero entries
        # next -> 20
        #
        # IFD B at 20:
        # zero entries
        # next -> 8
        #
        data = bytearray(
            b"\x00" * 32
        )

        data[
            8:10
        ] = (
            b"\x00\x00"
        )

        data[
            10:14
        ] = (
            (20).to_bytes(
                4,
                "little",
            )
        )

        data[
            20:22
        ] = (
            b"\x00\x00"
        )

        data[
            22:26
        ] = (
            (8).to_bytes(
                4,
                "little",
            )
        )

        state = (
            IfdTraversalState.create()
        )

        first = (
            parse_ifd_guarded(
                bytes(data),
                8,
                "little",
                state=state,
                depth=0,
            )
        )

        second = (
            parse_ifd_guarded(
                bytes(data),
                first.next_ifd_offset,
                "little",
                state=state,
                depth=1,
            )
        )

        with self.assertRaises(
            TiffParserError
        ):

            parse_ifd_guarded(
                bytes(data),
                second.next_ifd_offset,
                "little",
                state=state,
                depth=2,
            )


class TestExifPointerTraversalSecurity(
    unittest.TestCase
):

    @staticmethod
    def make_exif_with_pointer(
        tag: int,
        target_offset: int,
        *,
        include_child: bool = False,
    ):

        from photometa.parsers.exif import (
            parse_exif,
        )
        from photometa.parsers.jpeg import (
            JpegSegment,
        )

        tiff = bytearray()

        #
        # TIFF header.
        #
        tiff += b"II"
        tiff += b"\x2A\x00"
        tiff += (8).to_bytes(
            4,
            "little",
        )

        #
        # IFD0 with one LONG pointer.
        #
        tiff += (1).to_bytes(
            2,
            "little",
        )

        tiff += tag.to_bytes(
            2,
            "little",
        )

        tiff += (4).to_bytes(
            2,
            "little",
        )

        tiff += (1).to_bytes(
            4,
            "little",
        )

        tiff += target_offset.to_bytes(
            4,
            "little",
        )

        #
        # next IFD = none.
        #
        tiff += (0).to_bytes(
            4,
            "little",
        )

        if include_child:

            #
            # IFD0 ends at offset 26.
            # A minimal child IFD therefore
            # begins exactly here.
            #
            if target_offset != len(tiff):

                raise ValueError(
                    "Synthetic child offset "
                    "does not match TIFF length."
                )

            #
            # Zero entries + no next IFD.
            #
            tiff += b"\x00\x00"
            tiff += b"\x00\x00\x00\x00"

        payload = (
            b"Exif\x00\x00"
            + bytes(tiff)
        )

        segment = JpegSegment(
            offset=2,
            marker=0xE1,
            name="APP1",
            declared_length=(
                len(payload) + 2
            ),
            payload_length=len(
                payload
            ),
            is_exif=True,
            payload=payload,
        )

        return parse_exif(
            segment
        )

    def test_exif_pointer_cannot_return_to_ifd0(
        self,
    ):

        from photometa.extractors.exif_ifd import (
            parse_exif_ifd,
        )

        exif = (
            self.make_exif_with_pointer(
                0x8769,
                8,
            )
        )

        with self.assertRaises(
            TiffParserError
        ):

            parse_exif_ifd(
                exif
            )

    def test_gps_pointer_cannot_return_to_ifd0(
        self,
    ):

        from photometa.extractors.gps_ifd import (
            parse_gps_ifd,
        )

        exif = (
            self.make_exif_with_pointer(
                0x8825,
                8,
            )
        )

        with self.assertRaises(
            TiffParserError
        ):

            parse_gps_ifd(
                exif
            )

    def test_child_ifd_respects_node_budget(
        self,
    ):

        from photometa.extractors.exif_ifd import (
            parse_exif_ifd,
        )

        exif = (
            self.make_exif_with_pointer(
                0x8769,
                26,
                include_child=True,
            )
        )

        limits = replace(
            DEFAULT_PARSER_LIMITS,
            max_ifd_nodes=1,
        )

        with self.assertRaises(
            TiffParserError
        ):

            parse_exif_ifd(
                exif,
                limits=limits,
            )

    def test_child_ifd_respects_depth_budget(
        self,
    ):

        from photometa.extractors.exif_ifd import (
            parse_exif_ifd,
        )

        exif = (
            self.make_exif_with_pointer(
                0x8769,
                26,
                include_child=True,
            )
        )

        limits = replace(
            DEFAULT_PARSER_LIMITS,
            max_ifd_depth=0,
        )

        with self.assertRaises(
            TiffParserError
        ):

            parse_exif_ifd(
                exif,
                limits=limits,
            )


class TestXmpSecurityLimits(
    unittest.TestCase
):

    @staticmethod
    def make_xmp_segment(
        xml: bytes,
    ):

        from photometa.parsers.jpeg import (
            JpegSegment,
        )
        from photometa.parsers.xmp import (
            XMP_IDENTIFIER,
        )

        payload = (
            XMP_IDENTIFIER
            + xml
        )

        return JpegSegment(
            offset=2,
            marker=0xE1,
            name="APP1",
            declared_length=(
                len(payload) + 2
            ),
            payload_length=len(
                payload
            ),
            is_exif=False,
            payload=payload,
        )

    def test_rejects_xmp_packet_size_bomb(
        self,
    ):

        from photometa.parsers.xmp import (
            XmpParserError,
            parse_xmp_segment,
        )

        segment = (
            self.make_xmp_segment(
                b"<root>"
                + b"A" * 100
                + b"</root>"
            )
        )

        limits = replace(
            DEFAULT_PARSER_LIMITS,
            max_xmp_packet_bytes=32,
        )

        with self.assertRaises(
            XmpParserError
        ):

            parse_xmp_segment(
                segment,
                limits=limits,
            )

    def test_rejects_xmp_dtd_entity(
        self,
    ):

        from photometa.parsers.xmp import (
            XmpParserError,
            parse_xmp_segment,
        )

        xml = (
            b'<!DOCTYPE root ['
            b'<!ENTITY bomb "boom">'
            b']>'
            b'<root>&bomb;</root>'
        )

        segment = (
            self.make_xmp_segment(
                xml
            )
        )

        with self.assertRaises(
            XmpParserError
        ):

            parse_xmp_segment(
                segment
            )

    def test_rejects_xmp_node_bomb(
        self,
    ):

        from photometa.parsers.xmp import (
            XmpParserError,
            parse_xmp_segment,
        )

        xml = (
            b"<root>"
            b"<a/>"
            b"<b/>"
            b"<c/>"
            b"</root>"
        )

        segment = (
            self.make_xmp_segment(
                xml
            )
        )

        limits = replace(
            DEFAULT_PARSER_LIMITS,
            max_xmp_xml_nodes=2,
        )

        with self.assertRaises(
            XmpParserError
        ):

            parse_xmp_segment(
                segment,
                limits=limits,
            )

    def test_rejects_xmp_property_bomb(
        self,
    ):

        from photometa.parsers.xmp import (
            XmpParserError,
            parse_xmp_segment,
        )

        xml = (
            b'<x:xmpmeta '
            b'xmlns:x="adobe:ns:meta/">'
            b'<rdf:RDF '
            b'xmlns:rdf="http://www.w3.org/'
            b'1999/02/22-rdf-syntax-ns#" '
            b'xmlns:dc="http://purl.org/'
            b'dc/elements/1.1/">'
            b'<rdf:Description '
            b'dc:title="A" '
            b'dc:description="B"/>'
            b'</rdf:RDF>'
            b'</x:xmpmeta>'
        )

        segment = (
            self.make_xmp_segment(
                xml
            )
        )

        limits = replace(
            DEFAULT_PARSER_LIMITS,
            max_xmp_properties=1,
        )

        with self.assertRaises(
            XmpParserError
        ):

            parse_xmp_segment(
                segment,
                limits=limits,
            )


class TestIccSecurityLimits(
    unittest.TestCase
):

    def test_rejects_too_many_icc_chunks(
        self,
    ):

        from photometa.parsers.icc import (
            IccChunk,
            IccParserError,
            reassemble_icc_chunks,
        )

        chunks = (
            IccChunk(
                sequence_number=1,
                total_chunks=2,
                data=b"A",
            ),
            IccChunk(
                sequence_number=2,
                total_chunks=2,
                data=b"B",
            ),
        )

        limits = replace(
            DEFAULT_PARSER_LIMITS,
            max_icc_chunks=1,
        )

        with self.assertRaises(
            IccParserError
        ):

            reassemble_icc_chunks(
                chunks,
                limits=limits,
            )

    def test_rejects_icc_reassembly_size_bomb(
        self,
    ):

        from photometa.parsers.icc import (
            IccChunk,
            IccParserError,
            reassemble_icc_chunks,
        )

        chunks = (
            IccChunk(
                sequence_number=1,
                total_chunks=2,
                data=b"AA",
            ),
            IccChunk(
                sequence_number=2,
                total_chunks=2,
                data=b"BB",
            ),
        )

        limits = replace(
            DEFAULT_PARSER_LIMITS,
            max_icc_profile_bytes=3,
        )

        with self.assertRaises(
            IccParserError
        ):

            reassemble_icc_chunks(
                chunks,
                limits=limits,
            )

    def test_rejects_icc_tag_count_bomb(
        self,
    ):

        from photometa.parsers.icc import (
            IccParserError,
            parse_icc_profile,
        )

        profile = bytearray(
            b"\x00" * 132
        )

        profile[
            0:4
        ] = (
            (132).to_bytes(
                4,
                "big",
            )
        )

        profile[
            36:40
        ] = b"acsp"

        profile[
            128:132
        ] = (
            (2).to_bytes(
                4,
                "big",
            )
        )

        limits = replace(
            DEFAULT_PARSER_LIMITS,
            max_icc_tags=1,
        )

        with self.assertRaises(
            IccParserError
        ):

            parse_icc_profile(
                bytes(profile),
                limits=limits,
            )


class TestIptcSecurityLimits(
    unittest.TestCase
):

    @staticmethod
    def make_resource(
        resource_id: int = 0x0404,
        data: bytes = b"",
    ) -> bytes:

        return (
            b"8BIM"
            + resource_id.to_bytes(
                2,
                "big",
            )
            #
            # Empty Pascal name:
            # length byte + padding byte.
            #
            + b"\x00\x00"
            + len(data).to_bytes(
                4,
                "big",
            )
            + data
            + (
                b"\x00"
                if len(data) % 2
                else b""
            )
        )

    def test_rejects_photoshop_resource_bomb(
        self,
    ):

        from photometa.parsers.iptc import (
            PHOTOSHOP_IDENTIFIER,
            IptcParserError,
            parse_photoshop_resources,
        )
        from photometa.parsers.jpeg import (
            JpegSegment,
        )

        payload = (
            PHOTOSHOP_IDENTIFIER
            + self.make_resource(
                0x0404
            )
            + self.make_resource(
                0x0405
            )
        )

        segment = JpegSegment(
            offset=2,
            marker=0xED,
            name="APP13",
            declared_length=(
                len(payload) + 2
            ),
            payload_length=len(
                payload
            ),
            is_exif=False,
            payload=payload,
        )

        limits = replace(
            DEFAULT_PARSER_LIMITS,
            max_photoshop_resources=1,
        )

        with self.assertRaises(
            IptcParserError
        ):

            parse_photoshop_resources(
                segment,
                limits=limits,
            )

    def test_rejects_iptc_length_descriptor_bomb(
        self,
    ):

        from photometa.parsers.iptc import (
            IptcParserError,
            parse_iptc_iim,
        )

        data = (
            b"\x1C"
            b"\x02"
            b"\x05"
            #
            # Extended-length flag +
            # 9 length octets.
            #
            b"\x80\x09"
            + b"\x00" * 9
        )

        limits = replace(
            DEFAULT_PARSER_LIMITS,
            max_iptc_length_octets=8,
        )

        with self.assertRaises(
            IptcParserError
        ):

            parse_iptc_iim(
                data,
                limits=limits,
            )

    def test_rejects_iptc_value_bomb(
        self,
    ):

        from photometa.parsers.iptc import (
            IptcParserError,
            parse_iptc_iim,
        )

        value = (
            b"A" * 10
        )

        data = (
            b"\x1C"
            b"\x02"
            b"\x05"
            + len(value).to_bytes(
                2,
                "big",
            )
            + value
        )

        limits = replace(
            DEFAULT_PARSER_LIMITS,
            max_iptc_value_bytes=4,
        )

        with self.assertRaises(
            IptcParserError
        ):

            parse_iptc_iim(
                data,
                limits=limits,
            )

    def test_rejects_iptc_dataset_count_bomb(
        self,
    ):

        from photometa.parsers.iptc import (
            IptcParserError,
            parse_iptc_iim,
        )

        empty_dataset = (
            b"\x1C"
            b"\x02"
            b"\x05"
            b"\x00\x00"
        )

        data = (
            empty_dataset
            + empty_dataset
        )

        limits = replace(
            DEFAULT_PARSER_LIMITS,
            max_iptc_datasets=1,
        )

        with self.assertRaises(
            IptcParserError
        ):

            parse_iptc_iim(
                data,
                limits=limits,
            )
