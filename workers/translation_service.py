#!/usr/bin/env python3

# Core
from abc import ABC, abstractmethod
import logging

# =========================================================================== #

class TranslationException(Exception):
    pass

# =========================================================================== #

class TranslationService(ABC):

    _registry = {}

    # ----------------------------------------------------------------------- #

    def __init__(self, uid: str):
        self.uid = uid

    # ----------------------------------------------------------------------- #

    @classmethod
    def register(cls, uid, service_cls):
        cls._registry[uid] = service_cls

    # ----------------------------------------------------------------------- #

    @classmethod
    def get_service(cls, uid):
        return cls._registry.get(uid)

    # ----------------------------------------------------------------------- #

    @abstractmethod
    def translate(self, prompt, content_text):
        pass

# =========================================================================== #
