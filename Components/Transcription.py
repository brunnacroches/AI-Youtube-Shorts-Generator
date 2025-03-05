from faster_whisper import WhisperModel
import torch
import os
import sys
import openai
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Carregar a chave API
api_key = os.getenv("OPENAI_API")

# Controla qual método de transcrição usar
# "local" para faster-whisper local ou "api" para OpenAI API
TRANSCRIPTION_METHOD = "api"  # Mude para "api"

def transcribeAudio(audio_path):
    try:
        if not os.path.exists(audio_path):
            print(f"Erro: O arquivo de áudio {audio_path} não existe.")
            return []
            
        print("Iniciando transcrição do áudio...")
        print("Este processo pode levar alguns minutos dependendo do tamanho do arquivo.")
        
        # Método 1: Usar a API OpenAI Whisper (mais precisa, requer conexão com internet)
        if TRANSCRIPTION_METHOD == "api":
            return transcribe_with_openai_api(audio_path)
        
        # Método 2: Usar faster-whisper localmente (sem requisito de internet)
        else:
            return transcribe_locally(audio_path)
            
    except Exception as e:
        print(f"Erro de transcrição: {e}")
        return []

def transcribe_with_openai_api(audio_path):
    """Transcreve áudio usando a API OpenAI Whisper"""
    try:
        print("Usando API OpenAI Whisper para transcrição...")
        
        # Verificar se a chave API está configurada
        if not api_key:
            print("Erro: Chave da API OpenAI não encontrada no arquivo .env")
            print("Alternando para transcrição local...")
            return transcribe_locally(audio_path)
        
        # Configurar cliente OpenAI com a nova sintaxe
        client = openai.OpenAI(api_key=api_key)
        
        # Abrir o arquivo de áudio
        with open(audio_path, "rb") as audio_file:
            # Chamar a API
            print("Enviando áudio para a API OpenAI Whisper...")
            try:
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json"
                )
                
                print("Transcrição recebida da API!")
                
                # Processar resposta
                if hasattr(response, 'segments'):
                    segments = response.segments
                    extracted_texts = [[segment.text, segment.start, segment.end] for segment in segments]
                else:
                    # Extrair apenas o texto completo se não houver segmentos
                    text = response.text
                    print(f"Texto recebido: {text[:50]}...")
                    # Criar segmentos artificiais de 10 segundos para o texto completo
                    words = text.split()
                    segment_length = 20  # palavras por segmento
                    segments = []
                    
                    for i in range(0, len(words), segment_length):
                        segment_text = " ".join(words[i:i+segment_length])
                        start_time = i/segment_length * 10  # 10 segundos por segmento
                        end_time = start_time + 10
                        segments.append([segment_text, start_time, end_time])
                    
                    extracted_texts = segments
                
                print(f"Transcrição via API concluída: {len(extracted_texts)} segmentos")
                return extracted_texts
                
            except Exception as e:
                print(f"Erro específico na API Whisper: {e}")
                print("Tentando método alternativo...")
                # Tentar com formato diferente
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
                
                # Resposta simples sem segmentos
                text = response.text
                print(f"Texto recebido (formato simples): {text[:50]}...")
                # Criar segmentos artificiais
                words = text.split()
                segments = []
                
                chunk_size = len(words) // 5  # Dividir em 5 partes aproximadamente
                if chunk_size < 5:
                    chunk_size = 5
                
                for i in range(0, len(words), chunk_size):
                    segment_text = " ".join(words[i:i+chunk_size])
                    start_time = i/len(words) * 60  # Estimar 60 segundos para o áudio completo
                    end_time = (i+chunk_size)/len(words) * 60
                    segments.append([segment_text, start_time, end_time])
                
                print(f"Transcrição processada: {len(segments)} segmentos")
                return segments
        
    except Exception as e:
        print(f"Erro na transcrição via API: {e}")
        print("Alternando para transcrição local...")
        return transcribe_locally(audio_path)

def transcribe_locally(audio_path):
    """Transcreve áudio localmente usando faster-whisper"""
    try:
        # Verificar se CUDA está disponível
        Device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Usando dispositivo: {Device}")
        
        # Carregar modelo
        try:
            # Você pode alterar o tamanho do modelo conforme necessário:
            # - "tiny.en" (mais rápido, menos preciso)
            # - "base.en" (equilíbrio entre velocidade e precisão)
            # - "small.en" (mais preciso, mais lento)
            model_size = "tiny.en"  # Modelo mais leve e rápido para CPUs
            print(f"Carregando modelo {model_size}...")
            model = WhisperModel(model_size, device=Device)
            print(f"Modelo '{model_size}' carregado com sucesso")
        except Exception as e:
            print(f"Erro ao carregar o modelo: {e}")
            print("Tentando usar o modelo 'tiny' como alternativa...")
            try:
                model = WhisperModel("tiny", device="cpu")
                print("Modelo 'tiny' carregado com sucesso")
            except Exception as e2:
                print(f"Erro ao carregar modelo alternativo: {e2}")
                return []
        
        # Realizar transcrição
        try:
            print("Processando áudio... (Isto pode levar algum tempo)")
            segments, info = model.transcribe(
                audio=audio_path, 
                beam_size=5, 
                language="en", 
                max_new_tokens=128, 
                condition_on_previous_text=False
            )
            segments = list(segments)
            
            if not segments:
                print("Aviso: Nenhum segmento transcrito foi encontrado.")
                return []
                
            print(f"Transcrição concluída. {len(segments)} segmentos encontrados.")
            
            # Extrair informações dos segmentos
            extracted_texts = [[segment.text, segment.start, segment.end] for segment in segments]
            return extracted_texts
            
        except Exception as e:
            print(f"Erro durante a transcrição: {e}")
            return []
            
    except Exception as e:
        print(f"Erro na transcrição local: {e}")
        return []

if __name__ == "__main__":
    audio_path = "audio.wav"
    
    if not os.path.exists(audio_path):
        print(f"Erro: O arquivo {audio_path} não existe.")
        sys.exit(1)
        
    transcriptions = transcribeAudio(audio_path)
    
    if not transcriptions:
        print("Nenhuma transcrição encontrada.")
        sys.exit(1)
        
    print(f"Transcrição concluída. {len(transcriptions)} segmentos encontrados.")
    
    TransText = ""
    for text, start, end in transcriptions:
        TransText += (f"{start:.2f} - {end:.2f}: {text}\n")
        
    print("\nResultado da transcrição:")
    print("-" * 40)
    print(TransText)
    print("-" * 40)