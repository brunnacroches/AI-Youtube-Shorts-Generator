import os
from pytubefix import YouTube
import subprocess
import sys
import shutil

def get_video_size(stream):
    return stream.filesize / (1024 * 1024)

def download_youtube_video(url):
    try:
        yt = YouTube(url)

        video_streams = yt.streams.filter(type="video").order_by('resolution').desc()
        audio_stream = yt.streams.filter(only_audio=True).first()

        print("Available video streams:")
        for i, stream in enumerate(video_streams):
            size = get_video_size(stream)
            stream_type = "Progressive" if stream.is_progressive else "Adaptive"
            print(f"{i}. Resolution: {stream.resolution}, Size: {size:.2f} MB, Type: {stream_type}")

        # Find a progressive stream to avoid needing FFmpeg
        progressive_streams = [s for s in video_streams if s.is_progressive]
        
        if progressive_streams:
            print("\nRecomendado: Use um stream progressivo para evitar problemas com FFmpeg")
            print("Streams progressivos disponíveis:")
            for i, stream in enumerate(progressive_streams):
                size = get_video_size(stream)
                print(f"P{i}. Resolution: {stream.resolution}, Size: {size:.2f} MB")
            
            print("\nEscolha um stream normal (0, 1, 2...) ou um progressivo (P0, P1, P2...)")
            choice_input = input("Enter your choice (e.g., '0' or 'P0'): ")
            
            if choice_input.startswith('P'):
                choice = int(choice_input[1:])
                selected_stream = progressive_streams[choice]
            else:
                choice = int(choice_input)
                selected_stream = video_streams[choice]
        else:
            choice = int(input("Enter the number of the video stream to download: "))
            selected_stream = video_streams[choice]

        if not os.path.exists('videos'):
            os.makedirs('videos')

        print(f"Downloading video: {yt.title}")
        
        # Ensure safe filename for Windows
        safe_title = "".join([c for c in yt.title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        if not safe_title:
            safe_title = "youtube_video"
            
        video_file = selected_stream.download(output_path='videos', filename=f"video_{safe_title}")

        # If it's not progressive, we need to merge with audio
        if not selected_stream.is_progressive:
            print("Downloading audio...")
            audio_file = audio_stream.download(output_path='videos', filename=f"audio_{safe_title}")

            # Output file name
            output_file = os.path.join('videos', f"{safe_title}.mp4")
            
            # Check if ffmpeg is available
            ffmpeg_path = shutil.which('ffmpeg')
            
            if ffmpeg_path:
                print("Merging video and audio using ffmpeg...")
                try:
                    # Try to find ffmpeg in PATH first
                    ffmpeg_cmd = [ffmpeg_path, "-i", video_file, "-i", audio_file, 
                                "-c:v", "copy", "-c:a", "aac", 
                                output_file, "-y"]
                    
                    subprocess.run(ffmpeg_cmd, check=True)
                    print("Merged successfully with ffmpeg!")
                    
                    # Clean up temporary files
                    os.remove(video_file)
                    os.remove(audio_file)
                except subprocess.CalledProcessError as e:
                    print(f"Error executing FFmpeg: {e}")
                    print("Continuing with video-only file.")
                    output_file = video_file
            else:
                print("\nAVISO: FFmpeg não encontrado. Não é possível mesclar áudio e vídeo.")
                print("Usando apenas o arquivo de vídeo. O áudio pode estar ausente ou de baixa qualidade.")
                print("Para resolver, instale o FFmpeg: https://ffmpeg.org/download.html")
                print("E adicione-o ao PATH do sistema.")
                output_file = video_file
        else:
            output_file = video_file

        print(f"Downloaded: {yt.title} to 'videos' folder")
        print(f"File path: {output_file}")
        return output_file

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print("Please make sure you have the latest version of pytube and ffmpeg-python installed.")
        print("You can update them by running:")
        print("pip install --upgrade pytube pytubefix")
        print("Also, ensure that ffmpeg is installed on your system and available in your PATH.")
        print("Download FFmpeg from: https://ffmpeg.org/download.html")
        return None

if __name__ == "__main__":
    youtube_url = input("Enter YouTube video URL: ")
    download_youtube_video(youtube_url)
