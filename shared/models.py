from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

# --------------------------------------------------------------------------- #

class CollectorModel(Base):
    __tablename__ = 'collector'

    id = Column(Integer, primary_key=True, autoincrement=True)
    short_name = Column(String(255), nullable=False)
    long_name = Column(String(255), nullable=False)
    enabled = Column(Boolean, default=True)

    sources = relationship("SourceModel", back_populates="collector")

# --------------------------------------------------------------------------- #

class SourceModel(Base):
    __tablename__ = 'source'

    id = Column(Integer, primary_key=True, autoincrement=True)
    collector_id = Column(Integer, ForeignKey('collector.id'), nullable=False)
    uid = Column(String(255), nullable=False)
    friendly_name = Column(String(255), nullable=True)
    user_note = Column(String(1024), nullable=True)
    enabled = Column(Boolean, default=True)
    source_metadata = Column('metadata', Text, nullable=True)

    collector = relationship("CollectorModel", back_populates="sources")
    contents = relationship("ContentModel", back_populates="source")

# --------------------------------------------------------------------------- #

class ContentModel(Base):
    __tablename__ = 'content'

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey('source.id'), nullable=False)
    collection_time = Column(DateTime, default=datetime.utcnow)
    origin_time = Column(DateTime)
    translated = Column(Boolean, default=False)
    analysed = Column(Boolean, default=False)
    original_text = Column(Text)
    translated_text = Column(Text)
    content_metadata = Column('metadata', Text)

    source = relationship("SourceModel", back_populates="contents")
    analysis_results = relationship("AnalysisResultModel", back_populates="content")

# --------------------------------------------------------------------------- #

class AnalysisRequirementModel(Base):
    __tablename__ = 'analysis_requirement'

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey('source.id'), nullable=False)
    llm_id = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    prompt = Column(Text)
    enabled = Column(Boolean, default=True)

    source = relationship("SourceModel")
    analysis_results = relationship("AnalysisResultModel", back_populates="analysis_requirement")

# --------------------------------------------------------------------------- #

class AnalysisResultModel(Base):
    __tablename__ = 'analysis_result'

    id = Column(Integer, primary_key=True, autoincrement=True)
    req_id = Column(Integer, ForeignKey('analysis_requirement.id'), nullable=False)
    content_id = Column(Integer, ForeignKey('content.id'), nullable=False)
    analysis_time = Column(DateTime, default=datetime.utcnow)
    output = Column(Text)

    analysis_requirement = relationship("AnalysisRequirementModel", back_populates="analysis_results")
    content = relationship("ContentModel", back_populates="analysis_results")

# --------------------------------------------------------------------------- #
