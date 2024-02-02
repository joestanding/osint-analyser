#!/usr/bin/env python3

# Core
import logging
import json
import os
import importlib
import time
# Third-party
from celery import Celery, shared_task
# Project
from database import Database, connect_db
from gpt_api import *
from models import ContentModel
from analysis_service import AnalysisService, AnalysisException

app = Celery('analyse', broker='amqp://localhost', backend='rpc://')

# --------------------------------------------------------------------------- #

def load_analysis_services() -> None:
    """
    Iterate through the analysis service directory and dynamically load any
    valid Python modules. They will automatically register themselves upon
    dynamic import.

    Returns:
        None
    """
    base_path = 'services/analysis'
    for filename in os.listdir(base_path):
        if filename.endswith('.py') and \
           filename != '__init__.py' and \
           filename != '__pycache__':
            module_name = filename[:-3]
            importlib.import_module(f"services.analysis.{module_name}")

# --------------------------------------------------------------------------- #

@shared_task(name='analyse_content')
def analyse_content(content_id: int) -> bool:
    """
    Conduct analysis of a single Content entry using the respective analysis
    service assigned to it by the respective Analysis Requirement.

    Args:
        content_id: Unique identifier for the Content entry in the database.

    Returns:
        bool: True on success, False on non-exception failure.
    """
    logging.info("---------------------------------------------------------")
    logging.info("ANALYSIS REQUEST")
    logging.info(f"Content ID: {content_id}")

    # Connect to the DB so we can retrieve the original text to analyse
    database = Database()
    try:
        connect_db(database)
    except database.DatabaseConnectionError as err:
        logging.error(f"Analysis worker failed to connect to database! {err}")
        raise

    # Load the possible analysis services
    try:
        load_analysis_services()
    except Exception as err:
        logging.error(f"Failed to load analysis services! Exception: {err}")
        database.disconnect()
        raise

    # Retrieve the translated text to analyse
    translated_text = database.get_content_attribute(content_id,
            'translated_text')

    # Retrieve the source ID for the given content
    source_id = database.get_content_attribute(content_id, 'source_id')
    logging.info(f"Source ID: {source_id}")

    # Check whether analysis of content from this source is enabled
    source_enabled = database.get_source_attribute(source_id, 'enabled')
    if not source_enabled:
        logging.info(f"Analysis is not enabled for this source, terminating!")
        return None

    # Retrieve the analysis requirements for this source
    requirements = database.get_analysis_requirements(source_id)
    logging.info(f"Retrieved {len(requirements)} analysis requirements..")

    # Iterate through each requirement, and process it
    for requirement in requirements:
        logging.info(f"Processing requirement '{requirement['name']}'..")
        logging.info(f"    LLM ID: {requirement['llm_id']}")

        service_id = 'gpt3.5'

        # Retrieve the analysis service assigned to this requirement
        service = AnalysisService.get_service(service_id)
        if not service:
            logging.error(f"Failed to find analysis service {service_id}!")
            # TODO: Review return value for task failure
            return False
        service = service()

        # Attempt to execute the analysis - if anything fails, we'll re-raise
        # the exception so Celery can record it
        try:
            analysis = service.analyse(requirement['prompt'], translated_text)
        except ValueError as err:
            logging.error(f"The analysis service reported an error with the " \
                    f"provided arguments: {err}")
            raise
        except AnalysisException as err:
            logging.error(f"The analysis service encountered an " \
                    f"irrecoverable error: {err}")
            raise

        logging.info(f"Analysis: '{analysis[:80]}..'")

        new_id = database.save_analysis_result(content_id,
                requirement['req_id'], analysis)
        logging.info(f"Stored analysis result with ID {new_id}")

    logging.info("---------------------------------------------------------")
    logging.info("")

    return True

# --------------------------------------------------------------------------- #
