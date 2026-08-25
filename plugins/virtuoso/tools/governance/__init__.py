"""Virtuoso governance layer.

A provider-based governance model: each project declares its live work register,
terminal ledger, compatibility artifacts, ownership rules, and permitted
mutations, and the plugin resolves everything through that declaration rather
than assuming a fixed layout or a fixed authority.
"""
from __future__ import annotations

from .schema import SCHEMA_VERSION, SUPPORTED_SCHEMA_VERSIONS, PLUGIN_COMPATIBILITY

__all__ = ["SCHEMA_VERSION", "SUPPORTED_SCHEMA_VERSIONS", "PLUGIN_COMPATIBILITY"]
