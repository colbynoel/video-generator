import subprocess
import re
import ass
import sys

class VideoEditor(object):

    @staticmethod
    def get_video_length(video_file: str) -> float:
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                "format=duration", "-of",
                                "default=noprint_wrappers=1:nokey=1", f"./videos/{video_file}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        return float(result.stdout)

    @staticmethod
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

    @staticmethod
    def edit_ass(ass_file: str):
        with open(f"./subtitles/{ass_file}", encoding="utf_8_sig") as input_file:
            doc = ass.parse(input_file)
            doc.styles[0].fontname = "BurbankBigCondensed-Bold"
            doc.styles[0].fontsize = "15.0"
            doc.styles[0].alignment = "5"

        with open(f"./subtitles/{ass_file}", "w", encoding="utf_8_sig") as f:
            doc.dump_file(f)

    @staticmethod
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

    @staticmethod
    def finish_video(transcription_file: str, video_file: str, audio_file:str, output_file: str):

        ass_file = transcription_file[:-4] + ".ass"
        try:
            print("Converting SRT file to ASS file")
            command = ["ffmpeg", "-y", "-i", f"./subtitles/{transcription_file}", f"./subtitles/{ass_file}"]
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            print(f"Error converting SRT file to ASS file. Error: {e}")

        print("Editing ASS file")
        VideoEditor.edit_ass(ass_file)

        try:
            print("Adding audio and subtitles to final video")
            command = [
                "ffmpeg", "-y", "-i", f"./videos/{video_file}", "-i", f"./openai_responses/{audio_file}", 
                "-c:v", "libx264", "-c:a", "aac", "-lavfi", f'[0:v]scale=iw:2*trunc(iw*16/18),boxblur=luma_radius=min(h\\,w)/20:luma_power=1:chroma_radius=min(cw\\,ch)/20:chroma_power=1[bg];[bg][0:v]overlay=(W-w)/2:(H-h)/2,setsar=1,subtitles=./subtitles/{ass_file}:fontsdir=./fonts',
                "-map", "0:v:0", "-map", "1:a:0",  
                f"./videos/{output_file}", "-progress", "-", "-nostats"       
            ]
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            print(f"Error applying ASS file to video. Error: {e}")
            print("Error running FFmpeg:", e, file=sys.stderr)
            print("FFmpeg stderr:", e.stderr, file=sys.stderr)
