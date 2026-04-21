"""
Unit tests for ddl_builder.

All functions in ddl_builder are pure Python with no Spark or
database dependencies, so they are fully testable locally with
pytest.

Run from the project root:
    cd databricks
    python -m pytest tests/ -v
"""

import sys
import os

# Add src/ to the Python path so we can import ddl_builder
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ddl_builder import (
    escape_sql_string,
    build_column_definition,
    build_create_table_ddl,
    build_masking_function_ddl,
    build_pii_mask_statements,
    build_grant_statements,
)


# ---- escape_sql_string ----

def test_escape_sql_string_no_quotes():
    assert escape_sql_string("hello world") == "hello world"


def test_escape_sql_string_with_quote():
    assert escape_sql_string("it's great") == "it''s great"


def test_escape_sql_string_multiple_quotes():
    assert escape_sql_string("'a' 'b'") == "''a'' ''b''"


# ---- build_column_definition ----

def test_build_column_definition_simple():
    col = {
        "name": "region_code",
        "data_type": "STRING",
        "is_nullable": True,
        "is_pii": False,
        "description": "",
    }
    assert build_column_definition(col) == "region_code STRING"


def test_build_column_definition_not_null():
    col = {
        "name": "region_code",
        "data_type": "STRING",
        "is_nullable": False,
        "is_pii": False,
        "description": "",
    }
    result = build_column_definition(col)
    assert "NOT NULL" in result


def test_build_column_definition_with_comment():
    col = {
        "name": "region_code",
        "data_type": "STRING",
        "is_nullable": True,
        "is_pii": False,
        "description": "Unique regional identifier",
    }
    result = build_column_definition(col)
    assert "COMMENT 'Unique regional identifier'" in result


def test_build_column_definition_pii_flag():
    col = {
        "name": "email",
        "data_type": "STRING",
        "is_nullable": True,
        "is_pii": True,
        "description": "User email",
    }
    result = build_column_definition(col)
    assert "PII - masked | User email" in result


def test_build_column_definition_pii_no_description():
    col = {
        "name": "email",
        "data_type": "STRING",
        "is_nullable": True,
        "is_pii": True,
        "description": "",
    }
    result = build_column_definition(col)
    assert "PII - masked" in result


# ---- build_create_table_ddl ----

def test_build_create_table_ddl_basic():
    config = {
        "fully_qualified_name": "manualuploads.finance.region_mapping",
        "description": "Region mapping table",
        "columns": [
            {
                "name": "region_code",
                "data_type": "STRING",
                "is_included": True,
                "is_nullable": False,
                "is_pii": False,
                "column_order": 1,
                "description": "",
            },
            {
                "name": "cost_center",
                "data_type": "STRING",
                "is_included": True,
                "is_nullable": True,
                "is_pii": False,
                "column_order": 2,
                "description": "",
            },
        ],
    }
    ddl = build_create_table_ddl(config)
    assert "CREATE TABLE IF NOT EXISTS manualuploads.finance.region_mapping" in ddl
    assert "region_code STRING NOT NULL" in ddl
    assert "cost_center STRING" in ddl
    assert "USING DELTA" in ddl
    assert "COMMENT 'Region mapping table'" in ddl


def test_build_create_table_ddl_excluded_columns():
    config = {
        "fully_qualified_name": "manualuploads.finance.region_mapping",
        "description": "",
        "columns": [
            {
                "name": "region_code",
                "data_type": "STRING",
                "is_included": True,
                "is_nullable": False,
                "is_pii": False,
                "column_order": 1,
                "description": "",
            },
            {
                "name": "excluded_column",
                "data_type": "STRING",
                "is_included": False,
                "is_nullable": False,
                "is_pii": False,
                "column_order": 2,
                "description": "",
            },
        ],
    }
    ddl = build_create_table_ddl(config)
    assert "region_code" in ddl
    assert "excluded_column" not in ddl


