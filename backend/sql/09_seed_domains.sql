-- Initial domain seed data
-- These are the business domains available in the system
-- Each domain maps to a Unity Catalog schema
-- Add new domains here as the business grows

INSERT INTO domains (name, uc_schema_name, description, created_by)
VALUES
    (
        'Finance',
        'finance',
        'Financial data including cost centers, GL codes and budget mappings',
        'system'
    ),
    (
        'Human Resources',
        'human_resources',
        'HR data including employee mappings, org structures and job codes',
        'system'
    ),
    (
        'Supply Chain',
        'supply_chain',
        'Supply chain data including vendor mappings, product codes and logistics',
        'system'
    ),
    (
        'Sales',
        'sales',
        'Sales data including territory mappings, customer segments and product hierarchies',
        'system'
    ),
    (
        'Operations',
        'operations',
        'Operational data including plant codes, cost center mappings and process classifications',
        'system'
    )
ON CONFLICT (name) DO NOTHING;