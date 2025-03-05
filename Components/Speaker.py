import cv2
import numpy as np
import os
import sys
import subprocess
import shutil
from pydub import AudioSegment
import contextlib

# Verificar disponibilidade de webrtcvad
try:
    import webrtcvad
    import wave
    WEBRTCVAD_AVAILABLE = True
    # Initialize VAD
    vad = webrtcvad.Vad(2)  # Aggressiveness mode from 0 to 3
except ImportError:
    WEBRTCVAD_AVAILABLE = False
    print("\nAVISO: webrtcvad não está disponível. A detecção de voz será limitada.")
    print("Para instalar, você precisa do Microsoft Visual C++ Build Tools:")
    print("1. Baixe e instale: https://visualstudio.microsoft.com/visual-cpp-build-tools/")
    print("2. Depois, instale webrtcvad: pip install webrtcvad")

# Update paths to the model files
prototxt_path = "models/deploy.prototxt"
model_path = "models/res10_300x300_ssd_iter_140000_fp16.caffemodel"
temp_audio_path = "temp_audio.wav"

# Check if model files exist
if not os.path.exists(prototxt_path) or not os.path.exists(model_path):
    print(f"ERRO: Arquivos de modelo não encontrados em {prototxt_path} ou {model_path}")
    print("Por favor, verifique se os arquivos estão na pasta 'models'")
else:
    # Load DNN model
    try:
        net = cv2.dnn.readNetFromCaffe(prototxt_path, model_path)
    except Exception as e:
        print(f"ERRO ao carregar modelo DNN: {e}")
        print("Verificar se os arquivos de modelo são válidos")

# Lista global para armazenar informações de frames
Frames = []

def voice_activity_detection(audio_frame, sample_rate=16000):
    if WEBRTCVAD_AVAILABLE:
        try:
            return vad.is_speech(audio_frame, sample_rate)
        except Exception as e:
            print(f"Erro na detecção de voz: {e}")
            return False
    else:
        # Fallback: assume sempre que há voz (menos preciso)
        return True

