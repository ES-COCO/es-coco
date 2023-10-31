from pydantic import BaseModel


class DataSources(BaseModel):
    id: int
    name: str
    url: str
    citation: str
    format: str
    creator: str
    content: str
    size: str
    modality: str
    tagged: int
    scripted: int
    additional_info: str


class AnnotationSources(BaseModel):
    id: int
    name: str
    url: str
    additional_info: str


class AnnotationTypes(BaseModel):
    id: int
    name: str


class Tokens(BaseModel):
    id: int
    item_id: str
    surface_form: str
    token_index: int
    whisper_segment_id: int


class WhisperSegments(BaseModel):
    id: str
    data_source_id: int
    confidence: float
    start_time: str
    end_time: str


class ModelTokenID(BaseModel):
    model_token_id: str
    token_id: int
    annotation_source_id: int


class Annotations(BaseModel):
    id: int
    token_id: int
    type_id: int
    annotation_source_id: int
    value: str
    confidence: float
