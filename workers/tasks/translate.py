#!/usr/bin/env python3

# Core
import logging
logger = logging.getLogger(__name__)
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
from translation_service import TranslationService

app = Celery('translate', broker='amqp://localhost', backend='rpc://')

# --------------------------------------------------------------------------- #

def load_translation_services() -> None:
    base_path = 'services/translation'
    for filename in os.listdir(base_path):
        if filename.endswith('.py') and \
           filename != '__init__.py' and \
           filename != '__pycache__':
            module_name = filename[:-3]
            importlib.import_module(f"services.translation.{module_name}")

# --------------------------------------------------------------------------- #

@shared_task(name='translate_content')
def translate_content(content_id: int) -> bool:
    logging.info("---------------------------------------------------------")
    logging.info("TRANSLATION REQUEST")
    logging.info(f"Content ID: {content_id}")

    try:
        # Connect to the DB so we can retrieve the original text to translate
        database = Database()
        connect_db(database)

        # Retrieve the original text from the database record
        original_text = database.get_content_attribute(content_id,
                'original_text')
        logging.info(f"Original: '{original_text[:80]}..'")

        # Load the possible translation services
        try:
            load_translation_services()
        except Exception as err:
            logging.error(f"Failed to load translation services! Error: {err}")
            database.disconnect()
            raise

        # Invoke the appropriate translation service for this content
        service = TranslationService.get_service('gpt3.5')()
        start_time = time.time()
        translated_text = service.translate(original_text)
        end_time = time.time()
        time_taken = round(end_time - start_time, 1)  # Round to 1 decimal place
        logging.info(f"Time taken for translation: {time_taken} seconds")

        if translated_text:
            logging.info(f"Successfully translated content ID {content_id}!")
        else:
            logging.error("Failed to translate text!")
            return False

        logging.info(f"Translated: '{translated_text[:80]}..'")

        # Update the database record with the translated text
        database.set_content_attribute(content_id, 'translated_text',
                translated_text)

        # Finally, issue an analysis task request for the translated content
        app.send_task('analyse_content', args=[content_id], queue="analysis")

    except Exception as err:
        logging.error("Exception encountered when translating content!")
        # Re-raise the exception to Celery, which can handle/record it
        raise

    logging.info("---------------------------------------------------------")
    logging.info("")

    return True

# --------------------------------------------------------------------------- #
