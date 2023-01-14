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

import hikari as h
import lightbulb as lb

from .. import cfg, utils


async def get_basic_weekly_reset_embed():
    return h.Embed(
        title="Weekly Reset",
        url=await utils.follow_link_single_step("https://kyberscorner.com/"),
        color=cfg.kyber_pink,
    ).set_image("https://kyber3000.com/Reset")


@lb.command("reset", "Find out about this weeks reset")
@lb.implements(lb.SlashCommand)
async def weekly_reset_command(ctx: lb.Context):
    await ctx.respond(await get_basic_weekly_reset_embed())


def register(bot):
    for command in [
        weekly_reset_command,
    ]:
        bot.command(command)