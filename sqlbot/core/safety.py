"""
SQL safety analysis for SQLBot Core SDK

This module provides SQL safety analysis functionality independent of any UI.
"""

import re
from typing import List, Set
from .types import SafetyAnalysis, SafetyLevel


class SQLSafetyAnalyzer:
    """Analyzes SQL queries for dangerous operations"""
    
    # Dangerous SQL operations that modify data or schema
    DANGEROUS_OPERATIONS = {
        'CREATE', 'DROP', 'ALTER', 'TRUNCATE', 'DELETE', 'INSERT', 'UPDATE',
        'MERGE', 'REPLACE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE', 'CALL'
    }
    
    # Operations that might be concerning but not necessarily dangerous
    WARNING_OPERATIONS = {
        'BACKUP', 'RESTORE', 'BULK', 'OPENROWSET', 'OPENDATASOURCE'
    }
    
    def __init__(self, dangerous_mode: bool = False):
        self.dangerous_mode = dangerous_mode
    
    def analyze(self, sql_query: str) -> SafetyAnalysis:
        """
        Analyze SQL query for dangerous operations
        
        Args:
            sql_query: The SQL query to analyze
            
        Returns:
            SafetyAnalysis with safety level and detected operations
        """
        if not sql_query or not sql_query.strip():
            return SafetyAnalysis(
                level=SafetyLevel.SAFE,
                dangerous_operations=[],
                warnings=[],
                is_read_only=True,
                message="Empty query"
            )
        
        # Clean and normalize the query
        cleaned_query = self._clean_sql(sql_query)
        
        # Extract SQL keywords
        keywords = self._extract_keywords(cleaned_query)
        
        # Check for dangerous operations
        dangerous_ops = self._find_dangerous_operations(keywords)
        warning_ops = self._find_warning_operations(keywords)
        
        # Determine safety level
        if dangerous_ops:
            level = SafetyLevel.DANGEROUS
            message = f"Dangerous operations detected: {', '.join(dangerous_ops)}"
        elif warning_ops:
            level = SafetyLevel.WARNING
            message = f"Warning operations detected: {', '.join(warning_ops)}"
        else:
            level = SafetyLevel.SAFE
            message = "Query appears safe for execution"
        
        # Check if query is read-only
        is_read_only = not dangerous_ops and not any(
            op in keywords for op in ['INSERT', 'UPDATE', 'DELETE', 'MERGE', 'REPLACE']
        )
        
        return SafetyAnalysis(
            level=level,
            dangerous_operations=dangerous_ops,
            warnings=warning_ops,
            is_read_only=is_read_only,
            message=message
        )
    
    def is_safe_for_execution(self, sql_query: str) -> bool:
        """
        Quick check if query is safe for execution
        
        Args:
            sql_query: The SQL query to check
            
        Returns:
            True if safe to execute, False otherwise
        """
        analysis = self.analyze(sql_query)
        
        if not self.dangerous_mode:
            return analysis.level == SafetyLevel.SAFE and analysis.is_read_only
        else:
            return analysis.level != SafetyLevel.DANGEROUS
    
    def _clean_sql(self, sql_query: str) -> str:
        """Clean SQL query for analysis"""
        # Remove comments
        sql_query = re.sub(r'--.*$', '', sql_query, flags=re.MULTILINE)
        sql_query = re.sub(r'/\*.*?\*/', '', sql_query, flags=re.DOTALL)
        
        # Remove string literals to avoid false positives
        sql_query = re.sub(r"'[^']*'", "'STRING'", sql_query)
        sql_query = re.sub(r'"[^"]*"', '"STRING"', sql_query)
        
        return sql_query.upper()
    
    def _extract_keywords(self, sql_query: str) -> Set[str]:
        """Extract SQL keywords from query"""
        # Find SQL keywords (word boundaries)
        keywords = re.findall(r'\b[A-Z_][A-Z0-9_]*\b', sql_query)
        return set(keywords)
    
    def _find_dangerous_operations(self, keywords: Set[str]) -> List[str]:
        """Find dangerous operations in keywords"""
        found = []
        for op in self.DANGEROUS_OPERATIONS:
            if op in keywords:
                found.append(op)
        return sorted(found)
    
    def _find_warning_operations(self, keywords: Set[str]) -> List[str]:
        """Find warning operations in keywords"""
        found = []
        for op in self.WARNING_OPERATIONS:
            if op in keywords:
                found.append(op)
        return sorted(found)


# Global analyzer instance for backward compatibility
_default_analyzer = SQLSafetyAnalyzer()


def analyze_sql_safety(sql_query: str, dangerous_mode: bool = False) -> SafetyAnalysis:
    """
    Analyze SQL safety (backward compatible function)
    
    Args:
        sql_query: The SQL query to analyze
        dangerous_mode: Whether to allow dangerous operations
        
    Returns:
        SafetyAnalysis result
    """
    analyzer = SQLSafetyAnalyzer(dangerous_mode=dangerous_mode)
    return analyzer.analyze(sql_query)
