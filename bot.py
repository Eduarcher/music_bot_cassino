import discord, asyncio, youtube_dl, os
from discord.ext import commands
import config

cfg = config.load_config()


def get_prefix(bot, msg):
    """A callable Prefix for our bot. This could be edited to allow per server prefixes."""
    prefixes = [cfg['prefix']]
    return commands.when_mentioned_or(*prefixes)(bot, msg)


bot = commands.Bot(command_prefix=get_prefix, description='Multipurpose Discord Bot')
exts = cfg['extensions']


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name='Cassino Águias'))
    print(bot.user.name, 'loaded')


@commands.is_owner()
@bot.command(name='eval', hidden=True)
async def _eval(msg, *, cmd):
    await msg.send(eval(cmd))

for i in exts:
    bot.load_extension(i)

bot.run(cfg['token'])
