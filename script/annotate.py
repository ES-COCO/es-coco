from csv import DictReader
from pathlib import Path
from typing import List, Optional

import typer
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select, func, select
from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline

from code_switching.schema import (
    Annotation,
    AnnotationSource,
    AnnotationType,
    DataSource,
    Segment,
    Token,
)
from code_switching.schema import initialize as initialize_db

iso_lookup = {"en": "eng", "spa": "spa"}
languages = list(iso_lookup.values())


class LocalIdManager:
    def __init__(self, schema, session: Session):
        self.current_id: int = session.scalar(select(func.max(schema.id))) or 1

    def next_id(self) -> int:
        i = self.current_id
        self.current_id += 1
        return i


def get_one(query: Select, session: Session):
    result = session.scalar(query)
    assert result is not None
    return result


def main(path: Path, model_name: str, source_name: str, db: Optional[Path] = None):
    prev_db_exists = db and db.exists()
    engine = create_engine(f"sqlite:///{db or ':memory:'}")

    # Initialize the DB tables if the DB didn't exist already
    if not prev_db_exists:
        initialize_db(engine)

    lid_pretrained = "sagorsarker/codeswitch-spaeng-lid-lince"
    pos_pretrained = "sagorsarker/codeswitch-spaeng-pos-lince"

    lid_tokenizer = AutoTokenizer.from_pretrained(lid_pretrained)
    lid_model = AutoModelForTokenClassification.from_pretrained(lid_pretrained)
    lid_pipe = pipeline(
        "token-classification", model=lid_model, tokenizer=lid_tokenizer
    )
    pos_tokenizer = AutoTokenizer.from_pretrained(pos_pretrained)
    pos_model = AutoModelForTokenClassification.from_pretrained(pos_pretrained)
    pos_pipe = pipeline(
        "token-classification", model=pos_model, tokenizer=pos_tokenizer
    )

    with Session(engine) as session:
        segment_ids = LocalIdManager(Segment, session)
        token_ids = LocalIdManager(Token, session)

        # Fetch the metadata
        source = get_one(
            select(DataSource).where(DataSource.name == source_name), session
        )
        model = get_one(
            select(AnnotationSource).where(AnnotationSource.name == model_name), session
        )
        lid_model = get_one(
            select(AnnotationSource).where(
                AnnotationSource.url == f"https://huggingface.co/{lid_pretrained}"
            ),
            session,
        )
        pos_model = get_one(
            select(AnnotationSource).where(
                AnnotationSource.url == f"https://huggingface.co/{pos_pretrained}"
            ),
            session,
        )
        lid_type = get_one(
            select(AnnotationType).where(AnnotationType.name == "language"), session
        )
        pos_type = get_one(
            select(AnnotationType).where(AnnotationType.name == "pos"), session
        )
        switch_type = get_one(
            select(AnnotationType).where(AnnotationType.name == "switch"), session
        )

        if any(x is None for x in (source, model, lid_model, pos_model)):
            raise RuntimeError("Source or model is not in database!")

        with Session(engine) as session:
            segments = []
            tokens = []
            annotations = []
            with path.open("r") as f:
                reader = DictReader(f)
                texts = []
                for row in reader:
                    text = row["text"]
                    # Skip [music], [singing], etc.
                    if text.startswith("[") and text.endswith("]"):
                        continue
                    # Clean up artifacts that are introduced occasionally
                    if text.startswith(">>"):
                        text.replace(">>", "")
                    segment = Segment(
                        id=segment_ids.next_id(),
                        start_ms=row["start"],
                        end_ms=row["end"],
                        data_source_id=source.id,
                    )
                    segments.append(segment)
                    texts.append((text, segment.id))

                prev_token = None
                prev_lang = None
                prev_lang_conf = None
                for text, segment_id in texts:
                    # Run annotation pipelines
                    lid_out: List[dict] = lid_pipe(text)  # type: ignore
                    pos_out: List[dict] = pos_pipe(text)  # type: ignore
                    for lid, pos in zip(lid_out, pos_out):
                        assert lid["word"] == pos["word"]
                        token = Token(
                            id=token_ids.next_id(),
                            surface_form=lid["word"],
                            token_index=lid["index"],
                            segment_id=segment_id,
                            transcription_source_id=model.id,
                        )
                        tokens.append(token)
                        lang = iso_lookup.get(lid["entity"], "n/a")
                        lang_conf = lid["score"]
                        annotations.append(
                            Annotation(
                                value=lang,
                                confidence=lang_conf,
                                token_id=token.id,
                                annotation_type_id=lid_type.id,
                                annotation_source_id=lid_model.id,
                            )
                        )
                        annotations.append(
                            Annotation(
                                value=pos["entity"],
                                confidence=pos["score"],
                                token_id=token.id,
                                annotation_type_id=pos_type.id,
                                annotation_source_id=pos_model.id,
                            )
                        )

                        if (
                            prev_token is not None
                            and prev_lang != lang
                            and (prev_lang in languages)
                            and (lang in languages)
                        ):
                            annotations.append(
                                Annotation(
                                    value="from",
                                    confidence=prev_lang_conf * lang_conf,
                                    token_id=prev_token.id,
                                    annotation_type_id=switch_type.id,
                                    annotation_source_id=lid_model.id,
                                )
                            )
                            annotations.append(
                                Annotation(
                                    value="into",
                                    confidence=prev_lang_conf * lang_conf,
                                    token_id=token.id,
                                    annotation_type_id=switch_type.id,
                                    annotation_source_id=lid_model.id,
                                )
                            )
                        prev_token = token
                        prev_lang = lang
                        prev_lang_conf = lang_conf
            session.bulk_save_objects(segments + tokens + annotations)
            session.commit()


if __name__ == "__main__":
    typer.run(main)
