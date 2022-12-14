# Define our custom discord bot classes
# This is the base h.CachedFetchBot but with added utility functions

import hikari as h


class CachedFetchBot(h.GatewayBot):
    """lb.BotApp subclass with async methods that fetch objects from cache if possible"""

    async def fetch_channel(self, channel_id: int):
        """This method fetches a channel from the cache or from discord if not cached"""
        return self.cache.get_guild_channel(
            channel_id
        ) or await self.rest.fetch_channel(channel_id)

    async def fetch_guild(self, guild_id: int):
        """This method fetches a guild from the cache or from discord if not cached"""
        return self.cache.get_guild(guild_id) or await self.rest.fetch_guild(guild_id)

    async def fetch_message(
        self, channel: h.SnowflakeishOr[h.TextableChannel], message_id: int
    ):
        """This method fetches a message from the cache or from discord if not cached

        channel can be the channels id or the channel object itself"""
        if isinstance(channel, h.Snowflake) or isinstance(channel, int):
            # If a channel id is specified then get the channel for that id
            # I am not sure if the int check is necessary since Snowflakes
            # are subcalsses of int but want to test this later and remove
            # it only after double checking. Most likely can remove, and I'm
            # just being paranoid
            channel = await self.fetch_channel(channel)

        return self.cache.get_message(message_id) or await self.rest.fetch_message(
            channel, message_id
        )

    async def fetch_emoji(self, guild_id, emoji_id):
        """This method fetches an emoji from the cache or from discord if not cached"""
        # TODO allow passing a guild (not id) to this method as well for convenience
        return self.cache.get_emoji(emoji_id) or await self.rest.fetch_emoji(
            guild_id, emoji_id
        )

    async def fetch_user(self, user: int):
        """This method fetches a user from the cache or from discord if not cached"""
        return self.cache.get_user(user) or await self.rest.fetch_user(user)
