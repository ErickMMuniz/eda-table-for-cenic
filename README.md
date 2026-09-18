# EDA Process MLOps

A production-ready Python tool refactored from Google Colab for inspecting BigQuery dataset schemas, column statistics, partition requirements, periodicity, and exporting comprehensive data dictionaries into Excel reports.

## Project Structure

```
.
├── pyproject.toml         # UV project configuration and dependencies
├── README.md              # Project documentation
├── src/
│   ├── config/            # Configuration management settings
│   │   └── settings.py
│   ├── connection/        # GCP BigQuery connection using ADC
│   │   └── client.py
│   ├── models/            # Schema, Field, and Enum domain models
│   │   ├── enums.py
│   │   └── schema.py
│   ├── eda/               # Pipeline orchestrator and classification operators
│   │   ├── operators.py
│   │   └── pipeline.py
│   ├── io/                # Excel exporter and report handling
│   │   └── exporter.py
│   └── cli.py             # CLI entrypoint
└── tests/                 # Unit tests suite (pytest)
```

## Prerequisites & Installation

This project uses [UV](https://github.com/astral-sh/uv) for fast and reliable Python dependency management.

1. **Install UV** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Initialize Environment & Install Dependencies**:
   ```bash
   uv sync
   ```

## GCP Authentication

Replace any notebook/colab auth (`google.colab.auth`) with standard Google Cloud **Application Default Credentials (ADC)** or service account credentials.

Authenticate using the Google Cloud CLI:
```bash
gcloud auth application-default login
```

Alternatively, set the environment variable pointing to your service account key file:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
```

## Usage

You can run the CLI directly using `uv run eda-process` or `uv run python -m src.cli`.

### CLI Arguments

```bash
uv run eda-process --help
```

- `--project`: Google Cloud Project ID (default: `cpl-corp-mpd-prod-01082025`)
- `--dataset`: BigQuery Dataset Name or ID (default: `mlops_v01_shared`)
- `--output`: Output Excel report path (default: `Data_Dictionary_Report.xlsx`)

### Example Commands

Run with default parameters:
```bash
uv run eda-process
```

Run with custom project, dataset, and output path:
```bash
uv run eda-process --project my-gcp-project --dataset my_dataset --output my_report.xlsx
```

## Running Unit Tests

Run the test suite using `pytest`:

```bash
uv run pytest
```
