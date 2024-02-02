#!/usr/bin/env python3

from telegram import TelegramCollector

tc = TelegramCollector()
tc.connect()
tc.main()
tc.disconnect()
