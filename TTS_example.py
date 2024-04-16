from TTS.api import TTS
tts = TTS("tts_models/en/multi-dataset/tortoise-v2")


tts.tts_to_file(text="What does this sound like? This! or is this what it sounds like. I am excited to hear how TTS works!",
                file_path="output.wav")
