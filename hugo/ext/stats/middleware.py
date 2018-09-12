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

from typing import Callable

import discord
import pendulum

import hugo
from hugo.core.context import Context
from hugo.core.middleware import Middleware, MiddlewareState

from hugo.ext.stats.state import State


class Connect(Middleware):
    """Middleware for handling bot connections."""

    async def run(self, *_, ctx: Context, next: Callable, **kw):  # noqa: D102
        # State should be always present. It could be None only if middleware
        # tree is incorrectly built.
        state: State = MiddlewareState.get_state(ctx, State)

        if not state.initialized:
            state.initialized = True
            state.first_connect_time = pendulum.now(tz=pendulum.UTC)
        else:
            state.last_connect_time = pendulum.now(tz=pendulum.UTC)


class Message(Middleware):
    """Middleware for handling status requests."""

    @staticmethod
    async def set_author(embed: discord.Embed, client: discord.Client):
        """Set author to the embed.

        It could be an Discord Application, if Discord User info about bot is
        missing.
        """
        if client.user is None:
            app = await client.application_info()
            embed.set_author(name=app.name, icon_url=app.icon_url)
        else:
            bot = client.user
            embed.set_author(name=bot.name, icon_url=bot.avatar_url)
        #
        if client.shard_id is not None:
            embed.author.name += (
                f" (shard {client.shard_id} of {client.shard_count})"
            )

    @staticmethod
    def set_description(embed: discord.Embed):
        """Set description (libraries version) to the embed."""
        embed.description = "\n".join(
            [
                f"Hugo library v.{hugo.__version__}",
                f"Discord.py library v.{discord.__version__}",
            ]
        )

    @staticmethod
    async def set_counters(embed: discord.Embed, client: discord.Client):
        """Set counters where bot is used to the embed."""
        guilds = 0
        vip = 0
        verified = 0
        large = 0
        unavailable = 0
        members = 0
        online = 0
        text = 0
        voice = 0

        for guild in client.guilds:
            guilds += 1

            if guild.unavailable:
                unavailable += 1
                continue
            for feature in guild.features:
                if feature == "VIP_REGIONS":
                    vip += 1
                elif feature == "VERIFIED":
                    verified += 1
            #
            if guild.large:
                large += 1

                members_count = len(guild.members)
                members += members_count
                online += members_count
            else:
                for member in guild.members:
                    members += 1
                    if member.status is not discord.Status.offline:
                        online += 1
            #
            text += len(guild.text_channels)
            voice += len(guild.voice_channels)
        #
        # fmt: off
        embed.add_field(name="Guilds", value="\n".join([
            f"{guilds} total", f"{vip} vip", f"{verified} verified",
            f"{large} large", f"{unavailable} unavailable"
        ]))

        embed.add_field(name="Members", value="\n".join([
            f"{members} total", f"{online} online"
        ]))

        embed.add_field(name="Channels", value="\n".join([
            f"{text + voice} total", f"{text} text", f"{voice} voice"
        ]))
        # fmt: on

    @staticmethod
    def set_uptime(embed: discord.Embed, state: State):
        """Set uptime info to the embed."""
        uptime = (
            pendulum.now(tz=pendulum.UTC) - state.first_connect_time
        ).in_words()
        started = state.first_connect_time.to_day_datetime_string()

        values = [f"Uptime for {uptime}", f"Started on {started}"]
        if state.last_connect_time is not None:
            reconnected = state.last_connect_time.to_day_datetime_string()
            values.append(f"Last reconnection on {reconnected}")
        #
        embed.add_field(
            name="Uptime info", inline=False, value="\n".join(values)
        )

    async def run(self, *_, ctx: Context, next: Callable, **kw):  # noqa: D102
        # State should be always present. It could be None only if middleware
        # tree is incorrectly built.
        client = ctx.client
        state: State = MiddlewareState.get_state(ctx, State)
        embed = discord.Embed()

        await self.set_author(embed, client)
        self.set_description(embed)
        await self.set_counters(embed, client)
        self.set_uptime(embed, state)

        embed.timestamp = pendulum.now(tz=pendulum.UTC)
        await ctx.kwargs["message"].channel.send(embed=embed)
