import csv
from typing import List, Optional

from sqlalchemy import Engine
from sqlalchemy.orm import (
    Mapped,
    Session,
    declarative_base,
    mapped_column,
    relationship,
)
from sqlalchemy.orm.properties import ForeignKey

from . import config

Base = declarative_base()


class Format(Base):
    __tablename__ = "Formats"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False, unique=True)


class DataSource(Base):
    __tablename__ = "DataSources"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    url: Mapped[str] = mapped_column()
    citation: Mapped[Optional[str]] = mapped_column()
    creator: Mapped[str] = mapped_column()
    content: Mapped[str] = mapped_column()
    size: Mapped[str] = mapped_column()
    tagged: Mapped[bool] = mapped_column()
    scripted: Mapped[bool] = mapped_column()
    additional_info: Mapped[Optional[str]] = mapped_column()
    format_id: Mapped[Optional[int]] = mapped_column(ForeignKey("Formats.id"))
    format: Mapped[Optional["Format"]] = relationship()


class AnnotationSource(Base):
    __tablename__ = "AnnotationSources"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    url: Mapped[str] = mapped_column()
    additional_info: Mapped[Optional[str]] = mapped_column()


class AnnotationType(Base):
    __tablename__ = "AnnotationTypes"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)


class Token(Base):
    __tablename__ = "Tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    surface_form: Mapped[str] = mapped_column()
    token_index: Mapped[int] = mapped_column()
    transcription_source_id: Mapped[int] = mapped_column(
        ForeignKey("AnnotationSources.id")
    )
    transcription_source: Mapped["AnnotationSource"] = relationship()
    segment_id: Mapped[int] = mapped_column(ForeignKey("Segments.id"))
    segment: Mapped["Segment"] = relationship()
    annotations: Mapped[List["Annotation"]] = relationship(back_populates="token")


class Segment(Base):
    __tablename__ = "Segments"
    id: Mapped[int] = mapped_column(primary_key=True)
    confidence: Mapped[Optional[float]] = mapped_column()
    start_ms: Mapped[int] = mapped_column()
    end_ms: Mapped[int] = mapped_column()
    data_source_id: Mapped[int] = mapped_column(ForeignKey("DataSources.id"))
    data_source: Mapped["DataSource"] = relationship()


class Annotation(Base):
    __tablename__ = "Annotations"
    id: Mapped[int] = mapped_column(primary_key=True)
    value: Mapped[str] = mapped_column()
    confidence: Mapped[float] = mapped_column()
    token_id: Mapped[int] = mapped_column(ForeignKey("Tokens.id"))
    token: Mapped["Token"] = relationship(back_populates="annotations")
    annotation_type_id: Mapped[int] = mapped_column(ForeignKey("AnnotationTypes.id"))
    annotation_type: Mapped["AnnotationType"] = relationship()
    annotation_source_id: Mapped[int] = mapped_column(
        ForeignKey("AnnotationSources.id")
    )
    annotation_source: Mapped["AnnotationSource"] = relationship()


def initialize(engine: Engine):
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        audio_fmt = Format(name="audio")
        text_fmt = Format(name="text")
        session.add_all(
            [
                audio_fmt,
                text_fmt,
                AnnotationType(name="language"),
                AnnotationType(name="pos"),
                AnnotationSource(
                    name="whisper-small",
                    url="https://huggingface.co/openai/whisper-small",
                ),
                AnnotationSource(
                    name="BERT-lid-lince",
                    url="https://huggingface.co/sagorsarker/codeswitch-spaeng-lid-lince",
                ),
                AnnotationSource(
                    name="BERT-pos-lince",
                    url="https://huggingface.co/sagorsarker/codeswitch-spaeng-pos-lince",
                ),
            ]
        )

        with (config.DATA_DIR / "metadata.tsv").open("r") as f:
            data_sources = []
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                fmt = {"spoken": audio_fmt.id, "written": text_fmt.id}.get(
                    row["Modality"].lower()
                )
                data_sources.append(
                    DataSource(
                        name=row["Name"].strip(),
                        url=row["Link"].strip(),
                        format_id=fmt,
                        creator=row["Creator"].strip(),
                        content=row["Content"].strip(),
                        size=row["Size"].strip(),
                        tagged=row["Tagged"].lower() == "y",
                        scripted=row["Scripted"].lower() == "n",
                        additional_info=row["Comments"].strip() or None,
                    )
                )
        session.bulk_save_objects(data_sources)
        session.commit()
