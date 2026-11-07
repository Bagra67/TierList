import colorsys

import pytest

from app.constants.templates import DEFAULT_TIERS

INK_TEXT_COLOR: str = "#1D1640"
WCAG_AA_NORMAL_TEXT_CONTRAST: float = 4.5
HUE_DEGREES_WHERE_THE_RAMP_STARTS: float = 330


def channels(color: str) -> tuple[float, float, float]:
    return (
        int(color[1:3], 16) / 255,
        int(color[3:5], 16) / 255,
        int(color[5:7], 16) / 255,
    )


def relative_luminance(color: str) -> float:
    linear_channels: list[float] = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels(color)
    ]
    return 0.2126 * linear_channels[0] + 0.7152 * linear_channels[1] + 0.0722 * linear_channels[2]


def contrast_ratio(first_color: str, second_color: str) -> float:
    lighter_first: list[float] = sorted(
        (relative_luminance(first_color), relative_luminance(second_color)), reverse=True
    )
    return (lighter_first[0] + 0.05) / (lighter_first[1] + 0.05)


def hue_degrees_along_the_ramp(color: str) -> float:
    hue: float = colorsys.rgb_to_hsv(*channels(color))[0] * 360
    return (hue - HUE_DEGREES_WHERE_THE_RAMP_STARTS) % 360


@pytest.mark.parametrize(("tier_name", "color"), DEFAULT_TIERS)
def test_the_ink_text_stays_readable_on_every_default_tier(tier_name: str, color: str):
    assert contrast_ratio(color, INK_TEXT_COLOR) >= WCAG_AA_NORMAL_TEXT_CONTRAST


def test_the_default_tiers_go_from_warm_to_cold():
    hues: list[float] = [hue_degrees_along_the_ramp(color) for _, color in DEFAULT_TIERS]

    assert hues == sorted(hues)
