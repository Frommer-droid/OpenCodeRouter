from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def render_png(renderer: QSvgRenderer, size: int) -> bytes:
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()

    payload = QByteArray()
    buffer = QBuffer(payload)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, "PNG"):
        raise RuntimeError(f"Не удалось отрисовать PNG {size}×{size}")
    return bytes(payload)


def export_ico(svg_path: Path, ico_path: Path) -> None:
    renderer = QSvgRenderer(str(svg_path))
    if not renderer.isValid():
        raise ValueError(f"Некорректный SVG: {svg_path}")

    sizes = (16, 24, 32, 48, 64, 128, 256)
    images = [(size, render_png(renderer, size)) for size in sizes]
    header_size = 6 + 16 * len(images)
    offset = header_size
    entries: list[bytes] = []
    payloads: list[bytes] = []
    for size, payload in images:
        dimension = 0 if size == 256 else size
        entries.append(
            struct.pack(
                "<BBBBHHII",
                dimension,
                dimension,
                0,
                0,
                1,
                32,
                len(payload),
                offset,
            )
        )
        payloads.append(payload)
        offset += len(payload)

    ico_path.write_bytes(
        struct.pack("<HHH", 0, 1, len(images)) + b"".join(entries + payloads)
    )


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    export_ico(
        project_root / "assets" / "router.svg",
        project_root / "assets" / "router.ico",
    )
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
