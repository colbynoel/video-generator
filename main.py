from openai import OpenAI
import re
import time
import datetime
import os
from pathlib import Path
from dotenv import load_dotenv
from video_editor import VideoEditor
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pathlib

# Create necessary paths
pathlib.Path('./videos').mkdir(parents=True, exist_ok=True) 
pathlib.Path('./openai_responses').mkdir(parents=True, exist_ok=True) 
pathlib.Path('./subtitles').mkdir(parents=True, exist_ok=True) 

#Constants
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
CLIENT_SECRETS_FILE = "./client_secret.json"
MINIMUM_VIDEO_LENGTH = 30

load_dotenv()

os.environ["OPENAI_API_KEY"] = str(os.getenv("OPEN_AI_KEY"))

def get_title(filename: str):

    with open(filename, "r") as file:
        text = file.read()

    match = re.search(r'^Title:\s*(.+)\s*$', text, re.MULTILINE)
    if match:
        title = match.group(1)
        return title
    else:
        return "I CAN'T BELIEVE THIS HAPPENED"

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


def get_authenticated_service():
    creds = None
    # Load existing credentials from file
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no valid credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('youtube', 'v3', credentials=creds)

def upload_video(youtube, file, title, description, category, tags):
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': category
        },
        'status': {
            'privacyStatus': 'private',
            'selfDeclaredMadeForKids':False 


        }
    }
    try:
        media = MediaFileUpload(f"./videos/{file}", chunksize=-1, resumable=True)
        request = youtube.videos().insert(
            part='snippet,status',
            body=body,
            media_body=media
        )
    except Exception as e:
        print(e)
        print(f"Trying to avoid quota. Sleeping for 1 minute")
        time.sleep(60)
        media = MediaFileUpload(f"./videos/{file}", chunksize=-1, resumable=True)
        request = youtube.videos().insert(
            part='snippet,status',
            body=body,
            media_body=media
        )
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%")
    print("Upload Complete!")
    return response

if __name__ == "__main__":
    video_name = "reddit_aita_FINAL.mp4"

    title = get_title("./openai_responses/llm_story.txt") + " PART {count}"

    description = '#shorts'
    category = '22'  
    tags = ['#shorts', '#reddit', "#redditstories"]

    print("Creating reddit story")
    create_reddit_story()

    print("Getting audio length")
    hours, minutes, seconds, milliseconds = VideoEditor.get_audio_duration("speech.mp3")

    print("Cutting video")
    VideoEditor.cut_duration("minecraft.mp4", "00:00:07", f"{hours}:{minutes}:{seconds}", "output.mp4")

    print("Cutting video finished")
    VideoEditor.finish_video("transcription.srt", "output.mp4", "speech.mp3", video_name)

    print("Done making full video! Check videos folder for the file")

    print("Getting YT Authed")
    youtube = get_authenticated_service()
    print("Done getting YT Authed")


    start_time = datetime.datetime(100, 1, 1, 0, 0, 0)
    video_length = VideoEditor.get_video_length(video_name)
    print(f"Video Length = {video_length}")
    segment_length = 59

    segments = int(video_length / 59)
    remainder = video_length % (segment_length * segments)
    print(f"Remainder = {remainder}")
    if remainder < MINIMUM_VIDEO_LENGTH:
        segment_length = (video_length -  30) / segments

    print(f"Segment Length = {segment_length}")

    video_length = datetime.datetime(100, 1, 1, 0, 0, 0) + datetime.timedelta(seconds=int(video_length))

    count = 1
    segmented_video = f"{video_name[:-4]}_{count}.mp4"
    while count <= segments:
        VideoEditor.cut_duration(video_name, str(start_time.time()), f"00:00:{segment_length}", segmented_video)
        print(f"Uploading {segmented_video}")
        upload_video(youtube, segmented_video, title.format(count=count), description, category, tags)
        start_time = start_time + datetime.timedelta(seconds=segment_length)
        count += 1
        segmented_video = f"{video_name[:-4]}_{count}.mp4"
    else:
        if segment_length == 59:
            video_length = video_length - datetime.timedelta(seconds=start_time.time().second)
        else:
            video_length = datetime.datetime(100, 1, 1, 0, 0, 30)

        VideoEditor.cut_duration(video_name, str(start_time.time()), str(video_length.time()), segmented_video)
        upload_video(youtube, segmented_video, title.format(count=count), description, category, tags)
    
    
