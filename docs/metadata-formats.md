# XMP, ICC and IPTC Metadata

PhotoMeta supports metadata beyond EXIF.

## XMP

Standard XMP in JPEG is recognized in APP1 through:

    http://ns.adobe.com/xap/1.0/\0

Extended XMP presence is recognized through:

    http://ns.adobe.com/xmp/extension/\0

PhotoMeta maps selected RDF, Dublin Core, XMP, Photoshop, Camera Raw, EXIF,
TIFF and Google Camera namespaces.

XML is parsed defensively with `defusedxml`.

DTD and ENTITY declarations are rejected and resource budgets are applied.

## ICC

ICC color profiles are recognized in APP2 through:

    ICC_PROFILE\0

A JPEG ICC profile may span multiple APP2 chunks.

PhotoMeta validates chunk numbering and reconstructs the profile.

ICC profiles are normally preserved during full metadata scrub because they
affect color interpretation.

## IPTC

PhotoMeta supports IPTC data stored in Photoshop APP13.

Photoshop container identifier:

    Photoshop 3.0\0

Image Resource signature:

    8BIM

IPTC resource ID:

    0x0404

Supported IPTC fields include title, keywords, creator/byline, date,
location, headline, credit, source, copyright, caption and writer/editor.

## Interpretation

Presence of XMP, ICC or IPTC is descriptive.

It does not prove that an image has been edited, forged or produced by a
particular application.
