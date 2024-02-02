# Core
import logging
import os
import json
# Project
from analysis_service import AnalysisService, AnalysisException
from gpt_api import GPT, GPT3Turbo_16K
from openai import APIConnectionError, RateLimitError, APIStatusError

# =========================================================================== #

class APICredentialsMissing(Exception):
    pass

# =========================================================================== #

class GPTAnalyse(AnalysisService):
    def __init__(self):
        super().__init__('gpt3.5')

    # ----------------------------------------------------------------------- #

    def analyse(self, prompt: str, content_text: str) -> dict:
        """
        Analyse a given piece of text, using the analysis prompt provided.

        Args:
            prompt (str): The prompt to be passed to the LLM.
            content_text (str): The text to be analysed using the prompt.

        Returns:
            dict: A dictionary containing the analysis results.

        Raises:
            ValueError: If the prompt or content_text is not a valid string.
            APICredentialsMissing: If the OpenAI API key is missing.
            AnalysisException: For errors related to file handling, API
                connection, response parsing, and other unforeseen issues.
        """
        logging.info("GPTAnalyse() received analysis request")

        # Validate the information we've been provided
        if not prompt or not isinstance(prompt, str):
            raise ValueError("Prompt must be a non-empty string")
        if not content_text or not isinstance(content_text, str):
            raise ValueError("Content text must be a non-empty string")

        # Check existence of OpenAI API key and retrieve it
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise APICredentialsMissing("No OpenAI API key has been set as " \
                    "an env. var!")

        # Initialise GPT client
        gpt = GPT(api_key, GPT3Turbo_16K())

        # Load the translate template as the system prompt
        try:
            template = gpt.load_template('data/llm_templates/analyse.txt')
        except FileNotFoundError as err:
            raise AnalysisException(f"Template file not found: {err}") from err
        except PermissionError as err:
            raise AnalysisException(f"Permissions error loading template: " \
                    f"{err}") from err
        except OSError as err:
            raise AnalysisException(f"General OS error loading template: " \
                    f"{err}") from err

        # Load our template
        gpt.add_prompt(template)

        # Add our translation request
        gpt.add_prompt(json.dumps(
            { 'requirement': prompt, 'text': content_text }
        ))

        # Send off our GPT request
        # We'll handle specific exceptions raised by the OpenAI library, as
        # certain exceptions like rate limiting require us to do something
        # different. If all else fails however, we'll pass a generic
        # AnalysisException to the Celery task, as it doesn't need the specifics.
        try:
            response = gpt.execute()
        except APIConnectionError as err:
            raise AnalysisException(f"OpenAI API connection error: {err}") \
                    from err
        except RateLimitError as err:
            raise AnalysisException(f"OpenAI API rate limit error: {err}") \
                    from err
        except APIStatusError as err:
            raise AnalysisException(f"OpenAI API status error (not 200 OK): " \
                    f"{err}") from err

        # Attempt to parse GPT's response as JSON - regardless of the analysis
        # requirement, GPT is asked to provide its response in a pre-defined
        # JSON format, so that we can always consistently parse it, and potentially
        # ask for metadata in addition to the analysis itself in future. A JSON
        # response format lets us isolate the two.
        try:
            response_json = json.loads(response['response'])
        except json.JSONDecodeError as err:
            logging.error(f"GPT raw response: {response['response']}")
            raise AnalysisException(f"GPT did not respond with valid JSON? " \
                    f"Unable to parse: {err}") from err

        # A success, hopefully! How much did it cost us?
        logging.info(f"Translation complete, cost: ${response['cost']}")

        return response_json.get('analysis', {})

# =========================================================================== #

AnalysisService.register('gpt3.5', GPTAnalyse)
