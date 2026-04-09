# Manual File Uploader

A centralized, governance-first web application that allows business and 
functional consultants to manage manual mapping files and automatically 
sync them to Unity Catalog tables in Azure Databricks.

## The Problem

In data engineering projects, business teams maintain manual mapping files
that enrich raw pipeline data. These files are scattered across emails,
SharePoint folders and local drives with no versioning, no validation and
no governance. This creates maintenance nightmares and data quality risks.

## The Solution

Manual File Uploader provides a self-service portal where business users can:

- Create templates that define the structure of their mapping files
- Go through a governed approval workflow before any table is created
- Upload new versions of their files with automatic validation
- Let the tool handle writing clean, validated data to Unity Catalog

## Key Features

- Template creation with column-level configuration
- PII detection and automatic column masking in Unity Catalog
- Configurable data quality constraints (NOT NULL, UNIQUE etc.)
- Multi-reviewer approval workflow with email notifications
- Automatic Delta table creation in Unity Catalog on approval
- File validation with configurable bad row threshold
- Full upload history and audit trail
- Azure AD authentication

## Tech Stack

- **Frontend:** React
- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL
- **File Storage:** Azure Blob Storage
- **Authentication:** Azure AD
- **Compute:** Azure Databricks (PySpark)
- **Data Catalog:** Unity Catalog (Delta Lake)
- **Email:** Azure Communication Services

## Project Status

🚧 Under active development

## Setup Instructions

Coming soon as the project is built.

## Author

Built by **Mohsin Alam** as an open source tool for data engineering teams.

## License

MIT License — free to use, modify and distribute.