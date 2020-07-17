import discord, asyncio, random, pymongo, youtube_dl, string, os, functools, json
from discord.ext import commands
from discord.ext.commands import command
import logging

# TODO: CREATE PLAYLIST SUPPORT FOR MUSIC


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '{}',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'logtostderr': False,
    "extractaudio": True,
    "audioformat": "opus",
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

stim = {
    'default_search': 'auto',
    "ignoreerrors": True,
    'quiet': True,
    "no_warnings": True,
    "simulate": True,  # do not keep the video files
    "nooverwrites": True,
    "keepvideo": False,
    "noplaylist": True,
    "skip_download": False,
    'source_address': '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}


class Downloader(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.6):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get("url")
        self.thumbnail = data.get('thumbnail')
        self.duration = data.get('duration')
        self.views = data.get('view_count')
        self.playlist = {}

    @classmethod
    async def video_url(cls, url, ytdl, *, loop=None, stream=False):
        logging.getLogger('music').info(f'video_url url={url}')
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        data1 = {'queue': []}
        if 'entries' in data:
            if len(data['entries']) > 1:
                playlist_titles = [title['title'] for title in data['entries']]
                data1 = {'title': data['title'], 'queue': playlist_titles}
                data1['queue'].pop(0)

            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data), data1

    async def get_info(self, url):
        logging.getLogger('music').info(f'get_info url={url}')
        yt = youtube_dl.YoutubeDL(stim)
        down = yt.extract_info(url, download=False)
        data1 = {'queue': []}
        if 'entries' in down:
            if len(down['entries']) > 1:
                playlist_titles = [title['title'] for title in down['entries']]
                data1 = {'title': down['title'], 'queue': playlist_titles}

            down = down['entries'][0]['title']

        return down, data1