def test_build_create_table_ddl_column_order():
    config = {
        "fully_qualified_name": "manualuploads.finance.region_mapping",
        "description": "",
        "columns": [
            {
                "name": "second",
                "data_type": "STRING",
                "is_included": True,
                "is_nullable": True,
                "is_pii": False,
                "column_order": 2,
                "description": "",
            },
            {
                "name": "first",
                "data_type": "STRING",
                "is_included": True,
                "is_nullable": True,
                "is_pii": False,
                "column_order": 1,
                "description": "",
            },
        ],
    }
    ddl = build_create_table_ddl(config)
    first_pos = ddl.find("first")
    second_pos = ddl.find("second")
    assert first_pos < second_pos


# ---- build_masking_function_ddl ----

def test_build_masking_function_ddl():
    ddl = build_masking_function_ddl("manualuploads", "finance")
    assert "CREATE OR REPLACE FUNCTION" in ddl
    assert "manualuploads.finance.mask_pii_string" in ddl
    assert "is_member" in ddl


# ---- build_pii_mask_statements ----

def test_build_pii_mask_statements_none():
    config = {
        "catalog": "manualuploads",
        "schema": "finance",
        "fully_qualified_name": "manualuploads.finance.t1",
        "columns": [
            {
                "name": "region_code",
                "data_type": "STRING",
                "is_included": True,
                "is_pii": False,
            },
        ],
    }
    assert build_pii_mask_statements(config) == []


def test_build_pii_mask_statements_two_pii_columns():
    config = {
        "catalog": "manualuploads",
        "schema": "finance",
        "fully_qualified_name": "manualuploads.finance.t1",
        "columns": [
            {
                "name": "region_code",
                "data_type": "STRING",
                "is_included": True,
                "is_pii": False,
            },
            {
                "name": "email",
                "data_type": "STRING",
                "is_included": True,
                "is_pii": True,
            },
            {
                "name": "phone",
                "data_type": "STRING",
                "is_included": True,
                "is_pii": True,
            },
        ],
    }
    statements = build_pii_mask_statements(config)
    assert len(statements) == 2
    assert any("ALTER COLUMN email SET MASK" in s for s in statements)
    assert any("ALTER COLUMN phone SET MASK" in s for s in statements)
    assert all("manualuploads.finance.mask_pii_string" in s for s in statements)


def test_build_pii_mask_skips_excluded_columns():
    config = {
        "catalog": "manualuploads",
        "schema": "finance",
        "fully_qualified_name": "manualuploads.finance.t1",
        "columns": [
            {
                "name": "excluded_pii",
                "data_type": "STRING",
                "is_included": False,
                "is_pii": True,
            },
        ],
    }
    assert build_pii_mask_statements(config) == []


# ---- build_grant_statements ----

def test_build_grant_statements():
    config = {
        "catalog": "manualuploads",
        "schema": "finance",
        "fully_qualified_name": "manualuploads.finance.region_mapping",
        "reader_group": "data-readers-finance",
    }
    grants = build_grant_statements(config)
    assert len(grants) == 3
    assert any("USE CATALOG ON CATALOG manualuploads" in g for g in grants)
    assert any("USE SCHEMA ON SCHEMA manualuploads.finance" in g for g in grants)
    assert any("SELECT ON TABLE manualuploads.finance.region_mapping" in g for g in grants)


def test_build_grant_statements_no_reader_group():
    config = {
        "catalog": "manualuploads",
        "schema": "finance",
        "fully_qualified_name": "manualuploads.finance.region_mapping",
        "reader_group": None,
    }
    assert build_grant_statements(config) == []


def test_build_grant_statements_empty_reader_group():
    config = {
        "catalog": "manualuploads",
        "schema": "finance",
        "fully_qualified_name": "manualuploads.finance.region_mapping",
        "reader_group": "",
    }
    assert build_grant_statements(config) == []