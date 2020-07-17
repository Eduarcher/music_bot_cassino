import discord
from discord.ext import commands
from config import Config
import logging


logging.basicConfig(level=logging.INFO)
cfg = Config()


def get_prefix(target_bot, msg):
    """A callable Prefix for our bot. This could be edited to allow per server prefixes."""
    prefixes = [cfg.params['prefix']]
    return commands.when_mentioned_or(*prefixes)(target_bot, msg)


bot = commands.Bot(command_prefix=get_prefix, description='Multipurpose Discord Bot')
exts = cfg.params['extensions']


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.streaming, name='Cassino Águias  | !help'))
    print(bot.user.name, 'loaded')


@commands.is_owner()
@bot.command(name='eval', hidden=True)
async def _eval(msg, *, cmd):
    await msg.send(eval(cmd))

for i in exts:
    bot.load_extension(i)

logging.getLogger('main').info('Starting Bot')
bot.run(cfg.params['token'])
