import hikari as h

from . import cfg
from .bot import CachedFetchBot
from .modules import repeater

bot = CachedFetchBot(
    token=cfg.discord_token,
    intents=(h.Intents.ALL_UNPRIVILEGED | h.Intents.MESSAGE_CONTENT),
)

for module in [
    repeater,
]:
    module.register(bot)

bot.run()
