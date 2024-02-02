#!/usr/bin/env python3

# Core
import os
import logging
# Third-party
from telethon import TelegramClient, events
import telethon
import requests
from celery import Celery
# Project
from collector import Collector, CollectionException

app = Celery(broker='amqp://localhost', backend='rpc://')

class TelegramCollector(Collector):
    def __init__(self):
        super().__init__('telegram', 'Telegram Channel Monitor')
        self.api_id   = None
        self.api_hash = None
        self.client   = None

    # ----------------------------------------------------------------------- #

    def connect(self):
        """
        Establishes a connection to the Telegram API.

        This method initializes the Telegram client with the API ID and hash
        retrieved from environment variables. It also sets up a handler for
        new messages. If the API ID or hash is missing, it raises an exception.

        Raises:
            CollectionException: If the API ID or API hash are not found
                in the environment variables.
        """
        self.api_id   = os.environ.get('TELEGRAM_API_ID')
        self.api_hash = os.environ.get('TELEGRAM_API_HASH')
        if not self.api_id or not self.api_hash:
            raise CollectionException("API ID or API hash were empty or missing!")

        self.client = TelegramClient('data/anon', self.api_id, self.api_hash)
        self.client.on(events.NewMessage)(self.process_message)

    # ----------------------------------------------------------------------- #

    def disconnect(self):
        """
        Disconnects the Telegram client.
        """
        if self.client:
            self.client.disconnect()

    # ----------------------------------------------------------------------- #

    def main(self):
        """
        Initialises the Telegram client and starts the main event loop.

        Raises:
            CollectionException: If an error is encountered when initialising
                the Telethon client.
        """
        logging.info("Connecting to Telegram..")
        try:
            self.client.start()
        except telethon.errors.TelethonError as err:
            raise CollectionException(f"Telethon specific error occurred: {err}") \
                    from err
        except requests.exceptions.ConnectionError as err:
            raise CollectionException(f"Network connection error occurred: {err}") \
                    from err
        except Exception as err:
            raise CollectionException(f"Unexpected error occurred: {err}") \
                    from err
        logging.info("Connected successfully!")

        # Run initialisation code, retrieving chats etc.
        self.client.loop.run_until_complete(self.telegram_init())
        # After initialisation is done, now just process incoming events
        logging.info("Entering main Telegram event loop..")
        self.client.run_until_disconnected()

    # ----------------------------------------------------------------------- #

    async def telegram_init(self):
        """
        Enumerates subscribed channels and other initialisation tasks.

        Raises:
            CollectionException: If there's an error adding a new source to
                the database.
        """
        logging.info("Running Telegram initialisation..")
        async for dialog in self.client.iter_dialogs():
            if isinstance(dialog.entity, telethon.tl.types.Channel):
                logging.info(f"Channel ID: {dialog.entity.id}, Name: {dialog.entity.title}")
                # TODO: Handle whatever error type we decide this returns
                self.add_source(str(dialog.entity.id),
                        str(dialog.entity.title))

    # ----------------------------------------------------------------------- #

    async def process_message(self, event: telethon.events.NewMessage.Event):
        """
        Asynchronously processes new Telegram messages as they come in.

        Args:
            event (telethon.events.NewMessage.Event): The event object
                representing the incoming message.

        Raises:
            CollectionException: If any occurs during processing of the event,
                such as saving new content or issuing a translation task.
        """
        logging.info("----- New Message -----")
        sender = await event.get_sender()

        # Handle messages from Users
        if isinstance(sender, telethon.tl.types.User):
            logging.info(f"Username: {sender.username}")

        # Handle messages from Channels
        if isinstance(sender, telethon.tl.types.Channel):
            logging.info(f"Channel title: {sender.title}")

        # Check whether this message includes media
        if event.photo:
            logging.info(f"Attachment: Photo")

        # Store this message in the database
        if event.message is not None and event.message.message is not None:
            # On occasion, messages can have zero text, only insert
            # if there's text
            if len(event.message.message):
                content_id = self.add_content(str(sender.id),
                        event.message.date,
                        event.message.message,
                        {})

                if content_id:
                    app.send_task('translate_content', args=[content_id], queue="translation")
                else:
                    logging.info("Not translating message as no source found")

        logging.info("-----------------------")
        logging.info("")

    # ----------------------------------------------------------------------- #
