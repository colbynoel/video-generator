import subprocess
import ass
import re
import sys
from openai import OpenAI
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

os.environ["OPENAI_API_KEY"] = str(os.getenv("OPEN_AI_KEY"))

def create_reddit_story():
    client = OpenAI()

    text_response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are the best reddit post creator in the world. You come up with the most interesting stories. Make sure that you only give the story to the user. I also want the title of the story before you introduce the body of the story. Start your title as such 'Title: A.I.T.A {title of the story}', but do not do the same for the story. Just after the title give me the story of the post"},
        {"role": "user", "content": "Create me an am I the asshole reddit style post. I want the story to go along with it. Make the story super dramatic and juicy. I want this to be an exciting story. Make sure the story leaves the reader on the edge of their seat! Do not limit yourself to just creating cheating stories. Please choose from something like a work story, relationship story, family story, or random occurence type of story. Do not limit yourself. Remember, Start your title as such 'Title: A.I.T.A {title of the story}' "},
    ]
    )

    print("Saved LLM Story")
    with open("./openai_responses/llm_story.txt", "w") as f:
        f.write(str(text_response.choices[0].message.content))

    speech_file_path = Path(__file__).parent / "openai_responses/speech.mp3"
    audio_response = client.audio.speech.create(
    model="tts-1",
    voice="onyx",
    input=str(text_response.choices[0].message.content)
    )

    with open(speech_file_path, 'wb') as f:
        f.write(audio_response.content)
    print(f"Audio saved to {speech_file_path}")

    print("Creating SRT file via Whisper")
    audio_file = open("./openai_responses/speech.mp3", "rb")
    transcript = client.audio.transcriptions.create(
        file=audio_file,
        model="whisper-1",
        response_format="srt"
    )
    with open("./subtitles/transcription.srt", "w") as file:
        file.write(transcript)


def cut_duration(video_file: str, start_time: str, end_time: str, output_file: str):
    try:
        command = ['ffmpeg', '-y', '-i', f"./videos/{video_file}", '-ss', start_time, '-t', end_time,
                      '-c:v', 'libx264', '-c:a', 'aac', f"./videos/{output_file}"]
        process = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print("FFmpeg Output:\n", process.stdout)
        print("FFmpeg Error (if any):\n", process.stderr)
    except subprocess.CalledProcessError as e:
        print("Error running FFmpeg:", e, file=sys.stderr)
        print("FFmpeg stderr:", e.stderr, file=sys.stderr)

def edit_ass(ass_file: str):
    with open(f"./subtitles/{ass_file}", encoding="utf_8_sig") as input_file:
        doc = ass.parse(input_file)
        doc.styles[0].fontname = "BurbankBigCondensed-Bold"
        doc.styles[0].fontsize = "25.0"
        doc.styles[0].alignment = "5"

    with open(f"./subtitles/{ass_file}", "w", encoding="utf_8_sig") as f:
        doc.dump_file(f)

def get_audio_duration(audio_file: str):
    command = ["ffmpeg", "-i", f"./openai_responses/{audio_file}"]
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = result.stderr.decode('utf-8')

        # Extract duration using regex
        match = re.search(r"Duration: (\d+):(\d+):(\d+)\.(\d+)", output)
        if match:
            hours = match.group(1).zfill(2)
            minutes = match.group(2).zfill(2)
            seconds = match.group(3).zfill(2)
            milliseconds = match.group(4).zfill(3)
            
            return hours, minutes, seconds, milliseconds
        else:
            raise ValueError("Could not extract duration from the output.")
    except subprocess.CalledProcessError as e:
        raise ValueError(f"FFmpeg command failed with error: {e}")

def finish_video(transcription_file: str, video_file: str, audio_file:str, output_file: str):

    ass_file = transcription_file[:-4] + ".ass"
    try:
        print("Converting SRT file to ASS file")
        command = ["ffmpeg", "-y", "-i", f"./subtitles/{transcription_file}", f"./subtitles/{ass_file}"]
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"Error converting SRT file to ASS file. Error: {e}")

    print("Editing ASS file")
    edit_ass(ass_file)

    try:
        print("Adding audio and subtitles to final video")
        command = [
            "ffmpeg", "-y", "-i", f"./videos/{video_file}", "-i", f"./openai_responses/{audio_file}", 
            "-c:v", "libx264", "-c:a", "aac", "-vf", f"subtitles=./subtitles/{ass_file}:fontsdir=./fonts",
            "-map", "0:v:0", "-map", "1:a:0",  
            f"./videos/{output_file}", "-progress", "-", "-nostats"
        ]
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"Error applying ASS file to video. Error: {e}")


if __name__ == "__main__":
    print("Creating reddit story")
    create_reddit_story()
    print("Getting audio length")
    hours, minutes, seconds, milliseconds = get_audio_duration("speech.mp3")
    print("Cutting video")
    cut_duration("minecraft.mp4", "00:00:07", f"{hours}:{minutes}:{seconds}", "output.mp4")
    print("Cutting video finished")
    finish_video("transcription.srt", "output.mp4", "speech.mp3", "reddit_aita_FINAL.mp4")
    print("Done making video! Check videos folder")

