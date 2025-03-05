from Components.YoutubeDownloader import download_youtube_video
from Components.Edit import extractAudio, crop_video
from Components.Transcription import transcribeAudio
from Components.LanguageTasks import GetHighlight, GetMultipleHighlights
from Components.FaceCrop import crop_to_vertical, combine_videos
import os
import sys
import time

def check_prerequisites():
    missing = []
    
    # Verificar se os diretórios necessários existem
    if not os.path.exists("videos"):
        try:
            os.makedirs("videos")
            print("Criado diretório 'videos'")
        except:
            missing.append("Não foi possível criar o diretório 'videos'")
    
    # Verificar se existe um diretório para outputs
    if not os.path.exists("outputs"):
        try:
            os.makedirs("outputs")
            print("Criado diretório 'outputs'")
        except:
            missing.append("Não foi possível criar o diretório 'outputs'")
    
    # Verificar se os arquivos de modelo existem
    if not os.path.exists("models/deploy.prototxt") or not os.path.exists("models/res10_300x300_ssd_iter_140000_fp16.caffemodel"):
        missing.append("Arquivos de modelo (na pasta 'models')")
    
    if missing:
        print("\n⚠️ Aviso: Os seguintes pré-requisitos estão faltando:")
        for item in missing:
            print(f"  - {item}")
        print("\nVocê pode continuar, mas algumas funcionalidades podem não funcionar corretamente.")
        input("Pressione Enter para continuar...")
    
    return len(missing) == 0

def process_single_highlight(Vid, Audio, transcriptions, start, end, index=1):
    """Processa um único destaque e retorna o caminho do arquivo final."""
    try:
        # Definir nomes de arquivos para este clipe
        Output = f"outputs/Out_{index}.mp4"
        croped = f"outputs/Croped_{index}.mp4"
        final_output = f"outputs/Final_{index}.mp4"
        
        # Cortar vídeo
        print(f"\nProcessando Clipe {index} - Cortando o vídeo de {start}s até {end}s...")
        if not crop_video(Vid, Output, start, end):
            print(f"❌ Erro: Não foi possível cortar o vídeo para o clipe {index}.")
            return None
            
        print(f"✅ Vídeo cortado salvo em: {Output}")

        # Corte vertical
        print(f"Criando corte vertical (identificando faces) para o clipe {index}...")
        if not crop_to_vertical(Output, croped):
            print(f"❌ Erro: Não foi possível criar o corte vertical para o clipe {index}.")
            return None
            
        print(f"✅ Corte vertical salvo em: {croped}")

        # Combinar vídeos
        print(f"Combinando vídeo e áudio para o resultado final do clipe {index}...")
        if not combine_videos(Output, croped, final_output):
            print(f"❌ Erro: Não foi possível combinar os vídeos para o clipe {index}.")
            return None
            
        print(f"🎬 Clipe {index} concluído: {final_output}")
        print(f"   Duração: {end-start:.1f} segundos")
        
        return final_output
    except Exception as e:
        print(f"Erro ao processar o clipe {index}: {e}")
        return None

def main():
    print("\n=== AI YouTube Shorts Generator ===\n")
    print("Este programa baixa um vídeo do YouTube, identifica os destaques, e cria")
    print("vídeos verticais otimizados para plataformas de shorts.")
    print("\nPré-requisitos:")
    print("- Python 3.7+")
    print("- FFmpeg (recomendado)")
    print("- Modelos de detecção facial\n")
    
    # Verificar pré-requisitos
    check_prerequisites()
    
    # Entrada do URL do YouTube
    try:
        url = input("\nDigite o URL do vídeo do YouTube: ")
        print("\nBaixando vídeo do YouTube...")
        Vid = download_youtube_video(url)
        
        if not Vid:
            print("\n❌ Erro: Não foi possível baixar o vídeo.")
            return
            
        Vid = Vid.replace(".webm", ".mp4")
        print(f"\n✅ Vídeo baixado com sucesso em: {Vid}")

        # Extrair áudio
        print("\nExtraindo áudio do vídeo...")
        Audio = extractAudio(Vid)
        
        if not Audio:
            print("\n❌ Erro: Não foi possível extrair o áudio do vídeo.")
            return
            
        print(f"✅ Áudio extraído em: {Audio}")

        # Transcrever áudio
        print("\nTranscrevendo áudio (isso pode levar alguns minutos)...")
        start_time = time.time()
        transcriptions = transcribeAudio(Audio)
        
        if not transcriptions or len(transcriptions) == 0:
            print("\n❌ Erro: Não foi possível transcrever o áudio.")
            return
            
        print(f"✅ Transcrição concluída em {time.time() - start_time:.1f} segundos")

        # Preparar texto da transcrição
        TransText = ""
        for text, start, end in transcriptions:
            TransText += (f"{start} - {end}: {text}\n")

        # Perguntar ao usuário quantas partes ele deseja
        while True:
            try:
                num_parts = input("\nEm quantas partes você deseja dividir o vídeo? (1-5): ")
                num_parts = int(num_parts)
                if 1 <= num_parts <= 5:
                    break
                else:
                    print("Por favor, escolha um número entre 1 e 5.")
            except ValueError:
                print("Por favor, digite um número válido.")
        
        # Processar de acordo com o número de partes
        if num_parts == 1:
            # Modo original - um único destaque
            print("\nIdentificando o momento de destaque...")
            start, end = GetHighlight(TransText)
            
            if start == 0 and end == 0:
                print("\n❌ Erro: Não foi possível identificar destaques no vídeo.")
                return
                
            print(f"✅ Destaque identificado: {start}s até {end}s")
            
            # Processar o único destaque
            final_path = process_single_highlight(Vid, Audio, transcriptions, start, end)
            
            if final_path:
                print(f"\n🎉 Processo concluído com sucesso!")
                print(f"📱 Seu vídeo vertical está pronto em: {final_path}")
            
        else:
            # Modo múltiplos destaques
            print(f"\nIdentificando {num_parts} momentos de destaque...")
            highlights = GetMultipleHighlights(TransText, num_parts)
            
            if not highlights:
                print("\n❌ Erro: Não foi possível identificar destaques no vídeo.")
                return
            
            print(f"✅ {len(highlights)} destaques identificados para processamento")
            
            # Processar cada destaque
            successful_clips = []
            for idx, (start, end, content) in enumerate(highlights):
                print(f"\n--- Processando Clipe {idx+1}/{len(highlights)} ---")
                print(f"Intervalo: {start}s - {end}s (Duração: {end-start}s)")
                print(f"Conteúdo: {content[:100]}...")
                
                final_path = process_single_highlight(Vid, Audio, transcriptions, start, end, idx+1)
                if final_path:
                    successful_clips.append(final_path)
            
            # Resumo final
            if successful_clips:
                print(f"\n🎉 Processo concluído! {len(successful_clips)}/{len(highlights)} clipes gerados com sucesso!")
                print("\nClipes gerados:")
                for idx, path in enumerate(successful_clips):
                    print(f"  📱 Clipe {idx+1}: {path}")
            else:
                print("\n❌ Nenhum clipe foi gerado com sucesso.")

    except KeyboardInterrupt:
        print("\n\nOperação cancelada pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()