# MP2 — Data Processing REST API

A REST API built with FastAPI that wraps the data cleaning pipeline from MP1 and exposes it over HTTP. Clients can upload a CSV, retrieve its contents, and run validation and cleaning against it using a configuration sent in the request body. The pipeline itself is unchanged from MP1: it lives in `data_pipeline/` and is called directly by the API layer, so the same validation, duplicate removal, missing-value handling and outlier detection logic now runs on demand rather than from a YAML file on disk.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Returns the application status and version |
| POST | `/upload` | Accepts a CSV file, stores it, and returns its ID and metadata |
| GET | `/datasets/{id}` | Returns up to `limit` rows from a stored dataset |
| POST | `/datasets/{id}/process` | Validates and cleans a dataset using the supplied configuration |

Interactive documentation is available at `/docs` once the server is running.

## Structure

```
main.py              FastAPI application and endpoints
src/
  models.py          Pydantic request and response models
  storage.py         In-memory dataset storage
  middleware.py      Request logging, timing and request IDs
  utils.py           Logging configuration
data_pipeline/       MP1 pipeline, imported unchanged
tests/               Integration tests
```

## How it works

**Storage.** Datasets are held in memory by a single `DatasetStorage` instance created at module level, so they persist across requests for the lifetime of the server. Each dataset is stored with its filename and is copied on save, retrieval and update, which means a caller can modify a DataFrame they received without affecting what is stored. Metadata such as row count and column names is calculated from the current DataFrame rather than cached, so it stays accurate after processing.

**Validation.** Pydantic models define the shape of every request and response. Incoming data is validated before any endpoint code runs, which is why invalid input returns a 422 automatically. The `ProcessConfig` model mirrors the structure of MP1's `config.yaml`, so `model_dump()` produces exactly the dictionary the pipeline already expects.

**Processing.** The process endpoint retrieves the stored dataset, checks the configured numeric columns exist, runs MP1's `validate_dataframe()` and `process_data()`, and builds a cleaning report comparing the validated data against the processed result. Storage is only updated once both steps succeed, so a failed request leaves the original dataset intact.

**Middleware.** Every request is assigned a short request ID, timed, and logged with its method, path, status code and duration. The ID is returned to the client in an `X-Request-ID` header. Unhandled exceptions are logged with a full traceback and returned to the client as a generic 500 response without exposing internal details. Responses are logged at `INFO`, `WARNING` for 4xx and `ERROR` for 5xx.

## Running it

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python -m uvicorn main:app --reload
```

Run all commands from the repository root. The API is then available at `http://127.0.0.1:8000`, with documentation at `http://127.0.0.1:8000/docs`.

## Tests

```bash
python -m pytest tests -v
```

The test suite covers the health check, CSV upload, a full process-and-retrieve cycle, and error handling for missing datasets and invalid input.

## Notes

Storage is in memory only, so datasets are lost when the server restarts. This includes automatic restarts triggered by `--reload` during development. Processing replaces the stored dataset, so a fresh upload is needed before repeating a test that depends on the original data.