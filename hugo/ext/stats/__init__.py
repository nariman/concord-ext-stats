"""
The MIT License (MIT)

Copyright (c) 2017-2018 Nariman Safiulin

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import re

import discord
import pendulum

import hugo
from hugo.core.constants import EventType
from hugo.core.context import Context
from hugo.core.handler import event, not_authored_by_bot, pattern
from hugo.core.middleware import (
    MiddlewareState,
    OneOfAll,
    collection_of,
    chain_of,
)


__version__ = "1.0.2"


class State:
    """Class for uptime information about a bot."""

    def __init__(self):
        self.initialized = False
        self.start_time = None


@event(EventType.READY)
async def on_ready(*args, ctx: Context, next, state: State, **kwargs):
    """Save start time information."""
    if not state.initialized:
        state.initialized = True
        state.start_time = pendulum.now(tz=pendulum.UTC)


@event(EventType.MESSAGE)
@not_authored_by_bot()
@pattern(re.compile(r"status", re.I))
async def on_message(*args, ctx: Context, next, state: State, **kwargs):
    """Display information about bot uptime and stats."""
    embed = discord.Embed()

    if ctx.client.user is None:
        app = await ctx.client.application_info()
        embed.set_author(name=app.name, icon_url=app.icon_url)
    else:
        bot = ctx.client.user
        embed.set_author(name=bot.name, icon_url=bot.avatar_url)
    #
    if ctx.client.shard_id is not None:
        embed.title = f"Shard {ctx.client.shard_id} of {ctx.client.shard_count}"
    #
    embed.description = "\n".join(
        [
            f"Hugo library v.{hugo.__version__}",
            f"Discord.py library v.{discord.__version__}",
        ]
    )

    total_guilds = 0
    total_vip_guilds = 0
    total_verified_guilds = 0
    total_large_guilds = 0
    total_unavailable_guilds = 0
    total_members = 0
    total_online_members = 0
    total_text_channels = 0
    total_voice_channels = 0

    for guild in ctx.client.guilds:
        total_guilds += 1

        if guild.unavailable:
            total_unavailable_guilds += 1
            continue
        #
        for feature in guild.features:
            if feature == "VIP_REGIONS":
                total_vip_guilds += 1
            elif feature == "VERIFIED":
                total_verified_guilds += 1
        #
        if guild.large:
            total_large_guilds += 1

            members_count = len(guild.members)
            total_members += members_count
            total_online_members += members_count
        else:
            for member in guild.members:
                total_members += 1
                if member.status is not discord.Status.offline:
                    total_online_members += 1
        #
        total_text_channels += len(guild.text_channels)
        total_voice_channels += len(guild.voice_channels)
    #
    embed.add_field(
        name="Guilds",
        value="\n".join(
            [
                f"{total_guilds} total",
                f"{total_vip_guilds} vip",
                f"{total_verified_guilds} verified",
                f"{total_large_guilds} large",
                f"{total_unavailable_guilds} unavailable",
            ]
        ),
    )
    embed.add_field(
        name="Members",
        value="\n".join(
            [
                f"{total_members}+ total"
                if total_unavailable_guilds > 0 or total_large_guilds > 0
                else f"{total_members} total",
                f"{total_online_members}+ online"
                if total_unavailable_guilds > 0
                else f"{total_online_members} online",
            ]
        ),
    )
    embed.add_field(
        name="Channels",
        value="\n".join(
            [
                f"{total_text_channels + total_voice_channels}+ total",
                f"{total_text_channels}+ text",
                f"{total_voice_channels}+ voice",
            ]
            if total_unavailable_guilds > 0
            else [
                f"{total_text_channels + total_voice_channels} total",
                f"{total_text_channels} text",
                f"{total_voice_channels} voice",
            ]
        ),
    )

    uptime = (pendulum.now(tz=pendulum.UTC) - state.start_time).in_words()
    embed.set_footer(text=f"Uptime for {uptime}")

    await ctx.kwargs["message"].channel.send(embed=embed)


def get_root_middleware():
    """Return root middleware chain."""
    return chain_of(
        [
            collection_of(OneOfAll, [on_ready, on_message]),
            MiddlewareState(State()),
        ]
    )
