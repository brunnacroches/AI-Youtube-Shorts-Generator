import openai
from dotenv import load_dotenv
import os
import json
import re
import sys
import time

load_dotenv()

# Carregar a chave API do arquivo .env
api_key = os.getenv("OPENAI_API")

if not api_key:
    print("\n⚠️ AVISO: Chave da API OpenAI não encontrada!")
    print("Crie um arquivo .env com o conteúdo:")
    print("OPENAI_API=sua_chave_aqui")
    print("\nVocê pode obter uma chave em: https://platform.openai.com/api-keys")
    

# Função para extrair os tempos de início e fim
def extract_times(json_string, multiple=False):
    try:
        # Limpar a string JSON de possíveis marcadores de código
        json_string = json_string.replace("```json", "").replace("```", "").strip()
        
        # Usar expressões regulares para encontrar a estrutura JSON
        json_match = re.search(r'\[{.*?}\]', json_string, re.DOTALL)
        if json_match:
            json_string = json_match.group(0)
        
        # Analisar a string JSON
        data = json.loads(json_string)
        
        if not data or not isinstance(data, list) or len(data) == 0:
            print("Erro: Dados JSON inválidos ou vazios.")
            return [] if multiple else (0, 0)
        
        # Para múltiplos clipes
        if multiple:
            result = []
            for clip in data:
                try:
                    start_time = float(clip["start"])
                    end_time = float(clip["end"])
                    content = clip.get("content", "")
                    
                    # Validar os tempos
                    if start_time >= end_time:
                        print(f"Aviso: Tempo inválido para o clipe ({start_time} - {end_time}). Ignorando.")
                        continue
                    
                    # Limitar a duração máxima de cada clipe (60 segundos para shorts)
                    if (end_time - start_time) > 60:
                        print(f"Aviso: Clipe muito longo ({end_time - start_time} segundos). Limitando a 60 segundos.")
                        end_time = start_time + 60
                    
                    result.append((int(start_time), int(end_time), content))
                except (KeyError, ValueError) as e:
                    print(f"Aviso: Erro ao processar um clipe: {e}")
            
            # Ordenar por tempo de início
            result.sort(key=lambda x: x[0])
            return result
        
        # Para único clipe (compatibilidade)
        else:
            # Extrair tempos de início e fim como floats
            try:
                start_time = float(data[0]["start"])
                end_time = float(data[0]["end"])
            except (KeyError, ValueError):
                print("Erro: Os campos 'start' ou 'end' não foram encontrados ou não são números válidos.")
                return 0, 0
                
            # Converter para inteiros
            start_time_int = int(start_time)
            end_time_int = int(end_time)
            
            # Validar os tempos
            if start_time_int >= end_time_int:
                print(f"Aviso: O tempo de início ({start_time_int}) é maior ou igual ao tempo de fim ({end_time_int}).")
                return 0, 0
                
            # Garantir que o destaque não seja muito longo (limite de 60 segundos para shorts)
            if (end_time_int - start_time_int) > 60:
                print(f"Aviso: O destaque é muito longo ({end_time_int - start_time_int} segundos). Limitando a 60 segundos.")
                end_time_int = start_time_int + 60
                
            return start_time_int, end_time_int
    except Exception as e:
        print(f"Erro ao extrair tempos: {e}")
        print(f"String JSON problemática: {json_string}")
        return [] if multiple else (0, 0)


def create_prompt(num_clips=1):
    if num_clips <= 1:
        return """
Com base na transcrição fornecida pelo usuário com os tempos de início e fim, destaque a parte principal em menos de 1 minuto que pode ser convertida diretamente em um short. Faça o destaque de forma interessante e também mantenha as marcações de tempo para o início e fim do clipe.

Siga este formato e retorne em JSON válido:
[{
  "start": "Tempo de início do clipe em segundos",
  "content": "Texto do destaque",
  "end": "Tempo de fim do clipe em segundos"
}]

RETORNE APENAS O JSON VÁLIDO. Nenhuma explicação adicional.
"""
    else:
        return f"""
Com base na transcrição fornecida pelo usuário com os tempos de início e fim, identifique EXATAMENTE {num_clips} partes interessantes que podem ser convertidas em shorts. Cada uma deve ter menos de 1 minuto de duração.

Os clipes devem:
1. Ser distintos um do outro (momentos diferentes do vídeo)
2. Ter conteúdo interessante e envolvente
3. Funcionar bem como shorts independentes

Siga este formato e retorne em JSON válido:
[
  {{
    "start": "Tempo de início do primeiro clipe em segundos",
    "content": "Texto do primeiro destaque",
    "end": "Tempo de fim do primeiro clipe em segundos"
  }},
  {{
    "start": "Tempo de início do segundo clipe em segundos",
    "content": "Texto do segundo destaque",
    "end": "Tempo de fim do segundo clipe em segundos"
  }},
  ...e assim por diante para todos os {num_clips} clipes
]

RETORNE APENAS O JSON VÁLIDO com EXATAMENTE {num_clips} clipes. Nenhuma explicação adicional.
"""


