from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

BASE_LOGICAL_DPI = 96.0
REFERENCE_WIDTH = 2560
REFERENCE_HEIGHT = 1440


class ScreenGeometry(Protocol):
    def width(self) -> int: ...

    def height(self) -> int: ...


class ScreenLike(Protocol):
    def availableGeometry(self) -> ScreenGeometry: ...

    def logicalDotsPerInch(self) -> float: ...


@dataclass(frozen=True)
class UIScaleState:
    auto_percent: int
    delta_percent: int
    final_percent: int
    scale_factor: float


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def round_to_step(value: float, step: int) -> int:
    return int((value + step / 2) // step) * step


def normalize_ui_scale_delta_percent(value: object) -> int:
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        parsed = 0
    return clamp(round_to_step(parsed, 10), -50, 50)


def normalize_ui_scale_percent(value: object) -> int:
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        parsed = 100
    return clamp(round_to_step(parsed, 5), 35, 300)


def calculate_auto_percent(width: int, height: int, logical_dpi: float) -> int:
    dpi = logical_dpi if logical_dpi > 0 else BASE_LOGICAL_DPI
    normalized_width = width * dpi / BASE_LOGICAL_DPI
    normalized_height = height * dpi / BASE_LOGICAL_DPI
    ratio = min(normalized_width / REFERENCE_WIDTH, normalized_height / REFERENCE_HEIGHT)
    return clamp(round_to_step(ratio * 100, 10), 70, 200)


def calculate_final_percent(auto_percent: int, delta_percent: int) -> int:
    delta_reference = max(auto_percent, 100)
    raw_final = auto_percent + delta_reference * delta_percent / 100
    return clamp(round_to_step(raw_final, 5), 35, 300)


def calculate_target_window_height(base_height: int, scale_factor: float) -> int:
    return max(320, round(base_height * scale_factor))


def scale_px(value: int | float, scale_factor: float) -> int:
    return max(1, round(value * scale_factor))


def scale_point_size(value: int | float, scale_factor: float) -> float:
    return max(1.0, round(value * scale_factor * 2) / 2)


def resolve_ui_scale_from_screen(screen: ScreenLike, delta_percent: object) -> UIScaleState:
    geometry = screen.availableGeometry()
    auto_percent = calculate_auto_percent(
        geometry.width(), geometry.height(), screen.logicalDotsPerInch()
    )
    normalized_delta = normalize_ui_scale_delta_percent(delta_percent)
    final_percent = calculate_final_percent(auto_percent, normalized_delta)
    return UIScaleState(
        auto_percent=auto_percent,
        delta_percent=normalized_delta,
        final_percent=final_percent,
        scale_factor=final_percent / 100.0,
    )