def extract_audio_from_video(video_path, audio_path):
    try:
        audio = AudioSegment.from_file(video_path)
        audio = audio.set_frame_rate(16000).set_channels(1)
        audio.export(audio_path, format="wav")
        return True
    except Exception as e:
        print(f"Erro ao extrair áudio do vídeo: {e}")
        
        # Tentar com FFmpeg se disponível
        ffmpeg_path = shutil.which('ffmpeg')
        if ffmpeg_path:
            try:
                print("Tentando extrair áudio com FFmpeg...")
                cmd = [
                    ffmpeg_path,
                    "-i", video_path,
                    "-vn",  # No video
                    "-acodec", "pcm_s16le",  # PCM 16bit output
                    "-ar", "16000",  # 16kHz sample rate
                    "-ac", "1",  # mono
                    audio_path,
                    "-y"  # Overwrite
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                print("Áudio extraído com sucesso usando FFmpeg")
                return True
            except Exception as e:
                print(f"Erro ao extrair áudio com FFmpeg: {e}")
                return False
        else:
            print("FFmpeg não encontrado. Não é possível extrair o áudio.")
            return False

def process_audio_frame(audio_data, sample_rate=16000, frame_duration_ms=30):
    try:
        if WEBRTCVAD_AVAILABLE:
            n = int(sample_rate * (frame_duration_ms / 1000.0))
            return audio_data[:n], sample_rate
        else:
            # Retorna valores fictícios se webrtcvad não estiver disponível
            return b'', sample_rate
    except Exception as e:
        print(f"Erro ao processar frame de áudio: {e}")
        return b'', sample_rate

def detect_faces_and_speakers(input_video_path, output_video_path):
    # Return Frams:
    global Frames
    Frames = []
    
    try:
        if not os.path.exists(input_video_path):
            print(f"Erro: O arquivo {input_video_path} não existe.")
            return False
        
        # Extract audio from video
        print("Extraindo áudio do vídeo...")
        if not extract_audio_from_video(input_video_path, temp_audio_path):
            print("Aviso: Falha ao extrair áudio. Continuando sem detecção de voz.")
        
        # Initialize video capture
        cap = cv2.VideoCapture(input_video_path)
        if not cap.isOpened():
            print(f"Erro: Não foi possível abrir o vídeo {input_video_path}")
            return False
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # For output video
        out = cv2.VideoWriter(output_video_path, 
                            cv2.VideoWriter_fourcc(*'mp4v'), 
                            fps, 
                            (frame_width, frame_height))
        
        # Open audio file if available
        audio_data = None
        sample_rate = 16000
        audio_frames = []
        
        try:
            if os.path.exists(temp_audio_path) and WEBRTCVAD_AVAILABLE:
                with contextlib.closing(wave.open(temp_audio_path, 'rb')) as wf:
                    sample_rate = wf.getframerate()
                    pcm_data = wf.readframes(wf.getnframes())
                    
                    # Calculate frame size
                    frame_duration_ms = 30  # ms
                    frame_size = int(sample_rate * (frame_duration_ms / 1000.0))
                    
                    # Split audio into frames
                    for i in range(0, len(pcm_data), frame_size * 2):  # *2 for 16-bit PCM
                        audio_frames.append(pcm_data[i:i + frame_size * 2])
        except Exception as e:
            print(f"Erro ao processar arquivo de áudio: {e}")
            print("Continuando sem análise de áudio.")
            audio_frames = []
        
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            found_faces = []
            
            # Detect faces in the frame
            try:
                (h, w) = frame.shape[:2]
                blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0,
                                            (300, 300), (104.0, 177.0, 123.0))
                
                net.setInput(blob)
                detections = net.forward()
                
                # Get audio frame if available
                is_speech = False
                if frame_count < len(audio_frames) and WEBRTCVAD_AVAILABLE:
                    try:
                        audio_frame = audio_frames[frame_count]
                        is_speech = voice_activity_detection(audio_frame, sample_rate)
                    except Exception as e:
                        print(f"Erro na detecção de voz para o frame {frame_count}: {e}")
                
                # Process each detection
                for i in range(0, detections.shape[2]):
                    confidence = detections[0, 0, i, 2]
                    
                    if confidence > 0.5:  # Filter weak detections
                        box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                        (startX, startY, endX, endY) = box.astype("int")
                        
                        # Add text for active speaker if speech detected
                        if is_speech:
                            text = f"Speaking: {confidence:.2f}"
                            y = startY - 10 if startY - 10 > 10 else startY + 10
                            cv2.putText(frame, text, (startX, y),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2)
                        
                        # Draw rectangle around the face
                        cv2.rectangle(frame, (startX, startY), (endX, endY),
                                    (0, 255, 0) if is_speech else (0, 0, 255), 2)
                        
                        found_faces.append((startX, startY, endX - startX, endY - startY))
            
            except Exception as e:
                print(f"Erro ao processar detecções no frame {frame_count}: {e}")
                
            # Store face information for this frame
            if found_faces:
                Frames.append(found_faces[0])  # Using first face
            else:
                # If no faces found, use default values
                Frames.append((0, 0, 100, 100))
            
            # Write frame to output video
            out.write(frame)
            frame_count += 1
            
            # Progress indicator
            if frame_count % 30 == 0:
                print(f"Processados {frame_count} frames")
        
        # Cleanup
        cap.release()
        out.release()
        
        # Try to remove temporary audio file
        try:
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
        except:
            pass
            
        print(f"Detecção concluída. Processados {frame_count} frames.")
        print(f"Informações de {len(Frames)} frames armazenadas.")
        return True
        
    except Exception as e:
        print(f"Erro em detect_faces_and_speakers: {e}")
        return False

if __name__ == "__main__":
    detect_faces_and_speakers()
    print(Frames)
    print(len(Frames))
    print(Frames[1:5])
