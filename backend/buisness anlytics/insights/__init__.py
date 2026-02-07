"""
Insights Module - Rule-Based Business Intelligence

Generates human-readable insights based on calculated metrics.
No ML, just clear business rules.
"""

from .engine import (
    generate_insights,
    InsightRule,
)

__all__ = [
    "generate_insights",
    "InsightRule",
]
