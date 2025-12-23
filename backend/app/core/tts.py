
import edge_tts
import asyncio
import tempfile
import os
from mutagen.mp3 import MP3

# ============================================
# Voice Configuration per Agent
# ============================================

AGENT_VOICES = {
    "Attacker": {
        "voice": "th-TH-NiwatNeural",
        "pitch": "-5Hz",
        "volume": "+10%",
        "rate": "+0%"
    },
    "Defender": {
        "voice": "th-TH-PremwadeeNeural",
        "pitch": "+0Hz",
        "volume": "+10%",
        "rate": "+0%"
    },
    "Strategist": {
        "voice": "th-TH-NiwatNeural",
        "pitch": "+10Hz",
        "volume": "+10%",
        "rate": "-5%"  # Slightly slower for authority
    },
    "default": {
        "voice": "th-TH-NiwatNeural",
        "pitch": "+0Hz",
        "volume": "+10%",
        "rate": "+0%"
    }
}

def get_voice_config(agent: str) -> dict:
    """
    Get voice configuration for a specific agent.
    """
    for key in AGENT_VOICES:
        if key in agent:
            return AGENT_VOICES[key]
    return AGENT_VOICES["default"]


async def generate_audio(text: str, voice: str = "th-TH-NiwatNeural", 
                         pitch: str = "+0Hz", volume: str = "+10%", 
                         rate: str = "+0%") -> str:
    """
    Generates audio from text using edge-tts and saves it to a temporary file.
    Returns the path to the temporary audio file.
    """
    if not text:
        return ""
        
    try:
        communicate = edge_tts.Communicate(
            text, 
            voice, 
            pitch=pitch, 
            volume=volume, 
            rate=rate
        )
        
        # Create a temp file
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        
        await communicate.save(path)
        return path
    except Exception as e:
        print(f"❌ TTS Error: {e}")
        return ""


def get_audio_bytes_with_duration(text: str, voice: str = "th-TH-NiwatNeural",
                    pitch: str = "+0Hz", volume: str = "+10%",
                    rate: str = "+0%") -> tuple:
    """
    Returns tuple of (audio_bytes, duration_seconds).
    Duration is calculated from the actual MP3 file using mutagen.
    """
    path = asyncio.run(generate_audio(text, voice, pitch, volume, rate))
    if path and os.path.exists(path):
        # Get accurate duration from MP3 metadata
        try:
            audio = MP3(path)
            duration = audio.info.length
        except:
            # Fallback: estimate ~150 chars/sec
            duration = len(text) / 150.0
        
        with open(path, "rb") as f:
            data = f.read()
        os.unlink(path)  # Clean up temp file
        return (data, duration)
    return (None, 0)


def get_audio_bytes(text: str, voice: str = "th-TH-NiwatNeural",
                    pitch: str = "+0Hz", volume: str = "+10%",
                    rate: str = "+0%") -> bytes:
    """
    Synchronous wrapper to get audio bytes only (for backward compatibility).
    """
    data, _ = get_audio_bytes_with_duration(text, voice, pitch, volume, rate)
    return data


def get_audio_for_agent(text: str, agent: str) -> bytes:
    """
    Convenience function to get audio with the right voice for a specific agent.
    Returns only audio bytes for backward compatibility.
    """
    config = get_voice_config(agent)
    return get_audio_bytes(
        text,
        voice=config["voice"],
        pitch=config["pitch"],
        volume=config["volume"],
        rate=config["rate"]
    )


def get_audio_for_agent_with_duration(text: str, agent: str) -> tuple:
    """
    Returns (audio_bytes, duration_seconds) with the right voice for a specific agent.
    """
    config = get_voice_config(agent)
    return get_audio_bytes_with_duration(
        text,
        voice=config["voice"],
        pitch=config["pitch"],
        volume=config["volume"],
        rate=config["rate"]
    )
