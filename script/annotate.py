from collections import defaultdict
from csv import DictReader
from itertools import chain
from pathlib import Path
from typing import DefaultDict, List, Optional, Tuple

import typer
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select, func, select
from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline

from code_switching.schema import (
    AnnotationSource,
    AnnotationType,
    DataSource,
    Segment,
    Token,
    TokenAnnotation,
    Word,
    WordAnnotation,
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


def get_one_row(query: Select, session: Session):
    result = session.scalar(query)
    assert result is not None
    return result


def fetch_metadata(
    source_name: str,
    model_name: str,
    lid_pretrained: str,
    pos_pretrained: str,
    session: Session,
):
    source = get_one_row(
        select(DataSource).where(DataSource.name == source_name), session
    )
    model = get_one_row(
        select(AnnotationSource).where(AnnotationSource.name == model_name), session
    )
    lid_model = get_one_row(
        select(AnnotationSource).where(
            AnnotationSource.url == f"https://huggingface.co/{lid_pretrained}"
        ),
        session,
    )
    pos_model = get_one_row(
        select(AnnotationSource).where(
            AnnotationSource.url == f"https://huggingface.co/{pos_pretrained}"
        ),
        session,
    )
    lid_type = get_one_row(
        select(AnnotationType).where(AnnotationType.name == "language"), session
    )
    pos_type = get_one_row(
        select(AnnotationType).where(AnnotationType.name == "pos"), session
    )
    switch_type = get_one_row(
        select(AnnotationType).where(AnnotationType.name == "switch"), session
    )

    if any(x is None for x in (source, model, lid_model, pos_model)):
        raise RuntimeError("Source or model is not in database!")

    return source, model, lid_model, pos_model, lid_type, pos_type, switch_type


def read_segments(
    path: Path, session: Session, source: DataSource
) -> Tuple[List[Segment], List[Tuple[str, int]]]:
    segment_ids = LocalIdManager(Segment, session)
    segments = []
    texts = []
    with path.open("r") as f:
        reader = DictReader(f)
        cur_text = ""
        cur_start = None
        cur_end = None
        for row in reader:
            text = row["text"]
            # Skip [music], [singing], etc.
            if text.startswith("[") and text.endswith("]"):
                continue
            # Clean up artifacts that are introduced occasionally
            if text.startswith(">>"):
                text.replace(">>", "")

            cur_text += text
            cur_end = row["end"]
            if cur_start is None:
                cur_start = row["start"]
            if text[-1] in ".?!":
                segment = Segment(
                    id=segment_ids.next_id(),
                    start_ms=cur_start,
                    end_ms=cur_end,
                    data_source_id=source.id,
                )
                segments.append(segment)
                texts.append((cur_text, segment.id))
                cur_text = ""
                cur_start = None
        return segments, texts


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
        (
            source,
            model,
            lid_model_meta,
            pos_model_meta,
            lid_type,
            pos_type,
            switch_type,
        ) = fetch_metadata(
            source_name, model_name, lid_pretrained, pos_pretrained, session
        )
        token_ids = LocalIdManager(Token, session)

        segments, texts = read_segments(path, session, source)
        tokens: DefaultDict[Tuple[int, int], List[Token]] = defaultdict(list)
        annotations: DefaultDict[
            Tuple[int, int], DefaultDict[Tuple[int, int], List[TokenAnnotation]]
        ] = defaultdict(lambda: defaultdict(list))

        for text, segment_id in texts:
            lid_out: List[dict] = lid_pipe(text)  # type: ignore
            pos_out: List[dict] = pos_pipe(text)  # type: ignore
            tokenizer_word_ids: List[int] = lid_tokenizer(
                text, add_special_tokens=False
            ).word_ids()
            prev_token = None
            prev_lang = None
            prev_lang_conf = None
            prev_w_id = None
            for lid, pos, w_id in zip(lid_out, pos_out, tokenizer_word_ids):
                assert lid["word"] == pos["word"]
                token_text = lid["word"]
                token = Token(
                    id=token_ids.next_id(),
                    surface_form=token_text,
                    token_index=lid["index"],
                    segment_id=segment_id,
                    transcription_source_id=model.id,
                )
                tokens[(segment_id, w_id)].append(token)
                lang = iso_lookup.get(lid["entity"], "n/a")
                lang_conf = lid["score"]
                lang_annotation = TokenAnnotation(
                    value=lang,
                    confidence=lang_conf,
                    token_id=token.id,
                    annotation_type_id=lid_type.id,
                    annotation_source_id=lid_model_meta.id,
                )

                annotations[(segment_id, w_id)][(lid_type.id, lid_model_meta.id)].append(
                    lang_annotation
                )

                pos_annotation = TokenAnnotation(
                    value=pos["entity"],
                    confidence=pos["score"],
                    token_id=token.id,
                    annotation_type_id=pos_type.id,
                    annotation_source_id=pos_model_meta.id,
                )
                annotations[(segment_id, w_id)][(pos_type.id, pos_model_meta.id)].append(
                    pos_annotation
                )

                language_switched = all(
                    (
                        prev_token is not None,
                        prev_lang != lang,
                        prev_lang in languages,
                        lang in languages,
                    )
                )
                if language_switched:
                    annotations[(segment_id, w_id)][
                        (switch_type.id, lid_model_meta.id)
                    ].append(
                        TokenAnnotation(
                            value="from",
                            confidence=prev_lang_conf * lang_conf,
                            token_id=prev_token.id,  # type: ignore
                            annotation_type_id=switch_type.id,
                            annotation_source_id=lid_model_meta.id,
                        )
                    )
                    annotations[(segment_id, prev_w_id)][(switch_type.id, lid_model_meta.id)].append(  # type: ignore
                        TokenAnnotation(
                            value="into",
                            confidence=prev_lang_conf * lang_conf,
                            token_id=token.id,
                            annotation_type_id=switch_type.id,
                            annotation_source_id=lid_model_meta.id,
                        )
                    )
                prev_w_id = w_id
                prev_token = token
                prev_lang = lang
                prev_lang_conf = lang_conf

        word_ids = LocalIdManager(Word, session)
        word_annotation_ids = LocalIdManager(WordAnnotation, session)
        words: List[Word] = []
        word_annotations: List[WordAnnotation] = []
        for (s_id, w_id), word_tokens in tokens.items():
            word_id = word_ids.next_id()
            word_surface_form = lid_tokenizer.convert_tokens_to_string(
                [t.surface_form for t in word_tokens]
            )
            words.append(
                Word(
                    id=word_id,
                    surface_form=word_surface_form,
                )
            )
            for t in word_tokens:
                t.word_id = word_id
            for (type_id, source_id), anns in annotations[(s_id, w_id)].items():
                word_annotation_id = word_annotation_ids.next_id()
                ann_values = defaultdict(lambda: 0.0)
                for a in anns:
                    # TODO: handle switches differently
                    a.word_annotation_id = word_annotation_id
                    ann_values[a.value] += a.confidence
                value, confidence = max(ann_values.items(), key=lambda k: k[1])
                confidence /= sum(ann_values.values())
                word_annotations.append(
                    WordAnnotation(
                        value=value,
                        confidence=confidence,
                        word_id=word_id,
                        annotation_type_id=type_id,
                        annotation_source_id=source_id,
                    )
                )
        session.bulk_save_objects(
            chain(
                segments,
                chain.from_iterable(tokens.values()),
                chain.from_iterable(chain.from_iterable(d.values() for d in annotations.values())),
                words,
                word_annotations,
            )
        )
        session.commit()


if __name__ == "__main__":
    typer.run(main)
