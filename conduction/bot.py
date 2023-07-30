# Copyright © 2019-present gsfernandes81

# This file is part of "conduction-tines".

# conduction-tines is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.

# "conduction-tines" is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License along with
# conduction-tines. If not, see <https://www.gnu.org/licenses/>.

# Define our custom discord bot classes
# This is the base h.CachedFetchBot but with added utility functions

import json
import typing as t

import hikari as h
import lightbulb as lb
import miru as m

from . import cfg, schemas, utils


class CachedFetchBot(lb.BotApp):
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

    async def fetch_owner(self):
        """This method fetches the primary owner of the bot from the cache or from
        discord if not cached"""
        return await self.fetch_user((await self.fetch_owner_ids())[-1])


class SchemaBackedCommand:
    """Base class for schema backed commands in a lightbulb bot

    Differentiates normally defined commands from schema based / user commands"""

    @staticmethod
    def impl_from_user_command(cmd: schemas.UserCommand):
        if cmd.is_command_group:
            # Command group impls
            if cmd.is_subcommand_or_subgroup:
                impl_type = SBSlashSubGroup
            else:
                impl_type = SBSlashCommandGroup
        else:
            # Command impls
            if cmd.is_subcommand_or_subgroup:
                impl_type = SBSlashSubCommand
            else:
                impl_type = SBSlashCommand

        return impl_type


class SBSlashCommand(SchemaBackedCommand, lb.SlashCommand):
    pass


class SBSlashSubCommand(SchemaBackedCommand, lb.SlashSubCommand):
    pass


class SBSlashCommandGroup(SchemaBackedCommand, lb.SlashCommandGroup):
    pass


class SBSlashSubGroup(SchemaBackedCommand, lb.SlashSubGroup):
    pass


