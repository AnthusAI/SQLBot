"""
SQLBot Core SDK

This package provides the core SQLBot functionality independent of any presentation layer.
It can be used by different interfaces: REPL, Lambda, FastMCP, web APIs, etc.
"""

from .agent import SQLBotAgent
from .config import SQLBotConfig
from .types import (
    QueryResult, 
    QueryType, 
    SafetyLevel, 
    SafetyAnalysis,
    CompilationResult,
    TableInfo,
    ProfileInfo
)

__all__ = [
    'SQLBotAgent',
    'SQLBotConfig', 
    'QueryResult',
    'QueryType',
    'SafetyLevel',
    'SafetyAnalysis',
    'CompilationResult',
    'TableInfo',
    'ProfileInfo'
]
