#It’s the file that defines the shape of the data going in and out of your API.
#“An upload response looks like this.” “A health check looks like that.” Everything else in the project can then trust those shapes.

from pydantic import BaseModel
class HealthResponse(BaseModel):
    status: str
    version: str


class DatasetInfo(BaseModel):
    # TODO: id (int), filename (str), rows (int),
    # columns (int), column_names (list[str])
    id: int
    filename: str
    rows: int
    columns: int
    column_names: list[str]