class UserCommandBot(lb.BotApp):
    def __init__(
        self, *args, user_command_schema: t.Type[schemas.UserCommand], **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._user_command_schema = user_command_schema

        @self.listen()
        async def _on_start(event: h.StartingEvent):
            await self.sync_schema_to_bot_cmds()

    def is_existing_command(self, *ln_names) -> bool:
        """Check if a command is registered with a bot,

        Note: Does not differentiate between commands and command groups"""

        utils.check_number_of_layers(ln_names)

        # lb.BotApp._slash_commands is a dict of names to CommandLike instances
        commands_group = self._slash_commands

        for ln_name in ln_names:
            # Existing command will be None if no such command exists
            existing_command = commands_group.get(ln_name)
            if not existing_command:
                return False
            is_command_group = isinstance(existing_command, lb.SlashGroupMixin)
            # If existing_command is a command group then check if the next
            # ln_name exists in it in the next cycle
            # If it is not then make commands_group an empty dict
            # when we try and check if a command exists here in the next cycle
            # this will return false, and if no next cycle occurs because we checked
            # all ln_names already, this will return true
            commands_group = existing_command.subcommands if is_command_group else {}

        return True

    def get_command_group(self, *ln_names) -> lb.CommandLike:
        """Get an existing command group from the bot

        Note: Only supports a depth of 2 since the current discord limit is 3 layers
              of subcommands"""

        cmd_not_found_exc = ValueError(
            f"Command group {' -> '.join(ln_names)} was not found"
        )

        utils.check_number_of_layers(ln_names, max_layers=2)

        try:
            # Try to find the command group
            command_group: lb.Command = self._slash_commands[ln_names[0]]._initialiser
        except KeyError:
            raise cmd_not_found_exc

        if len(ln_names) > 1:
            # Try to find the subgroup if asked for
            try:
                command_group = [
                    subgroup
                    for subgroup in command_group.subcommands
                    if subgroup.name == ln_names[1]
                ][0]
            except IndexError:
                raise cmd_not_found_exc

        return command_group

    @utils.ensure_session(schemas.db_session)
    async def sync_schema_to_bot_cmds(
        self, session: t.Optional[schemas.AsyncSession] = None
    ):
        """Sync commands from schema in db to the bot"""

        # Remove all commands and command groups that are schema based
        # Currently only deletes layer 1 commands and groups
        for command in self.slash_commands:
            if isinstance(command, SchemaBackedCommand):
                self.remove_command(command)

        schema_commands = await self._user_command_schema.fetch_command_groups(
            session=session
        ) + await self._user_command_schema.fetch_commands(session=session)

        for cmd in schema_commands:
            if not self.is_existing_command(cmd.l1_name, cmd.l2_name, cmd.l3_name):
                self.command(cmd)

    async def sync_bot_cmds_to_discord(self):
        """Sync commands added to the bot to discord

        Effectively an alias of the sync_application_commands method"""
        await super().sync_application_commands()

    @utils.ensure_session(schemas.db_session)
    async def sync_application_commands(
        self, session: t.Optional[schemas.AsyncSession] = None
    ) -> None:
        await self.sync_schema_to_bot_cmds(session=session)
        await self.sync_bot_cmds_to_discord()

    def command(
        self, cmd: t.Optional[lb.CommandLike | schemas.UserCommand] = None
    ) -> t.Union[lb.CommandLike, t.Callable[[lb.CommandLike], lb.CommandLike],]:
        """Handle schema based commands and lightbulb commands

        Throws a utils.FriendlyValueError if a schema command is already defined"""

        if not isinstance(cmd, schemas.UserCommand):
            return super().command(cmd)

        if self.is_existing_command(*cmd.ln_names):
            if len(cmd.ln_names) > 1:
                cmd_group = self.get_command_group(*cmd.ln_names[:-1])
                for existing_cmd in cmd_group.subcommands:
                    if existing_cmd.name == cmd.ln_names[-1]:
                        cmd_group.subcommands.remove(existing_cmd)
            else:
                self.remove_command(self._slash_commands.get(cmd.l1_name))

        if cmd.is_subcommand_or_subgroup:
            register_command = self.get_command_group(*cmd.ln_names[:-1]).child
        else:
            register_command = super().command

        return register_command(self._user_command_response_func_builder(cmd))

    @staticmethod
    def _user_command_response_func_builder(
        cmd: schemas.UserCommand,
    ) -> t.Coroutine:
        # Create a decorator for the command
        decorator = lambda func: lb.command(cmd.ln_names[-1], cmd.description)(
            lb.implements(SchemaBackedCommand.impl_from_user_command(cmd))(func)
        )

        if cmd.response_type == 0:

            @decorator
            async def _responder(ctx: lb.Context):
                pass

        elif cmd.response_type == 1:

            @decorator
            async def _responder(ctx: lb.Context):
                text = cmd.response_data.strip()
                # Follow redirects once if any, then substitute these
                # url into the text and respond with it
                await ctx.respond(
                    cfg.url_regex.sub("{}", text).format(
                        *[
                            await utils.follow_link_single_step(link)
                            for link in cfg.url_regex.findall(text)
                        ]
                    ),
                    components=m.View().add_item(
                        m.Button(
                            style=h.ButtonStyle.LINK,
                            url=cfg.user_command_button_url,
                            label="See more on Kyber's Corner!",
                        )
                    ),
                )

        elif cmd.response_type == 2:

            @decorator
            async def _responder(ctx: lb.Context):
                msg_to_respond_with = await ctx.bot.rest.fetch_message(
                    *[int(id_) for id_ in cmd.response_data.split(":")]
                )
                await ctx.respond(
                    msg_to_respond_with.content,
                    embeds=msg_to_respond_with.embeds,
                    components=msg_to_respond_with.components,
                    attachments=msg_to_respond_with.attachments,
                )

        elif cmd.response_type == 3:
            embed_kwargs = json.decoder.JSONDecoder().decode(cmd.response_data)
            embed_kwargs["color"] = embed_kwargs.get("color") or cfg.embed_default_color

            @decorator
            async def _responder(ctx: lb.Context):
                try:
                    image = embed_kwargs.pop("image")
                except KeyError:
                    image = None

                embed = h.Embed(**embed_kwargs)

                if image:
                    image = await utils.follow_link_single_step(image)
                    embed.set_image(image)

                await ctx.respond(embed)

        return _responder