# Prompt de exemplo para uso no modo teste
User = """
0.00 - 10.00: Olá, hoje vamos falar sobre inteligência artificial.
10.00 - 20.00: A IA está mudando o mundo de diversas formas.
20.00 - 30.00: Vamos ver alguns exemplos práticos disso.
30.00 - 40.00: Este é um exemplo realmente impressionante de como a IA pode resolver problemas complexos.
40.00 - 50.00: A velocidade de processamento é incrível!
50.00 - 60.00: Isso tem aplicações em várias áreas como medicina e finanças.
60.00 - 70.00: Espero que você tenha gostado deste vídeo.
"""


def GetMultipleHighlights(Transcription, num_clips=1, max_retries=3):
    """Obtém múltiplos destaques da transcrição."""
    print(f"Identificando {num_clips} destaques da transcrição...")
    
    if not api_key:
        print("Erro: Chave da API OpenAI não configurada.")
        return []
        
    if not Transcription or len(Transcription.strip()) < 10:
        print("Erro: Transcrição muito curta ou vazia.")
        return []
    
    # Criar cliente OpenAI com a nova sintaxe
    client = openai.OpenAI(api_key=api_key)
    
    # Criar o prompt baseado no número de clipes
    system_prompt = create_prompt(num_clips)
    
    for attempt in range(max_retries):
        try:
            print(f"Tentativa {attempt+1}/{max_retries} de identificar {num_clips} destaques...")
            
            # Tentar primeiro com gpt-4o
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-2024-05-13",
                    temperature=0.7,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": Transcription},
                    ]
                )
            except Exception as e:
                print(f"Erro ao usar gpt-4o: {e}")
                print("Tentando com modelo alternativo gpt-3.5-turbo...")
                
                # Fallback para gpt-3.5-turbo se gpt-4o falhar
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    temperature=0.7,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": Transcription},
                    ]
                )

            # Obter a resposta e processar o JSON
            json_string = response.choices[0].message.content
            print("Resposta recebida da API.")
            
            # Extrair os tempos
            highlights = extract_times(json_string, multiple=True)
            
            if not highlights:
                print(f"Aviso: Não foi possível extrair tempos válidos. Tentativa {attempt+1}/{max_retries}")
                time.sleep(2)  # Esperar antes de tentar novamente
                continue
                
            if len(highlights) < num_clips:
                print(f"Aviso: Apenas {len(highlights)} destaques válidos encontrados (pedimos {num_clips}).")
                
            # Destaques encontrados com sucesso
            print(f"Total de {len(highlights)} destaques identificados:")
            for i, (start, end, content) in enumerate(highlights):
                print(f"  Clip {i+1}: {start}s até {end}s (duração: {end-start}s)")
            
            return highlights
            
        except Exception as e:
            print(f"Erro durante a chamada da API: {e}")
            print(f"Tentativa {attempt+1}/{max_retries} falhou. Tentando novamente em 3 segundos...")
            time.sleep(3)
    
    # Se todas as tentativas falharam, perguntar ao usuário se deseja tentar novamente
    print("Todas as tentativas automáticas falharam.")
    Ask = input("Deseja tentar novamente? (s/n): ").lower()
    if Ask == "s":
        return GetMultipleHighlights(Transcription, num_clips, max_retries)
    return []


def GetHighlight(Transcription, max_retries=3):
    """Função original para compatibilidade - obtém um único destaque"""
    print("Identificando o destaque principal da transcrição...")
    
    # Usar a nova função e extrair apenas o primeiro resultado
    highlights = GetMultipleHighlights(Transcription, 1, max_retries)
    
    if not highlights:
        return 0, 0
    
    # Retornar apenas o início e fim do primeiro destaque para compatibilidade
    return highlights[0][0], highlights[0][1]


if __name__ == "__main__":
    # Se for executado diretamente, testar a funcionalidade de múltiplos clipes
    num_clips = int(input("Quantos clipes deseja extrair? "))
    highlights = GetMultipleHighlights(User, num_clips)
    
    if highlights:
        print("\nDestaques encontrados:")
        for i, (start, end, content) in enumerate(highlights):
            print(f"\nClip {i+1}: {start}s - {end}s (duração: {end-start}s)")
            print(f"Conteúdo: {content[:100]}...")
    else:
        print("\nNão foi possível identificar destaques válidos.")
