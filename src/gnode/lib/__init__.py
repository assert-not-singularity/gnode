"""Productionized algorithm layer — the single source of truth for the numpy
glitch routines that nodes wrap (promoted from ``reference/``; that directory is
kept as untouched provenance).

Import from the submodules directly (``gnode.lib.glitch`` / ``gnode.lib.artistic``)
— they are intentionally *not* flattened here because both define same-named
functions (e.g. ``pixel_sort``, ``channel_shift``).
"""

from __future__ import annotations
