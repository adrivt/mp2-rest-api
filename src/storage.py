import logging

logger = logging.getLogger(__name__)


class DatasetStorage:
    def __init__(self):
        self._store = {}
        self._counter = 0

    def save(self, df, filename):
        """Store a copy of the data and return a new integer ID."""
        self._counter += 1
        dataset_id = self._counter
        self._store[dataset_id] = {"filename": filename, "data": df.copy()}
        logger.debug(f"Stored dataset: id={dataset_id}, rows={len(df)}")
        return dataset_id

    def get(self, dataset_id):
        """Return a copy of the stored DataFrame, or None."""
        entry = self._store.get(dataset_id)
        if entry is None:
            logger.debug(f"Dataset not found: id={dataset_id}")
            return None
        df = entry["data"].copy()
        logger.debug(f"Retrieved dataset copy: id={dataset_id}, rows={len(df)}")
        return df

    def get_metadata(self, dataset_id):
        """Return the dataset metadata, or None."""
        entry = self._store.get(dataset_id)
        if entry is None:
            logger.debug(f"Metadata not found: id={dataset_id}")
            return None
        df = entry["data"]
        metadata = {
            "id": dataset_id,
            "filename": entry["filename"],
            "rows": df.shape[0],
            "columns": df.shape[1],
            "column_names": list(df.columns),
        }
        logger.debug(f"Retrieved metadata: id={dataset_id}")
        return metadata

    def update(self, dataset_id, df):
        """Replace an existing dataset; return True, or False if missing."""
        if dataset_id not in self._store:
            logger.debug(f"Cannot update, dataset not found: id={dataset_id}")
            return False
        self._store[dataset_id]["data"] = df.copy()
        logger.debug(f"Updated dataset: id={dataset_id}, rows={len(df)}")
        return True

    def clear(self):
        """Clear all data and reset the ID counter."""
        self._store.clear()
        self._counter = 0
