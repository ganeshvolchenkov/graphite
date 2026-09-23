from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Wire format is camelCase (TypeScript frontend); Python stays snake_case."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
