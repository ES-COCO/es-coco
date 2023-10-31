import sqlite3

from pydantic import BaseModel

from code_switching import schema


def insert_data_into_database(db_file: str, data_model: BaseModel):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    table_name = data_model.__class__.__name__
    fields = ", ".join(
        [field for field in data_model.__dict__["__annotations__"].keys()]
    )
    values = [getattr(data_model, field) for field in fields]

    placeholders = ", ".join(["?"] * len(fields))
    insert_query = f"INSERT INTO {table_name} ({fields}) VALUES ({placeholders})"

    cursor.execute(insert_query, values)
    conn.commit()
    conn.close()


# Example usage:
data_source = DataSources(
    id=1,
    name="Example Source",
    url="http://example.com",
    format="JSON",
    creator="John Doe",
    content="Sample data",
    size="100 MB",
    modality="Text",
    tagged=1,
    scripted=0,
)
insert_data_into_database("your_database.db", data_source)
