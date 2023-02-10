import discord
from discord import FFmpegPCMAudio
from discord import FFmpegOpusAudio
from discord.ext import commands, tasks
#from discord.ext.audiorec import NativeVoiceClient
from plyer import notification
#test
import os
from dotenv import load_dotenv
import youtube_dl
import yt_dlp
import numpy as np
import wave
import soundfile
import ffmpeg

import array
import pydub
from pydub import AudioSegment
from pydub.utils import mediainfo
import torch
import torchaudio
import io
from io import BytesIO
import tempfile
from enum import Enum
import whisper

model = whisper.load_model("small", download_root="./models")
#model = whisper.load_model("small")
#options = whisper.DecodingOptions(language= 'en', fp16=False)


load_dotenv()

#discord.opus.load_opus("libopus.so.0")
#print(discord.opus.is_loaded())

#Get api token from .env file
DISCORD_TOKEN = os.getenv("discord_token")
print(DISCORD_TOKEN)

intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='!',intents=intents)

youtube_dl.utils.bug_reports_message = lambda: ''

ydl_opts = {'format': 'bestaudio'}
connections = {}

ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn',
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class Sinks(Enum):
    mp3 = discord.sinks.MP3Sink()
    wav = discord.sinks.WaveSink()
    pcm = discord.sinks.PCMSink()
    ogg = discord.sinks.OGGSink()
    mka = discord.sinks.MKASink()
    mkv = discord.sinks.MKVSink()
    mp4 = discord.sinks.MP4Sink()
    m4a = discord.sinks.M4ASink()

def load_audio(file: (str, bytes), sr: int = 16000):
    """
    Open an audio file and read as mono waveform, resampling as necessary

    Parameters
    ----------
    file: (str, bytes)
        The audio file to open or bytes of audio file

    sr: int
        The sample rate to resample the audio if necessary

    Returns
    -------
    A NumPy array containing the audio waveform, in float32 dtype.
    """
    
    if isinstance(file, bytes):
        inp = file
        file = 'pipe:'
    else:
        inp = None
    
    try:
        # This launches a subprocess to decode audio while down-mixing and resampling as necessary.
        # Requires the ffmpeg CLI and `ffmpeg-python` package to be installed.
        out, _ = (
            ffmpeg.input(file, threads=0)
            .output("-", format="s16le", acodec="pcm_s16le", ac=1, ar=sr)
            .run(cmd="ffmpeg", capture_stdout=True, capture_stderr=True, input=inp)
        )
    except ffmpeg.Error as e:
        raise RuntimeError(f"Failed to load audio: {e.stderr.decode()}") from e

    return np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0


async def once_done(sink, channel: discord.TextChannel, *args):
    recorded_users = [f"<@{user_id}>" for user_id, audio in sink.audio_data.items()]
    await sink.vc.disconnect()
    files = [
        discord.File(audio.file, f"{user_id}.{sink.encoding}")
        for user_id, audio in sink.audio_data.items()
    ]
    
    print(files[0])
    print(files[0].fp)
    print(files[0].fp.read()[:100])
    files[0].fp.seek(0)

    sound = AudioSegment.from_file(BytesIO(files[0].fp.read()))
    files[0].fp.seek(0)
    
    #channel_sounds = sound.split_to_mono()
    #channel_sounds = sound.set_channels(1)
    sound = sound.set_frame_rate(16000)
    channel_sounds = sound.set_channels(1)

    samples = [s.get_array_of_samples() for s in channel_sounds]
    fp_arr = np.array(samples).T.astype(np.float32)


    whisper_result = model.transcribe(load_audio(files[0].fp.read()), fp16=False, language='da')
    #whisper_result = model.transcribe(fp_arr, fp16=False, language='da')
    print(whisper_result)
    files[0].fp.seek(0)
    await channel.send(
        f"Finished! Recorded audio for {', '.join(recorded_users)}.", files=files
    )
    await channel.send(whisper_result["text"])

@bot.command(name='join', help='Tells the bot to join the voice channel')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send("{} is not connected to a voice channel".format(ctx.message.author.name))
        return
    else:
        channel = ctx.message.author.voice.channel
    await channel.connect()

@bot.command(name='tidal')
async def start(ctx: discord.ApplicationContext):
    voice = ctx.author.voice
    server = ctx.message.guild
    vc = server.voice_client

    if not voice:
        return await ctx.send("You're not in a vc right now")

    connections.update({ctx.guild.id: vc})
    
    #session.login_oauth_simple(function=print)
    #await ctx.send(session.login_oauth_simple(function=print))
    login, future = session.login_oauth()
    ost = login.verification_uri_complete
    msg = "Open URL to login to Tidal: " +ost
    await ctx.send(msg)
    print(session.check_login())
    #session.load_oauth_session(token_type, access_token, refresh_token, expiry_time)
    
    #ctx.send(print(("open the url to login", login.verification_uri_complete)))


@bot.command(name='record')
async def start(ctx: discord.ApplicationContext):
    """Record your voice!"""
    voice = ctx.author.voice
    server = ctx.message.guild
    vc = server.voice_client

    if not voice:
        return await ctx.send("You're not in a vc right now")

    #vc = voice.channel
    #vc = connections[ctx.guild.id]
    connections.update({ctx.guild.id: vc})

    vc.start_recording(
        discord.sinks.WaveSink(),
        # discord.sinks.MP3Sink(),
        once_done,
        ctx.channel,
    )

    await ctx.send("The recording has started!")


@bot.command(name='stop_recording')
async def stop_recording(ctx):
    if ctx.guild.id in connections:
        vc = connections[ctx.guild.id]
        vc.stop_recording()
        del connections[ctx.guild.id]
        #await ctx.delete()
    else:
        await ctx.send("I am currently not recording here.")




@bot.command(name='leave', help='To make the bot leave the voice channel')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
    else:
        await ctx.send("The bot is not connected to a voice channel.")

@bot.command(name='play_song', help='To play song')
async def play(ctx,url):
    try:
        server = ctx.message.guild
        voice_channel = server.voice_client
        #voiceChannel = ctx.message.author.voice.channel
        #await voiceChannel.connect()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            song_info = ydl.extract_info(url, download=False)
        ctx.voice_client.play(discord.FFmpegOpusAudio(song_info["url"], **ffmpeg_options))
    except:
        print(Exception)


@bot.command(name='pause', help='This command pauses the song')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.pause()
    else:
        await ctx.send("The bot is not playing anything at the moment.")
    
@bot.command(name='resume', help='Resumes the song')
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        await voice_client.resume()
    else:
        await ctx.send("The bot was not playing anything before this. Use play_song command")

@bot.command(name='stop', help='Stops the song')
async def stop(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.stop()
    else:
        await ctx.send("The bot is not playing anything at the moment.")


if __name__ == "__main__" :
    bot.run(DISCORD_TOKEN, reconnect=True)