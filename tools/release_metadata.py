#!/usr/bin/env python3
"""Attach third-party font licensing metadata to firmware artifacts."""

import shutil
from pathlib import Path


FONT_LICENSE = (
    Path(__file__).resolve().parents[1]
    / "components"
    / "retro-go"
    / "fonts"
    / "NotoSansCJK-OFL.txt"
)


def copy_font_license(artifact):
    """Copy the Noto CJK OFL next to a generated firmware artifact."""

    artifact = Path(artifact)
    sidecar = artifact.with_name(artifact.name + ".OFL.txt")
    shutil.copyfile(FONT_LICENSE, sidecar)
    return sidecar
