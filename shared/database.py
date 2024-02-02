#!/usr/bin/env python3

# Core
from contextlib import contextmanager
from urllib.parse import quote_plus
import os
import logging
# Third-party
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker
# Project
from models import Base, ContentModel, AnalysisResultModel, \
    AnalysisRequirementModel, SourceModel

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')

# =========================================================================== #


class DatabaseConnectionError(Exception):
    pass

class ContentNotFoundError(Exception):
    pass

# =========================================================================== #

class Database:
    def __init__(self):
        pass

    # ----------------------------------------------------------------------- #

    def connect(self, username, password, db_name):
        try:
            username = quote_plus(username)
            password = quote_plus(password)

            uri = f"mysql+mysqlconnector://{username}:{password}@database/" \
                    f"{db_name}"
            self.engine = create_engine(uri, echo=False)

            logging.debug("Connecting to SQL database..")
            self.engine.connect()
        except exc.SQLAlchemyError as err:
            logging.error(f"Failed to connect to SQL database! Error: {err}")
            return False
        except Exception as err:
            logging.error("Non-SQLAlchemy error encountered when connecting " \
                    f"to SQL database! Error: {err}")
            return False
        logging.debug("Connected to SQL database!")
        Base.metadata.create_all(self.engine)
        return True

    # ----------------------------------------------------------------------- #

    def disconnect(self) -> None:
        self.engine.disconnect()

    # ----------------------------------------------------------------------- #

    @contextmanager
    def session_scope(self):
        """
        Provide a transactional scope around a series of operations.
        """
        session = sessionmaker(bind=self.engine)()
        try:
            yield session
            session.commit()
        except Exception as err:
            logging.error(f"Exception occurred when committing session: {err}")
            session.rollback()
            raise
        finally:
            session.close()

    # ----------------------------------------------------------------------- #

    def get_content_attribute(self, content_id: int, attribute_name: str):
        with self.session_scope() as session:
            content = session.query(ContentModel) \
                      .filter_by(id=content_id) \
                      .first()
            if content is not None:
                return getattr(content, attribute_name, None)
            else:
                raise ContentNotFoundError("No content record found with " \
                        f"ID {content_id}")

    # ----------------------------------------------------------------------- #

    def set_content_attribute(self, content_id: int, attribute_name: str,
            new_value) -> None:
        with self.session_scope() as session:
            content = session.query(ContentModel) \
                      .filter_by(id=content_id) \
                      .first()
            if content is not None:
                if hasattr(content, attribute_name):
                    setattr(content, attribute_name, new_value)
                    session.commit()
                    logging.info(f"Updated {attribute_name} for content ID " \
                            f"{content_id}")
                else:
                    raise AttributeError("Content record has no attribute " \
                            f"'{attribute_name}'")
            else:
                raise ContentNotFoundError(f"No content record found with " \
                        f"ID {content_id}")

    # ----------------------------------------------------------------------- #

    def get_source_attribute(self, source_id: int, attribute_name: str):
        with self.session_scope() as session:
            source = session.query(SourceModel) \
                     .filter_by(id=source_id) \
                     .first()
            if source is not None:
                return getattr(source, attribute_name, None)
            else:
                raise ContentNotFoundError(f"No source record found with " \
                        f"ID {source_id}")

    # ----------------------------------------------------------------------- #

    def get_analysis_requirements(self, source_id: int):
        requirements = []
        with self.session_scope() as session:
            analysis_requirements = session.query(AnalysisRequirementModel) \
                    .filter(AnalysisRequirementModel.source_id == source_id) \
                    .all()

            for requirement in analysis_requirements:
                if requirement.enabled:
                    requirements.append({
                        'req_id': requirement.id,
                        'name': requirement.name,
                        'llm_id': requirement.llm_id,
                        'prompt': requirement.prompt
                    })

            return requirements

    # ----------------------------------------------------------------------- #

    def save_analysis_result(self, content_id: int, req_id: int, output: str):
        with self.session_scope() as session:
            new_analysis_result = AnalysisResultModel(
                req_id=req_id,
                content_id=content_id,
                output=output
            )
            session.add(new_analysis_result)
            session.commit()
            return int(new_analysis_result.id)

# =========================================================================== #

def connect_db(database: Database) -> bool:
    """
    Connect to the database using credentials stored in environment
    variables.
    """
    username = os.environ.get('MYSQL_USER')
    password = os.environ.get('MYSQL_PASSWORD')
    db_name  = os.environ.get('MYSQL_DATABASE')

    if not username or \
       not password or \
       not db_name:
        raise DatabaseConnectionError("Database connection params missing!")

    if not database.connect(username, password, db_name):
        raise DatabaseConnectionError("database.connect() failed!")

    logging.debug("Connected to database!")
    return True

# =========================================================================== #
