"""
Unit tests for SQLBot Core SDK Safety Analysis
"""

import pytest
from sqlbot.core.safety import SQLSafetyAnalyzer, analyze_sql_safety
from sqlbot.core.types import SafetyLevel


class TestSQLSafetyAnalyzer:
    """Test SQL safety analysis functionality"""
    
    def test_safe_queries(self):
        """Test that safe queries are identified correctly"""
        analyzer = SQLSafetyAnalyzer()
        
        safe_queries = [
            "SELECT * FROM users",
            "SELECT COUNT(*) FROM orders WHERE date > '2023-01-01'",
            "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id",
            "WITH cte AS (SELECT * FROM products) SELECT * FROM cte",
        ]
        
        for query in safe_queries:
            analysis = analyzer.analyze(query)
            assert analysis.level == SafetyLevel.SAFE, f"Query should be safe: {query}"
            assert analysis.is_read_only == True, f"Query should be read-only: {query}"
            assert len(analysis.dangerous_operations) == 0
    
    def test_dangerous_queries(self):
        """Test that dangerous queries are identified correctly"""
        analyzer = SQLSafetyAnalyzer()
        
        dangerous_queries = [
            ("DROP TABLE users", ["DROP"]),
            ("DELETE FROM users WHERE id = 1", ["DELETE"]),
            ("INSERT INTO users (name) VALUES ('test')", ["INSERT"]),
            ("UPDATE users SET name = 'new' WHERE id = 1", ["UPDATE"]),
            ("CREATE TABLE test (id INT)", ["CREATE"]),
            ("ALTER TABLE users ADD COLUMN email VARCHAR(255)", ["ALTER"]),
            ("TRUNCATE TABLE logs", ["TRUNCATE"]),
        ]
        
        for query, expected_ops in dangerous_queries:
            analysis = analyzer.analyze(query)
            assert analysis.level == SafetyLevel.DANGEROUS, f"Query should be dangerous: {query}"
            assert analysis.is_read_only == False, f"Query should not be read-only: {query}"
            assert set(analysis.dangerous_operations) == set(expected_ops), f"Wrong operations detected for: {query}"
    
    def test_warning_queries(self):
        """Test that warning queries are identified correctly"""
        analyzer = SQLSafetyAnalyzer()
        
        warning_queries = [
            ("BACKUP DATABASE test TO DISK = 'backup.bak'", ["BACKUP"]),
            ("RESTORE DATABASE test FROM DISK = 'backup.bak'", ["RESTORE"]),
        ]
        
        for query, expected_ops in warning_queries:
            analysis = analyzer.analyze(query)
            assert analysis.level == SafetyLevel.WARNING, f"Query should be warning: {query}"
            assert set(analysis.warnings) == set(expected_ops), f"Wrong warnings detected for: {query}"
    
    def test_dangerous_mode(self):
        """Test dangerous mode enforcement"""
        analyzer = SQLSafetyAnalyzer(dangerous_mode=False)
        
        # Safe query should still be safe
        safe_analysis = analyzer.analyze("SELECT * FROM users")
        assert analyzer.is_safe_for_execution("SELECT * FROM users") == True
        
        # Dangerous query should not be safe for execution when dangerous mode is disabled
        dangerous_analysis = analyzer.analyze("DELETE FROM users")
        assert analyzer.is_safe_for_execution("DELETE FROM users") == False
    
    def test_empty_query(self):
        """Test handling of empty queries"""
        analyzer = SQLSafetyAnalyzer()
        
        empty_queries = ["", "   ", "\n\t  \n"]
        
        for query in empty_queries:
            analysis = analyzer.analyze(query)
            assert analysis.level == SafetyLevel.SAFE
            assert analysis.message == "Empty query"
    
    def test_sql_cleaning(self):
        """Test SQL cleaning removes comments and strings"""
        analyzer = SQLSafetyAnalyzer()
        
        # Query with comments and strings that might contain dangerous keywords
        query_with_comments = """
        SELECT * FROM users 
        -- This comment mentions DROP but it's just a comment
        WHERE name != 'DELETE this user'  /* Another comment with CREATE */
        """
        
        analysis = analyzer.analyze(query_with_comments)
        assert analysis.level == SafetyLevel.SAFE
        assert len(analysis.dangerous_operations) == 0
    
    def test_backward_compatibility_function(self):
        """Test the backward compatibility function"""
        # Test safe query
        analysis = analyze_sql_safety("SELECT * FROM users")
        assert analysis.level == SafetyLevel.SAFE
        
        # Test dangerous query
        analysis = analyze_sql_safety("DROP TABLE users")
        assert analysis.level == SafetyLevel.DANGEROUS
        
        # Test read-only mode
        analysis = analyze_sql_safety("DELETE FROM users", dangerous_mode=False)
        assert analysis.level == SafetyLevel.DANGEROUS


class TestSafetyAnalysisDataClass:
    """Test SafetyAnalysis data class"""
    
    def test_safety_analysis_creation(self):
        """Test creating SafetyAnalysis objects"""
        from sqlbot.core.types import SafetyAnalysis
        
        analysis = SafetyAnalysis(
            level=SafetyLevel.DANGEROUS,
            dangerous_operations=["DROP", "DELETE"],
            warnings=["BACKUP"],
            is_read_only=False,
            message="Dangerous operations detected"
        )
        
        assert analysis.level == SafetyLevel.DANGEROUS
        assert analysis.dangerous_operations == ["DROP", "DELETE"]
        assert analysis.warnings == ["BACKUP"]
        assert analysis.is_read_only == False
        assert analysis.message == "Dangerous operations detected"