"""What the scrubber and the hotkey reference paint with: purpose names over the family's
hues and tiers.

These lived in ``shared_ui.colors`` under a section headed with this app's
name, where genaumacher was the one app reading them; a shared palette's job is the
hue and the tier ladder, and an app's mapping of "loop frame" onto red belongs
beside the widget that draws it.  Every one is an alias, so the scrubber stays
on the family's colors and nothing here can drift a shade away from them.
"""

from __future__ import annotations

from shared_ui.colors import (
    BLUE,
    BLUE_LIGHT,
    BORDER_DEFAULT,
    GREEN,
    RED,
    TEXT_MUTED,
    TEXT_SECONDARY,
    WHITE,
    YELLOW,
)

# The hotkey reference's two tiers are the body tiers: a label reads as body text and the
# " or " between items reads as muted.
TEXT_HOTKEY_REFERENCE_LABEL = TEXT_SECONDARY
TEXT_HOTKEY_REFERENCE_JOIN = TEXT_MUTED

# A scrubber's outline and its ticks are the standard border.
BORDER_SCRUBBER = BORDER_DEFAULT
BORDER_TICK = BORDER_DEFAULT

# There is one blue in the family: the bounds is it, and the range in
# play is it tinted lighter.
SCRUBBER_BOUNDS = BLUE
SCRUBBER_IN_OUT = BLUE_LIGHT
SCRUBBER_CURSOR = WHITE
SCRUBBER_LOOP = RED
# The two suggested points are marks that can land on either range, so each is
# a hue neither range wears.
SCRUBBER_SUGGESTED_IN = YELLOW
SCRUBBER_SUGGESTED_OUT = GREEN
