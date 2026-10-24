from app.services.ui_scale_service import (
    calculate_auto_percent,
    calculate_final_percent,
    normalize_ui_scale_delta_percent,
    resolve_ui_scale_from_screen,
)


class Geometry:
    def __init__(self, width: int, height: int) -> None:
        self._width = width
        self._height = height

    def width(self) -> int:
        return self._width

    def height(self) -> int:
        return self._height


class Screen:
    def __init__(self, width: int, height: int, dpi: float) -> None:
        self.geometry = Geometry(width, height)
        self.dpi = dpi

    def availableGeometry(self) -> Geometry:
        return self.geometry

    def logicalDotsPerInch(self) -> float:
        return self.dpi


def test_reference_screen_is_one_hundred_percent() -> None:
    assert calculate_auto_percent(2560, 1440, 96.0) == 100


def test_scale_clamps_and_rounds_manual_delta() -> None:
    assert normalize_ui_scale_delta_percent(46) == 50
    assert normalize_ui_scale_delta_percent(-88) == -50
    assert calculate_final_percent(80, 50) == 130


def test_screen_resolution_produces_full_scale_state() -> None:
    state = resolve_ui_scale_from_screen(Screen(1920, 1080, 96.0), -10)
    assert state.auto_percent == 80
    assert state.delta_percent == -10
    assert state.final_percent == 70
    assert state.scale_factor == 0.7