class MusicPlayer(commands.Cog, name='Music'):
    def __init__(self, client):
        logging.getLogger('music').info(f'started MusicPlayer')
        self.bot = client
        self.player = {
            "audio_files": []
        }
        # NOTE: AN EXAMPLE OF HOW THE `self.player` DICT IS GOING TO LOOK LIKE
        self.__player = {
            "audio_files": [],
            "guildId: int": {
                "player": 'player object',  # NOTE: get current songs from player
                'queue': [{'title': 'the sound of silence', 'author': '`user object`'},
                          {'title': "Hello - Adel", 'author': '`user object`'}],
                'play': 'True/False| pause/play',
                'name': 'current audio file name',
                'author': 'user obj',
                'repeat': False
            }
        }

    def random_color(self):
        return random.randint(1, 255)

    @commands.Cog.listener('on_voice_state_update')
    async def music_voice(self, user, before, after):
        logging.getLogger('music').info(f'music_voice user={user} after={after}')
        if after.channel is None and user.id == self.bot.user.id:
            try:
                self.player[user.guild.id]['queue'].clear()
            except KeyError:
                print(f"Falha em conseguir id do server {user.guild.id}")

    async def filename_generator(self):
        logging.getLogger('music').info(f'filename_generator')
        chars = list(string.ascii_letters + string.digits)
        name = ''
        for i in range(random.randint(9, 25)):
            name += random.choice(chars)

        if name not in self.player['audio_files']:
            return name

        return await self.filename_generator()

    async def playlist(self, data, msg):
        logging.getLogger('music').info(f'playlist function data={data} msg={msg}')
        for i in data['queue']:
            self.player[msg.guild.id]['queue'].append({'title': i, 'author': msg})

    async def queue(self, msg, song):
        logging.getLogger('music').info(f'queue function msg={msg} song={song}')
        title1 = await Downloader.get_info(self, url=song)
        title = title1[0]
        data = title1[1]
        # NOTE:needs fix here
        if data['queue']:
            await self.playlist(data, msg)
            return await msg.send(
                f"Adicionada playlist {data['title']} to queue")  # NOTE: needs to be embeded to make it better output
        self.player[msg.guild.id]['queue'].append({'title': title, 'author': msg})
        return await msg.send(f"'{title}' adicionada a fila")

    async def voice_check(self, msg):
        """
        function used to make bot leave voice channel if music not being played for longer than 2 minutes
        """
        if msg.voice_client is not None:
            await asyncio.sleep(1800)
            if msg.voice_client is not None and msg.voice_client.is_playing() is False and msg.voice_client.is_paused() is False:
                await msg.voice_client.disconnect()

    async def clear_data(self, msg):
        """
        Clear the local dict data
            name - remove file name from dict
            remove file and filename from directory
            remove filename from global audio file names
        """
        name = self.player[msg.guild.id]['name']
        os.remove(name)
        self.player['audio_files'].remove(name)

    async def loop_song(self, msg):
        """
        Loop the currently playing song by replaying the same audio file via `discord.PCMVolumeTransformer()`
        """
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.player[msg.guild.id]['name']))
        loop = asyncio.get_event_loop()
        try:
            msg.voice_client.play(source, after=lambda a: loop.create_task(self.done(msg)))
        except Exception as Error:
            # Has no attribute play
            print(Error)  # NOTE: output back the error for later debugging

    async def done(self, msg, msgId: int = None):
        """
        Function to run once song completes
        Delete the "Now playing" message via ID
        """
        logging.getLogger('music').info(f'done function msg={msg} msgId={msgId}')
        if msgId:
            try:
                # chan=self.bot.get_channel(msg.channel.id)
                message = await msg.channel.fetch_message(msgId)
                await message.delete()
            except Exception as Error:
                print("Failed to get the message")

        if msg.guild.id in self.player and self.player[msg.guild.id]['repeat'] is True:
            return await self.loop_song(msg)

        await self.clear_data(msg)

        if self.player[msg.guild.id]['queue']:
            queue_data = self.player[msg.guild.id]['queue'].pop(0)
            return await self.start_song(msg=queue_data['author'], song=queue_data['title'])

        else:
            self.player[msg.guild.id]['play'] = False
            await self.voice_check(msg)

    async def start_song(self, msg, song):
        logging.getLogger('music').info(f'start_song function msg={msg} song={song}')
        new_opts = ytdl_format_options.copy()
        audio_name = await self.filename_generator()

        self.player['audio_files'].append(audio_name)
        new_opts['outtmpl'] = new_opts['outtmpl'].format(audio_name)

        ytdl = youtube_dl.YoutubeDL(new_opts)
        download1 = await Downloader.video_url(song, ytdl=ytdl, loop=self.bot.loop)

        download = download1[0]
        data = download1[1]
        self.player[msg.guild.id]['name'] = audio_name
        emb = discord.Embed(
            colour=discord.Color.from_rgb(self.random_color(), self.random_color(), self.random_color()),
            title='Tocando ', description=download.title, url=download.url)
        emb.set_thumbnail(url=download.thumbnail)
        emb.set_footer(text=f'Escolhida por {msg.author.display_name}', icon_url=msg.author.avatar_url)
        loop = asyncio.get_event_loop()

        if data['queue']:
            await self.playlist(data, msg)

        msgId = await msg.send(embed=emb)
        self.player[msg.guild.id]['player'] = download
        self.player[msg.guild.id]['author'] = msg
        msg.voice_client.play(download, after=lambda a: loop.create_task(self.done(msg, msgId.id)))
        return msg.voice_client

    @command(name='play', aliases=['p', 'Play', 'PLAY', "vaidj"])
    async def play(self, msg, *, song):
        logging.getLogger('music').info(f'play function msg={msg} song={song}')
        if msg.guild.id in self.player:
            if self.player[msg.guild.id]['play'] is True:
                return await self.queue(msg, song)

            if self.player[msg.guild.id]['queue']:
                return await self.queue(msg, song)

            if self.player[msg.guild.id]['play'] is False and not self.player[msg.guild.id]['queue']:
                return await self.start_song(msg, song)
        else:
            # IMPORTANT: THE ONLY PLACE WHERE NEW `self.player[msg.guild.id]={}` IS CREATED
            self.player[msg.guild.id] = {
                'player': None,
                'queue': [],
                'play': True,
                'author': msg,
                'name': None,
                'repeat': False
            }
            return await self.start_song(msg, song)

    @play.before_invoke
    async def before_play(self, msg):
        """
        Check voice_client
            - User voice = None:
                please join a voice channel
            - bot voice == None:
                joins the user's voice channel
            - user and bot voice NOT SAME:
                - music NOT Playing AND queue EMPTY
                    join user's voice channel
                - items in queue:
                    please join the same voice channel as the bot to add song to queue
        """
        logging.getLogger('music').info(f'before_play function')
        if msg.author.voice is None:
            return await msg.send('Conecte-se a um canal para tocar música'.title())

        if msg.voice_client is None:
            return await msg.author.voice.channel.connect()

        if msg.voice_client.channel != msg.author.voice.channel:

            # NOTE: Check player and queue
            if msg.voice_client.is_playing() is False and not self.player[msg.guild.id]['queue']:
                return await msg.voice_client.move_to(msg.author.voice.channel)
                # NOTE: move bot to user's voice channel if queue does not exist

            if self.player[msg.guild.id]['queue']:
                # NOTE: user must join same voice channel if queue exist
                return await msg.send("Please join the same voice channel as the bot to add song to queue")

    @command()
    async def repeat(self, msg):
        """
        Repeat the currently playing or turn off by using the command again
        `Ex:` .repeat
        """
        if msg.guild.id in self.player:
            if self.player[msg.guild.id]['play'] is True:
                if self.player[msg.guild.id]['repeat'] is True:
                    self.player[msg.guild.id]['repeat'] = False
                    return await msg.message.add_reaction(emoji='✅')

                self.player[msg.guild.id]['repeat'] = True
                return await msg.message.add_reaction(emoji='✅')

            return await msg.send("No audio currently playing")
        return await msg.send("Bot not in voice channel or playing music")

    @command()
    async def skip(self, msg):
        logging.getLogger('music').info(f'skip function msg={msg}')
        if msg.author.voice is not None \
                and msg.author.voice.channel != msg.voice_client.channel \
                or msg.author.voice is None:
            return await msg.send("Conecte-se ao mesmo canal do Cassino Bot")
        if msg.voice_client is None:
            return await msg.send("Nenhuma música sendo tocada")
        else:
            if not self.player[msg.guild.id]['queue'] and self.player[msg.guild.id]['play'] is False:
                return await msg.send("Nenhuma música na fila".title())
        await msg.send("Pulando música...")
        return msg.voice_client.stop()

    @commands.has_permissions(manage_channels=True)
    @command()
    async def stop(self, msg):
        if msg.author.voice is not None and msg.voice_client is not None:
            if msg.voice_client.is_playing() is True or self.player[msg.guild.id]['queue']:
                self.player[msg.guild.id]['queue'].clear()
                msg.voice_client.stop()
                return await msg.voice_client.disconnect(), await msg.message.add_reaction(emoji='✅')

    @commands.has_permissions(manage_channels=True)
    @command()
    async def pause(self, msg):
        if msg.author.voice is not None and msg.voice_client is not None:
            if msg.voice_client.is_paused() is True:
                return await msg.send("A música já está pausada.")

            if msg.voice_client.is_paused() is False:
                msg.voice_client.pause()
                await msg.message.add_reaction(emoji='✅')

    @commands.has_permissions(manage_channels=True)
    @command()
    async def resume(self, msg):
        if msg.author.voice is not None and msg.voice_client is not None:
            if msg.voice_client.is_paused() is False:
                return await msg.send("A música já está tocando.")
            else:
                msg.voice_client.resume()
                return await msg.message.add_reaction(emoji='✅')

    @command(name='queue', aliases=['song-list', 'q', 'current-songs'])
    async def _queue(self, msg):
        if msg.voice_client is not None:
            if msg.guild.id in self.player:
                if self.player[msg.guild.id]['queue']:
                    emb = discord.Embed(
                        colour=discord.Color.from_rgb(self.random_color(), self.random_color(), self.random_color()),
                        title='queue')
                    emb.set_footer(text=f'Comando utilizado por {msg.author.name}', icon_url=msg.author.avatar_url)
                    for i in self.player[msg.guild.id]['queue']:
                        emb.add_field(name=f"{i['author'].author.name}", value=i['title'], inline=False)
                    return await msg.send(embed=emb, delete_after=120)

        return await msg.send("No songs in queue")

    @command(name='current-song', aliases=['song?', ''])
    async def nowplaying(self, msg):
        logging.getLogger('music').info(f'nowplaying function msg={msg}')
        if msg.voice_client is not None and msg.voice_client.is_playing() is True:
            emb = discord.Embed(
                colour=discord.Color.from_rgb(self.random_color(), self.random_color(), self.random_color()),
                title='Música', description=self.player[msg.guild.id]['player'].title)
            emb.set_footer(text=f"{self.player[msg.guild.id]['author'].author.name}", icon_url=msg.author.avatar_url)
            emb.set_thumbnail(url=self.player[msg.guild.id]['player'].thumbnail)
            return await msg.send(embed=emb, delete_after=120)

        return await msg.send(f"Nenhuma música sendo tocada", delete_after=30)

    @command(aliases=['move-bot', 'move-b', 'mb', 'mbot'])
    async def join(self, msg, *, channel: discord.VoiceChannel = None):
        """
        Make bot join a voice channel you are in if no channel is mentioned
        `Ex:` .join
        `Ex:` .join Gen Voice
        """
        if msg.voice_client is not None:
            return await msg.send(f"O bot já está no canal")
        if msg.voice_client is None:
            if channel is None:
                return await msg.author.voice.channel.connect(), await msg.message.add_reaction(emoji='✅')
            return await channel.connect(), await msg.message.add_reaction(emoji='✅')
        else:
            if self.player[msg.guild.id]['play'] is False and not self.player[msg.guild.id]['queue']:
                return await msg.author.voice.channel.connect(), await msg.message.add_reaction(emoji='✅')

    @join.before_invoke
    async def before_join(self, msg):
        if msg.author.voice is None:
            return await msg.send("Você não está em nenhum canal de voz.")

    @join.error
    async def join_error(self, msg, error):
        if isinstance(error, commands.BadArgument):
            return msg.send(error)
        if error.args[0] == 'Command raised an exception: Exception: playing':
            return await msg.send("Entre no mesmo canal do Cassino Bot para adicionar músicas".title())

    @commands.has_permissions(manage_channels=True)
    @command(aliases=['vol'])
    async def volume(self, msg, vol: int):
        """
        Change the volume of the bot
        `Ex:` .vol 100
        `Ex:` .vol 150
        `Note:` 200 is the max
        `Permission:` manage_channels
        """
        vol = min(vol, 200) / 100
        if msg.author.voice is not None:
            if msg.voice_client is not None:
                if msg.voice_client.channel == msg.author.voice.channel and msg.voice_client.is_playing() is True:
                    msg.voice_client.source.volume = vol
                    return await msg.message.add_reaction(emoji='✅')

        return await msg.send("Conecte-se ao mesmo canal do Cassino Bot para alterar o volume".title(),
                              delete_after=30)

    @volume.error
    async def volume_error(self, msg, error):
        if isinstance(error, commands.MissingPermissions):
            return await msg.send("Manage channels or admin perms required to change volume", delete_after=30)


def setup(bot):
    bot.add_cog(MusicPlayer(bot))
