import io
import json
import logging
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from src import DatasetInfo, DatasetStorage, HealthResponse, setup_logging, DatasetInfo, HealthResponse, ValidationSettings, MissingSettings, OutlierSettings, ProcessingSettings, ProcessConfig, ProcessingReport
from data_pipeline import create_cleaning_report, process_data, validate_dataframe


setup_logging(verbose=True)
logger = logging.getLogger(__name__)

app = FastAPI(title="Data Processing API", version="1.0.0")
storage = DatasetStorage()

@app.get("/health", response_model=HealthResponse)
def health_check():
    """Return the application status and version."""
    return {"status": "ok", "version": app.version}

@app.post("/upload", response_model=DatasetInfo)
async def upload_dataset(file: UploadFile = File(...)):
    """Read and store a CSV upload."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix != ".csv":
        logger.warning(f"Unsupported file format: {suffix}")
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as error:
        logger.warning(f"Could not parse CSV: {error}")
        raise HTTPException(status_code=400, detail="Could not read the uploaded CSV")

    dataset_id = storage.save(df, file.filename)
    logger.info(
        f"Uploaded dataset: id={dataset_id}, filename={file.filename}, rows={len(df)}"
    )
    return storage.get_metadata(dataset_id)

@app.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: int, limit: int = Query(default=100, ge=1)):
    """Return up to limit rows from a stored dataset."""
    df = storage.get(dataset_id)
    if df is None:
        logger.warning(f"Dataset not found: {dataset_id}")
        raise HTTPException(status_code=404, detail="Dataset not found")

    records = json.loads(df.head(limit).to_json(orient="records"))
    logger.info(f"Retrieved dataset: id={dataset_id}, returned_rows={len(records)}")

    return {"id": dataset_id, "data": records, "total_rows": len(df)}

@app.post("/datasets/{dataset_id}/process", response_model=ProcessingReport)
def process_dataset(dataset_id: int, config: ProcessConfig):
    """Validate and process a stored dataset using MP1 functions."""
    # TODO: retrieve, validate, process, report, update, and return.
    df=storage.get(dataset_id)
    if df is None:
            logger.warning(f"Dataset not found: {dataset_id}")
            raise HTTPException(status_code=404, detail="Dataset not found")
    config_dict = config.model_dump() #understand why we doing this more deeply. 
    required_columns = config_dict["validation"]["required_columns"]
    numeric_columns = config_dict["validation"]["numeric_columns"]

    missing = [col for col in numeric_columns if col not in df.columns]
    if missing:
        logger.warning(f"Missing numeric columns: {missing}")
        raise HTTPException(
            status_code=400, detail=f"Missing numeric columns: {missing}"
        )

    rows_before_validation = len(df)

    try:
        validated_df = validate_dataframe(df, required_columns, numeric_columns)
        validation_rows_removed = rows_before_validation - len(validated_df)

        df_before = validated_df.copy()
        processed_df = process_data(validated_df, config_dict)
    except ValueError as error:
        logger.warning(f"Processing failed: id={dataset_id}, error={error}")
        raise HTTPException(status_code=400, detail=str(error))

    report = create_cleaning_report(df_before, processed_df)
    storage.update(dataset_id, processed_df)

    logger.info(
        f"Processed dataset: id={dataset_id}, "
        f"validation_removed={validation_rows_removed}, "
        f"rows_before={report['rows_before']}, rows_after={report['rows_after']}"
    )

    return {
        "id": dataset_id,
        "validation_rows_removed": validation_rows_removed,
        "cleaning_report": report,
    }