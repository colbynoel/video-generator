import subprocess
import sys

def run_ffmpeg_command(command):
    try:
        process = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print("FFmpeg Output:\n", process.stdout)
        print("FFmpeg Error (if any):\n", process.stderr)
    except subprocess.CalledProcessError as e:
        print("Error running FFmpeg:", e, file=sys.stderr)
        print("FFmpeg stderr:", e.stderr, file=sys.stderr)

if __name__ == "__main__":
    ffmpeg_command = ['ffmpeg', '-i', 'input_video.mp4', 
                      '-codec:v', 'libx264', '-profile:v', 
                      'main', '-preset', 'slow', '-b:v', '400k', 
                      '-maxrate', '400k', '-bufsize', '800k', '-vf', 
                      'scale=-1:1080', '-threads', '0', '-b:a', '128k', 'output_video.mp4']
    
    run_ffmpeg_command(ffmpeg_command)

