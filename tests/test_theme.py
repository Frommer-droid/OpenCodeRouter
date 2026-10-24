from app.core.app_config import COLORS
from app.ui.styles import build_global_stylesheet


def _relative_luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: str, second: str) -> float:
    lighter, darker = sorted(
        (_relative_luminance(first), _relative_luminance(second)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


def test_uses_one_dark_pro_palette() -> None:
    assert COLORS["background"] == "#282C34"
    assert COLORS["surface"] == "#21252B"
    assert COLORS["surface_alt"] == "#2C313C"
    assert COLORS["border"] == "#3E4451"
    assert COLORS["text"] == "#ABB2BF"
    assert COLORS["accent"] == "#61AFEF"
    assert COLORS["success"] == "#98C379"
    assert COLORS["danger"] == "#E06C75"
    assert COLORS["warning"] == "#D19A66"


def test_one_dark_text_and_state_pairs_meet_wcag_aa() -> None:
    for foreground, background in (
        (COLORS["text"], COLORS["background"]),
        (COLORS["muted"], COLORS["background"]),
        (COLORS["on_accent"], COLORS["accent"]),
        (COLORS["on_accent"], COLORS["success"]),
        (COLORS["on_accent"], COLORS["danger"]),
        (COLORS["success"], COLORS["selection"]),
        (COLORS["text"], COLORS["danger_surface"]),
        (COLORS["danger_text"], COLORS["danger_surface"]),
    ):
        assert _contrast(foreground, background) >= 4.5


def test_stylesheet_contains_no_previous_navy_green_palette() -> None:
    stylesheet = build_global_stylesheet(COLORS)
    for obsolete in ("#0F172A", "#192134", "#1E3A5F", "#22C55E", "#60A5FA"):
        assert obsolete not in stylesheet
