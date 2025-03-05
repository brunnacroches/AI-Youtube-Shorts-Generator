from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.editor import VideoFileClip
import subprocess
import os
import shutil

def extractAudio(video_path):
    try:
        if not os.path.exists(video_path):
            print(f"Erro: O arquivo de vídeo {video_path} não existe.")
            return None
            
        print(f"Extraindo áudio de: {video_path}")
        video_clip = VideoFileClip(video_path)
        audio_path = "audio.wav"
        
        if video_clip.audio is None:
            print("Aviso: O vídeo não contém áudio. Tentando métodos alternativos...")
            
            # Tentar usar FFmpeg diretamente se disponível
            ffmpeg_path = shutil.which('ffmpeg')
            if ffmpeg_path:
                try:
                    print("Tentando extrair áudio com FFmpeg...")
                    cmd = [
                        ffmpeg_path,
                        "-i", video_path,
                        "-vn",  # No video
                        "-acodec", "pcm_s16le",  # PCM 16bit output
                        "-ar", "44100",  # 44.1kHz sample rate
                        "-ac", "2",  # stereo
                        audio_path,
                        "-y"  # Overwrite
                    ]
                    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    print("Áudio extraído com sucesso usando FFmpeg")
                    return audio_path
                except Exception as e:
                    print(f"Erro ao extrair áudio com FFmpeg: {e}")
                    return None
            else:
                print("FFmpeg não encontrado. Não é possível extrair o áudio.")
                return None
                
        # Continuar com o método normal se o vídeo tem áudio
        video_clip.audio.write_audiofile(audio_path, verbose=False, logger=None)
        video_clip.close()
        print(f"Áudio extraído para: {audio_path}")
        return audio_path
    except Exception as e:
        print(f"Erro ao extrair áudio: {e}")
        return None


def crop_video(input_file, output_file, start_time, end_time):
    try:
        if not os.path.exists(input_file):
            print(f"Erro: O arquivo de vídeo {input_file} não existe.")
            return False
            
        if start_time >= end_time:
            print(f"Erro: Tempo inicial ({start_time}) deve ser menor que tempo final ({end_time}).")
            return False
            
        print(f"Cortando vídeo de {start_time:.2f}s até {end_time:.2f}s...")
        
        with VideoFileClip(input_file) as video:
            # Verificar se os tempos estão dentro da duração do vídeo
            if end_time > video.duration:
                print(f"Aviso: Tempo final ({end_time:.2f}s) é maior que a duração do vídeo ({video.duration:.2f}s).")
                end_time = video.duration
                print(f"Ajustando para: {end_time:.2f}s")
                
            if start_time < 0:
                print(f"Aviso: Tempo inicial ({start_time:.2f}s) é negativo.")
                start_time = 0
                print(f"Ajustando para: {start_time:.2f}s")
                
            # Realizar o corte
            cropped_video = video.subclip(start_time, end_time)
            
            # Criar diretório para o arquivo de saída se não existir
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            # Salvar o vídeo cortado
            cropped_video.write_videofile(output_file, codec='libx264', verbose=False, logger=None)
            
            print(f"Vídeo cortado salvo em: {output_file}")
            return True
    except Exception as e:
        print(f"Erro ao cortar vídeo: {e}")
        return False

# Example usage:
if __name__ == "__main__":
    input_file = r"Example.mp4" ## Test
    print(input_file)
    output_file = "Short.mp4"
    start_time = 31.92 
    end_time = 49.2   

    if crop_video(input_file, output_file, start_time, end_time):
        print("Corte realizado com sucesso!")
    else:
        print("Falha ao realizar o corte.")

