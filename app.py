import discord
from discord import FFmpegPCMAudio
from discord import FFmpegOpusAudio
from discord.ext import commands, tasks
#from discord.ext.audiorec import NativeVoiceClient
import os
from dotenv import load_dotenv
import youtube_dl
import yt_dlp
import numpy as np
import wave
import soundfile
from scipy.io.wavfile import read
import pydub


from scipy.io import wavfile
import scipy.signal as sps


import tempfile



from enum import Enum
import whisper




model = whisper.load_model("small")
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
    'options': '-vn'
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

def bytes_to_float(_bytes: bytes):
    """bytes_to_float.    Parameters    ----------    _bytes : bytes        _bytes    """    
    sig = np.frombuffer(_bytes, dtype=np.int16)    
    dtype = np.dtype("float32")    
    i = np.iinfo(sig.dtype)    
    abs_max = 2 ** (i.bits - 1)    
    offset = i.min + abs_max    
    return (sig.astype(dtype) - offset) / abs_max


def mp3_read(f, normalized=True):    
    """MP3 to numpy array"""    
    a = pydub.AudioSegment.from_mp3(f)    
    y = np.array(a.get_array_of_samples())    
    if a.channels == 2:
        y = y.reshape((-1, 2))    
        if normalized:        
            return a.frame_rate, np.float32(y) / 2**15    
        else:        
            return a.frame_rate, y


async def once_done(sink, channel: discord.TextChannel, *args):
    recorded_users = [f"<@{user_id}>" for user_id, audio in sink.audio_data.items()]
    await sink.vc.disconnect()
    files = [
        discord.File(audio.file, f"{user_id}.{sink.encoding}")
        for user_id, audio in sink.audio_data.items()
    ]
    
    # print(files[0].fp.tell())


    # print(files[0])
    # print(files[0].fp)
    # print(files[0].fp.read()[:100])
    # files[0].fp.seek(0)


    #tf = tempfile.NamedTemporaryFile(suffix="wav")
    
    with open("testfiles.wav", "wb") as tf:
        tf.write(files[0].fp.read())
    
    #print(bytes_to_float(files[0].fp.read()))
    
    
    # sampling_rate, data = mp3_read(files[0].fp)
    # print(data[:100])
    # print(data.shape)

    # # Your new sampling rate
    # new_rate = 16000
    # # Read file
    # #sampling_rate, data = mp3file.read(tf)
    # print(data[:100], sampling_rate)
    # # Resample data
    # number_of_samples = round(len(data) * float(new_rate) / sampling_rate)
    # data = sps.resample(data, number_of_samples)
    # print(data[:100])
    # print(sampling_rate)
    #print(files)
    #print(files[0])
    #print(discord.sinks.RawData(sink.audio_data.values(), discord.TextChannel))
    #print(sink.audio_data.values())
    #print(sink.audio_data.items())

 

    # data_bytes = read(files[0].fp)
    # print(data_bytes)
    # np_data_bytes = np.array(data_bytes[1],dtype=float)
    # print(np_data_bytes[:100])
    
    
    #data, samplerate = soundfile.read(files[0].fp.read())
    #print(type(data))
    #print(samplerate)
    # with wave.open(files[0].fp) as wav_file:
    #     wav_file.setpos(0)        
    #     n = wav_file.getnframes()
    #     b = wav_file.readframes(n)
    #     floats = bytes_to_float(b)
    #     print(b[:100])
    #     print(floats)
    #     print(n)
    #     print(wav_file)

    # data = bytes_to_float(files[0].fp.read())

    whisper_result = model.transcribe("testfiles.wav", fp16=False, language='da')
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