import cv2
import numpy as np
import sys
import os
import shutil
from moviepy.editor import *
from Components.Speaker import detect_faces_and_speakers, Frames
global Fps

def crop_to_vertical(input_video_path, output_video_path):
    try:
        # Verificar se o arquivo de entrada existe
        if not os.path.exists(input_video_path):
            print(f"Erro: O arquivo {input_video_path} não existe.")
            return False
            
        detect_faces_and_speakers(input_video_path, "DecOut.mp4")
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

        cap = cv2.VideoCapture(input_video_path, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            print(f"Erro: Não foi possível abrir o vídeo {input_video_path}.")
            print("Verifique se o FFmpeg está instalado corretamente e se o arquivo de vídeo é válido.")
            return False

        original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        vertical_height = int(original_height)
        vertical_width = int(vertical_height * 9 / 16)
        print(vertical_height, vertical_width)

        if original_width < vertical_width:
            print(f"Aviso: Largura original do vídeo ({original_width}) é menor que a largura vertical desejada ({vertical_width}).")
            vertical_width = original_width
            print(f"Usando largura ajustada: {vertical_width}")

        x_start = (original_width - vertical_width) // 2
        x_end = x_start + vertical_width
        print(f"start and end - {x_start} , {x_end}")
        print(x_end-x_start)
        half_width = vertical_width // 2

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_video_path, fourcc, fps, (vertical_width, vertical_height))
        global Fps
        Fps = fps
        print(fps)
        count = 0
        
        # Use try-except para capturar qualquer erro durante o processamento de frames
        try:
            for _ in range(total_frames):
                ret, frame = cap.read()
                if not ret:
                    print(f"Aviso: Não foi possível ler o frame {count+1}/{total_frames}.")
                    break
                    
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
                
                if len(faces) >-1:
                    if len(faces) == 0:
                        try:
                            (x, y, w, h) = Frames[count]
                        except (IndexError, ValueError) as e:
                            print(f"Aviso: Erro ao acessar frame {count}: {e}")
                            (x, y, w, h) = (0, 0, 0, 0)  # Default values

                    try:
                        #check if face 1 is active
                        (X, Y, W, H) = Frames[count]
                    except Exception as e:
                        try:
                            (X, Y, W, H) = Frames[count][0]
                            print(Frames[count][0])
                        except (IndexError, ValueError) as e:
                            print(f"Aviso: Erro com detecção de face no frame {count}: {e}")
                            (X, Y, W, H) = (0, 0, 0, 0)  # Default values
                    
                    for f in faces:
                        x1, y1, w1, h1 = f
                        center = x1+ w1//2
                        if center > X and center < X+W:
                            x = x1
                            y = y1
                            w = w1
                            h = h1
                            break

                    # print(faces[0])
                    try:
                        centerX = x+(w//2)
                        print(centerX)
                        print(x_start - (centerX - half_width))
                        if count == 0 or (x_start - (centerX - half_width)) <1 :
                            ## IF dif from prev fram is low then no movement is done
                            pass #use prev vals
                        else:
                            x_start = centerX - half_width
                            x_end = centerX + half_width
                    except UnboundLocalError:
                        print(f"Aviso: Erro ao calcular centerX no frame {count} - usando valor padrão")
                        # Use default values if no face was detected properly

                # Ensure crop region is within video boundaries
                x_start = max(0, x_start)
                x_end = min(original_width, x_end)

                count += 1
                
                # Safely crop the frame
                if x_start < x_end and x_end <= frame.shape[1]:
                    cropped_frame = frame[:, x_start:x_end]
                    
                    # Check if dimensions are consistent
                    if cropped_frame.shape[1] != vertical_width:
                        print(f"Aviso: Dimensões inconsistentes no frame {count}")
                        # Resize to ensure consistent dimensions
                        cropped_frame = cv2.resize(cropped_frame, (vertical_width, vertical_height))
                    
                    print(cropped_frame.shape)
                    out.write(cropped_frame)
                else:
                    print(f"Aviso: Coordenadas inválidas para corte no frame {count}: x_start={x_start}, x_end={x_end}")
                    # Use default center crop
                    default_x_start = (original_width - vertical_width) // 2
                    default_x_end = default_x_start + vertical_width
                    cropped_frame = frame[:, default_x_start:default_x_end]
                    out.write(cropped_frame)
                
        except Exception as e:
            print(f"Erro durante o processamento de frames: {e}")
            
        cap.release()
        out.release()
        print("Cropping complete. The video has been saved to", output_video_path, count)
        return True
        
    except Exception as e:
        print(f"Erro fatal em crop_to_vertical: {e}")
        return False



def combine_videos(video_with_audio, video_without_audio, output_filename):
    try:
        # Verificar se os arquivos existem
        for file in [video_with_audio, video_without_audio]:
            if not os.path.exists(file):
                print(f"Erro: O arquivo {file} não existe.")
                return False
                
        # Check if FFmpeg is available
        ffmpeg_path = shutil.which('ffmpeg')
        if not ffmpeg_path:
            print("\nAviso: FFmpeg não encontrado. Usando moviepy para combinar os vídeos.")
            print("Isso pode ser mais lento e menos confiável.")
            print("Para melhor desempenho, instale o FFmpeg: https://ffmpeg.org/download.html")
        
        # Load video clips
        try:
            clip_with_audio = VideoFileClip(video_with_audio)
            clip_without_audio = VideoFileClip(video_without_audio)
            
            audio = clip_with_audio.audio
            
            # Se não há áudio, avisar o usuário
            if audio is None:
                print("Aviso: O vídeo fonte não contém áudio.")
                
            combined_clip = clip_without_audio.set_audio(audio)
            
            global Fps
            # Use o codec mais compatível
            combined_clip.write_videofile(output_filename, codec='libx264', audio_codec='aac', 
                                          fps=Fps, preset='medium', bitrate='3000k', 
                                          verbose=False, logger=None)
            
            print(f"Vídeo combinado salvo com sucesso como {output_filename}")
            return True
            
        except Exception as e:
            print(f"Erro ao usar moviepy: {e}")
            
            # Tentar com FFmpeg diretamente se disponível
            if ffmpeg_path:
                try:
                    print("Tentando com FFmpeg diretamente...")
                    # Comando FFmpeg para combinar vídeo e áudio
                    ffmpeg_cmd = [
                        ffmpeg_path, 
                        "-i", video_without_audio, 
                        "-i", video_with_audio,
                        "-map", "0:v", 
                        "-map", "1:a", 
                        "-c:v", "copy",
                        "-c:a", "aac",
                        "-shortest",
                        output_filename,
                        "-y"
                    ]
                    
                    subprocess.run(ffmpeg_cmd, check=True)
                    print(f"FFmpeg combinou o vídeo com sucesso como {output_filename}")
                    return True
                except subprocess.CalledProcessError as e:
                    print(f"Erro no comando FFmpeg: {e}")
                    return False
            
            return False
    
    except Exception as e:
        print(f"Erro fatal em combine_videos: {e}")
        return False



if __name__ == "__main__":
    input_video_path = r'Out.mp4'
    output_video_path = 'Croped_output_video.mp4'
    final_video_path = 'final_video_with_audio.mp4'
    detect_faces_and_speakers(input_video_path, "DecOut.mp4")
    crop_to_vertical(input_video_path, output_video_path)
    combine_videos(input_video_path, output_video_path, final_video_path)



