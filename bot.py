import discord, asyncio, youtube_dl, os
from discord.ext import commands


def get_prefix(bot, msg):
    """A callable Prefix for our bot. This could be edited to allow per server prefixes."""
    prefixes = ['k.', 'k!', 's.']
    return commands.when_mentioned_or(*prefixes)(bot, msg)


bot = commands.Bot(command_prefix=get_prefix, description='Multipurpose Discord Bot')
exts = ['music']


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name='TWICE LIKEY'))
    print(bot.user.name)


@commands.is_owner()
@bot.command(name='eval', hidden=True)
async def _eval(msg, *, cmd):
    await msg.send(eval(cmd))

for i in exts:
    bot.load_extension(i)

bot.run('NzI2MTM5NTMwNzQ2Mzk2Njky.XwKS-A.5ioZuPA6L6YuF19f7QwNCVMkuGM')
