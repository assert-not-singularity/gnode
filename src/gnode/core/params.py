"""Typed widget-field factories (plan §3.3).

Each factory returns a Pydantic ``Field`` whose ``json_schema_extra`` carries a
``widget`` hint the frontend reads to choose a control. The emitted JSON Schema
stays the single serialized contract; validation constraints (``ge``/``le``)
ride along where they make sense. Using typed factories instead of hand-written
``json_schema_extra`` dicts means a widget-metadata mistake fails at import.

The factories are intentionally capitalized (they read like field types, à la
Pydantic's ``Field``); ``N802`` is ignored for this module in ``pyproject.toml``.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field


def _field(default: Any, widget: str, *, extra: dict | None = None, **kwargs: Any) -> Any:
    schema_extra: dict[str, Any] = {"widget": widget}
    if extra:
        schema_extra.update(extra)
    return Field(default, json_schema_extra=schema_extra, **kwargs)


def Slider(default: float, *, min: float, max: float, step: float = 1, **kw: Any) -> Any:
    """A ranged number rendered as a slider."""
    return _field(
        default, "slider", extra={"min": min, "max": max, "step": step}, ge=min, le=max, **kw
    )


def Number(
    default: float,
    *,
    min: float | None = None,
    max: float | None = None,
    step: float | None = None,
    **kw: Any,
) -> Any:
    """A plain number input (optionally bounded)."""
    constraints: dict[str, Any] = {}
    if min is not None:
        constraints["ge"] = min
    if max is not None:
        constraints["le"] = max
    extra = {k: v for k, v in (("min", min), ("max", max), ("step", step)) if v is not None}
    return _field(default, "number", extra=extra, **constraints, **kw)


def Toggle(default: bool = False, **kw: Any) -> Any:
    return _field(default, "toggle", **kw)


def Text(default: str = "", **kw: Any) -> Any:
    return _field(default, "string", **kw)


def SeedField(default: int = 0, **kw: Any) -> Any:
    return _field(default, "seed", ge=0, **kw)


def ColorField(default: tuple[int, int, int] = (0, 0, 0), **kw: Any) -> Any:
    return _field(list(default), "color", **kw)


def Vec2Field(default: tuple[float, float] = (0.0, 0.0), **kw: Any) -> Any:
    return _field(list(default), "vec2", **kw)


def CodeField(default: str = "", *, language: str = "python", **kw: Any) -> Any:
    return _field(default, "code", extra={"language": language}, **kw)


def Choice(default: Any, choices: list[Any], **kw: Any) -> Any:
    """An explicit dropdown. (A ``Literal[...]``-typed field is preferred when the
    choices are static — Pydantic emits ``enum`` in the schema automatically.)"""
    return _field(default, "enum", extra={"choices": list(choices)}, **kw)
