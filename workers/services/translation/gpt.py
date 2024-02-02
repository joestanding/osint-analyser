# Core
import logging
import os
import json
# Project
from translation_service import TranslationService
from gpt_api import GPT, GPT3Turbo_16K

# =========================================================================== #

class GPTTranslate(TranslationService):
    def __init__(self):
        super().__init__('gpt3.5')

    # ----------------------------------------------------------------------- #

    def translate(self, text: str):
        logging.info("GPTTranslate() received translation request")

        # Check existence of OpenAI API key and retrieve it
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            logging.error("No OpenAI API key has been set as an env. var!")
            return None

        # Initialise GPT client
        gpt = GPT(api_key, GPT3Turbo_16K())

        # Load the translate template as the system prompt
        template = gpt.load_template('data/llm_templates/translate.txt')
        gpt.add_prompt(template)

        # Add our translation request
        gpt.add_prompt(json.dumps({ 'translate_to': 'English', 'message': text }))

        # Send off our GPT request
        response = gpt.execute()
        if response is None:
            logging.error("GPT query failed!")
            return None

        # Convert the response to a dict
        response_json = json.loads(response['response'])
        logging.debug(f"JSON response: {response_json}")

        # Parse the response
        logging.info(f"Translation complete, cost: ${response['cost']}")
        logging.info(f"Raw translation JSON: {response['response']}")

        # Return only the translation and none of the metadata
        data = json.loads(response['response'])
        return data['translation']

# =========================================================================== #

TranslationService.register('gpt3.5', GPTTranslate)
