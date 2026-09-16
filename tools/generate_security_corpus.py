from __future__ import annotations

from pathlib import Path

from PIL import Image

from photometa.parsers.xmp import (
    XMP_IDENTIFIER,
)

OUTPUT_DIRECTORY = Path(
    "samples/private/security-corpus"
)


def jpeg_segment(
    marker: int,
    payload: bytes,
) -> bytes:

    declared_length = (
        len(payload) + 2
    )

    if declared_length > 0xFFFF:

        raise ValueError(
            "JPEG segment is too large."
        )

    return (
        b"\xFF"
        + bytes(
            [marker]
        )
        + declared_length.to_bytes(
            2,
            "big",
        )
        + payload
    )


def main() -> None:

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    base_path = (
        OUTPUT_DIRECTORY
        / "valid.jpg"
    )

    image = Image.new(
        "RGB",
        (32, 32),
        (120, 80, 40),
    )

    image.save(
        base_path,
        format="JPEG",
        quality=85,
    )

    base = (
        base_path.read_bytes()
    )

    if not base.startswith(
        b"\xFF\xD8"
    ):

        raise RuntimeError(
            "Generated base file "
            "is not JPEG."
        )

    #
    # 1. Segment-count resource bomb.
    #
    segment_bomb = (
        base[:2]
        + (
            b"\xFF\xE1\x00\x02"
            * 5000
        )
        + base[2:]
    )

    (
        OUTPUT_DIRECTORY
        / "many-segments.jpg"
    ).write_bytes(
        segment_bomb
    )

    #
    # 2. Truncated APP1.
    #
    (
        OUTPUT_DIRECTORY
        / "truncated-app1.jpg"
    ).write_bytes(
        b"\xFF\xD8"
        b"\xFF\xE1"
        b"\x01\x00"
        b"ABC"
    )

    #
    # 3. XMP containing a DTD/entity.
    #
    # PhotoMeta does not need DTDs or
    # entities for its XMP feature set,
    # so the native parser rejects them.
    #
    xml = (
        b'<!DOCTYPE root ['
        b'<!ENTITY bomb "boom">'
        b']>'
        b'<root>&bomb;</root>'
    )

    xmp_payload = (
        XMP_IDENTIFIER
        + xml
    )

    xmp_segment = (
        jpeg_segment(
            0xE1,
            xmp_payload,
        )
    )

    (
        OUTPUT_DIRECTORY
        / "xmp-entity.jpg"
    ).write_bytes(
        base[:2]
        + xmp_segment
        + base[2:]
    )

    print(
        "Security corpus generated:"
    )

    for path in sorted(
        OUTPUT_DIRECTORY.iterdir()
    ):

        print(
            f"  {path.name}: "
            f"{path.stat().st_size} bytes"
        )


if __name__ == "__main__":

    main()
