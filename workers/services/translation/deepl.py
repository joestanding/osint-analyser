#!/usr/bin/env python3

# Core
import logging
import os
import json
# Project
from translation_service import TranslationService

class DeepLTranslate(TranslationService):
    def __init__(self):
        super().__init__('deepl')


    def translate(self, text: str):
        logging.info("DeepLTranslate() received translation request")

        # Check existence of DeepL API key and retrieve it
        api_key = os.environ.get('DEEPL_API_KEY')
        if not api_key:
            logging.error("No DeepL API key has been set as an env. var!")
            return None

        return None


TranslationService.register('deepl', DeepLTranslate)
