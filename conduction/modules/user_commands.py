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

import logging
import hikari as h
import lightbulb as lb
import typing as t
import traceback as tb

from .. import cfg
from ..schemas import UserCommand
from ..bot import UserCommandBot

# TODO
# define a rename command


@lb.add_checks(lb.checks.has_roles(cfg.control_discord_role_id))
@lb.command(
    "command",
    "Custom command control",
    guilds=(cfg.control_discord_server_id,),
    inherit_checks=True,
)
@lb.implements(lb.SlashCommandGroup)
def command_group(ctx: lb.Context):
    pass


async def layer_name_autocomplete(
    option: h.AutocompleteInteractionOption, interaction: h.AutocompleteInteraction
) -> t.List[h.CommandOption] | None:
    name = option.name
    value = option.value
    # Get the list of all options provided
    other_options = interaction.options[0].options
    other_options = {
        other_option.name: other_option.value for other_option in other_options
    }

    l1_name = other_options.get("layer1")
    l2_name = other_options.get("layer2", "")
    l3_name = other_options.get("layer3", "")

    # If this is a layer name
    if name.startswith("layer"):
        try:
            depth = int(name[len("layer") :])
        except ValueError:
            # If the name is not layer followed by an int
            # do not autocomplete
            return

        # Get autocompletions from the db
        cmds = await UserCommand._autocomplete(l1_name, l2_name, l3_name)
        # Return names from the right layer depth
        options = [
            cmd.ln_names[depth - 1]
            for cmd in cmds
            if cmd.depth == depth and cmd.ln_names[depth - 1].startswith(value)
        ]
        return options


def layer_options(autocomplete: bool):
    """Decorator to add layer options to command with optional autocompletion"""

    def decorator_actual(func):
        return lb.option(
            "layer3",
            "1st layer commands and groups",
            autocomplete=autocomplete and layer_name_autocomplete,
            default="",
        )(
            lb.option(
                "layer2",
                "1st layer commands and groups",
                autocomplete=autocomplete and layer_name_autocomplete,
                default="",
            )(
                lb.option(
                    "layer1",
                    "1st layer commands and groups",
                    autocomplete=autocomplete and layer_name_autocomplete,
                )(func)
            )
        )

    return decorator_actual


def schema_options(type_needed, description_needed):
    """Decorator to add non layer schema options to commands"""

    def decorator_actual(func):
        choices = [
            h.CommandChoice(name="No Change", value=-1),
            h.CommandChoice(name="Text", value=1),
            h.CommandChoice(name="Message Copy", value=2),
            h.CommandChoice(name="Embed", value=3),
        ]
        if type_needed:
            choices = choices[1:]
            default = h.UNDEFINED
        else:
            default = choices[0]
        return lb.option("response", "Respond to the user with this data", default="")(
            lb.option(
                "type",
                "Type of response to show the user",
                choices=choices,
                default=default,
                type=int,
            )(
                lb.option(
                    "description",
                    "Description of the command",
                    default="",
                    required=description_needed,
                )(func)
            )
        )

    return decorator_actual


@command_group.child
@schema_options(type_needed=True, description_needed=True)
@layer_options(autocomplete=False)
@lb.command(
    "add", "Add a command", pass_options=True, auto_defer=True, inherit_checks=True
)
@lb.implements(lb.SlashSubCommand)
async def add_command(
    ctx: lb.Context,
    layer1: str,
    layer2: str,
    layer3: str,
    description: str,
    type: int,
    response: str,
):
    bot: UserCommandBot = ctx.bot
    type: int = int(type)

    await UserCommand.add_command(
        layer1,
        layer2,
        layer3,
        description=description,
        response_type=type,
        response_data=response,
    )
    await bot.sync_application_commands()


@command_group.child
@layer_options(autocomplete=True)
@lb.command(
    "delete",
    "Delete a command",
    pass_options=True,
    auto_defer=True,
    inherit_checks=True,
)
@lb.implements(lb.SlashSubCommand)
async def delete_command(ctx: lb.Context, layer1: str, layer2: str, layer3: str):
    bot: UserCommandBot = ctx.bot

    try:
        # Delete the command and sync
        deleted_command = await UserCommand.delete_command(layer1, layer2, layer3)
        await bot.sync_application_commands()
    except Exception as e:
        # If an exception occurs, respond with it as a message
        logging.error(e)
        await ctx.respond(
            "An error occured deleting the `{}` commmand.".format(
                " -> ".join(
                    [layer for layer in [layer1, layer2, layer3] if layer != ""]
                )
            )
            + "\n\n Error trace:\n```"
            + "\n".join(tb.format_exception(e))
            + "\n```"
        )
    else:
        # Otherwise confirm success
        await ctx.respond(f"Deleted the `{deleted_command}` command")


@command_group.child
@schema_options(type_needed=False, description_needed=False)
@layer_options(autocomplete=True)
@lb.command(
    "edit", "Edit a command", pass_options=True, auto_defer=True, inherit_checks=True
)
@lb.implements(lb.SlashSubCommand)
async def edit_command(
    ctx: lb.Context,
    layer1: str,
    layer2: str,
    layer3: str,
    description: str,
    type: int,
    response: str,
):
    bot: UserCommandBot = ctx.bot
    type: int = int(type)

    # Delete subject command from db
    deleted_command = await UserCommand.delete_command(layer1, layer2, layer3)

    # Update command parameters if specified
    ln_names = deleted_command.ln_names
    description = description if description else deleted_command.description
    type = type if type else deleted_command.response_type
    response = response if response else deleted_command.response_data

    # Add command back with new parameters
    await UserCommand.add_command(
        *ln_names,
        description=description,
        response_type=type,
        response_data=response,
    )

    # Resync with discord
    await bot.sync_application_commands()


def register(bot):
    for command in [
        command_group,
    ]:
        bot.command(command)
