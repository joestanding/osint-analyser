#!/usr/bin/env python3

# Core
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
import logging
import os
# Third-party
from dotenv import load_dotenv
# Project
from database import Database
from models import CollectorModel, SourceModel, ContentModel

# =========================================================================== #

class CollectionException(Exception):
    pass

# =========================================================================== #

class Collector(ABC):
    def __init__(self, short_name: str, long_name: str):
        """
        Initialise the database connection and any other services so the
        collector can store what it finds.

        Returns:
            None
        """
        self.short_name = short_name
        self.long_name  = long_name
        self._connect_db()
        self._register_collector()
        self._get_collector_id()

    # ----------------------------------------------------------------------- #

    def _connect_db(self) -> bool:
        """
        Establishes a connection to the database using environment variables.

        Returns:
            bool: True if the database connection was successful, False
            otherwise.
        """
        self.database = Database()
        username = os.environ.get('MYSQL_USER')
        password = os.environ.get('MYSQL_PASSWORD')
        db_name  = os.environ.get('MYSQL_DATABASE')

        if not username or \
           not password or \
           not db_name:
            logging.error("Database connection parameters are missing!")
            return False

        if not self.database.connect(username, password, db_name):
            logging.error("Failed to connect to database!")
            return False

        logging.debug("Connected to database!")
        return True

    # ----------------------------------------------------------------------- #

    def _register_collector(self) -> None:
        """
        Registers the collector in the database if it's not already registered.

        This method checks for an existing collector entry in the database.
        If not found, it creates a new entry. The collector is identified by
        its 'short_name'.

        Returns:
            None
        """
        with self.database.session_scope() as session:

            existing_collector = session.query(CollectorModel) \
                .filter_by(short_name=self.short_name) \
                .first()

            if existing_collector is None:
                logging.info("No existing collector registration found!")
                new_collector = CollectorModel(short_name=self.short_name,
                        long_name=self.long_name,
                        enabled=True)
                session.add(new_collector)
                session.commit()
            else:
                logging.info("Existing collector registration found!")

    # ----------------------------------------------------------------------- #

    def _get_collector_id(self) -> None:
        """
        Retrieves and sets the collector ID from the database.

        This method queries the database for the collector's ID based on its
        'short_name'. If found, the ID is stored in the instance variable
        'collector_id'. If not found, 'collector_id' is set to None and an
        error is logged.

        Returns:
            None
        """
        with self.database.session_scope() as session:
            collector = session.query(CollectorModel) \
                        .filter_by(short_name=self.short_name) \
                        .first()
            if collector:
                self.collector_id = collector.id
                logging.info(f"Collector ID for '{self.short_name}' is " \
                        f"{self.collector_id}.")
            else:
                logging.error(f"Collector '{self.short_name}' not found in the database.")
                self.collector_id = None

    # ----------------------------------------------------------------------- #

    def add_source(self, uid: str, friendly_name: str) -> Optional[SourceModel]:
        """
        Adds a new source to the database if it doesn't already exist.

        This method checks if a source with the given UID already exists for
        the collector. If it does not exist, it creates a new SourceModel
        instance and adds it to the database. If the source already exists, it
        does nothing.

        Args:
            uid (str): The unique identifier of the source.
            friendly_name (str): A user-friendly name for the source.

        Returns:
            Optional[SourceModel]: The newly created SourceModel instance if a
            new source was added, None if the source already exists.
        """
        with self.database.session_scope() as session:
            # Check if the source already exists
            existing_source = session.query(SourceModel) \
                .filter_by(uid=uid, collector_id=self.collector_id) \
                .first()

            if existing_source is None:
                # Add the new source
                logging.info(f"Adding new source: {uid}")
                new_source = SourceModel(uid=uid,
                        friendly_name=friendly_name,
                        collector_id=self.collector_id,
                        enabled=True)
                session.add(new_source)
                session.commit()
                logging.info(f"New source inserted with ID {new_source.id}")
                return new_source
            else:
                # Source already exists
                logging.info(f"Source '{uid}' already exists for collector " \
                    f"'{self.short_name}'.")
        return None

    # ----------------------------------------------------------------------- #

    def add_content(self, source_uid: str, origin_time: datetime, text: str, metadata: dict):
        """
        Adds new content to the database associated with a specific source.

        Args:
            source_uid (str): The unique identifier of the source to which the
                content belongs.
            origin_time (datetime): The original time when the content was
                created or posted.
            text (str): The actual text content.
            metadata (dict): A dictionary containing additional metadata about
                the content.

        Returns:
            Optional[int]: The ID of the newly created content record if
                successful, None otherwise.
        """
        with self.database.session_scope() as session:
            source = session.query(SourceModel) \
                .filter_by(uid=source_uid, collector_id=self.collector_id) \
                .first()

            if source is None:
                logging.warning(f"Source with UID {source_uid} not found.")
                return None

            new_content = ContentModel(source_id=source.id,
                    original_text=text,
                    origin_time=origin_time,
                    metadata=metadata)
            session.add(new_content)
            session.commit()
            logging.info(f"New content added for source {source_uid}.")
            return int(new_content.id)

    # ----------------------------------------------------------------------- #

    def get_source(self, uid: str):
        """
        Retrieves a source by its uid for the current collector.
        :param uid: The uid of the source to retrieve.
        :return: The SourceModel object if found, otherwise None.
        """
        with self.database.session_scope() as session:
            source = session.query(SourceModel)\
                .filter_by(uid=uid, collector_id=self.collector_id)\
                .first()
            return source
        return None

    # ----------------------------------------------------------------------- #

    @abstractmethod
    def connect(self):
        """
        Used by collectors that require connection to an external service,
        such as Telegram which requires a maintained connection to Telegram
        servers.
        """
        pass

    # ----------------------------------------------------------------------- #

    @abstractmethod
    def disconnect(self):
        """
        Used by collectors that require disconnection logic from an external
        service.
        """
        pass

    # ----------------------------------------------------------------------- #

    @abstractmethod
    def main(self):
        """
        The main logic loop for the collector. As an example, a Telegram
        collector may wait for new messages to be pushed from the server,
        then process them within this loop.
        """
        pass

# =========================================================================== #
