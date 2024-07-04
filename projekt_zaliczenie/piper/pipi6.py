import subprocess  # Import modułu subprocess do uruchamiania poleceń zewnętrznych
import requests  # Import modułu requests do wysyłania żądań HTTP
import time  # Import modułu time do dodawania opóźnień
import json  # Import modułu json do obsługi danych JSON
import threading  # Import modułu threading do równoległego wykonywania zadań
import argparse  # Import modułu argparse do parsowania argumentów wiersza poleceń
import logging  # Import modułu logging do rejestrowania komunikatów
from queue import Queue  # Import klasy Queue z modułu queue do komunikacji międzywątkowej
import os  # Import modułu os do obsługi systemu plików
import signal  # Import modułu signal do obsługi sygnałów

# Kody ANSI do kolorowania tekstu
RED = "\033[31m"  # Definiuje kod ANSI dla koloru czerwonego
GREEN = "\033[32m"  # Definiuje kod ANSI dla koloru zielonego
BLUE = "\033[34m"  # Definiuje kod ANSI dla koloru niebieskiego
YELLOW = "\033[33m"  # Definiuje kod ANSI dla koloru żółtego
RESET = "\033[0m"  # Definiuje kod ANSI do resetowania koloru

# Konfiguracja rejestrowania
logging.basicConfig(level=logging.INFO)

# Globalne zmienne
running = True
transcript = []

# Funkcje pomocnicze
def signal_handler(sig, frame):
    global running
    print(f"\nSignal {sig} received, exiting.")
    running = False

def handle_user_input(user_input, transcript, process, transcript_queue):
    global running
    user_input = user_input.lower()
    if user_input == 'q':
        print(f"{RED}Exiting voice recognition.{RESET}")
        running = False
    elif user_input == 'e':
        transcript.clear()
        print(f"\033c", end="")
    elif user_input == 'w':
        transcript_queue.put(''.join(transcript))
        transcript.clear()
        print(f"\033c", end="")
        send_control_command('pause', pipe_name)
        process.wait()
        send_control_command('resume', pipe_name)
    else:
        print(f"{RED}Invalid input. Please try again.{RESET}")

def send_control_command(command, pipe_name):
    with open(pipe_name, 'w') as pipe:
        pipe.write(command + '\n')
    logging.info(f"Command sent: {command}")
    time.sleep(0.1)

def remove_pipe(pipe_name):
    try:
        os.remove(pipe_name)
        logging.info("Named pipe removed")
    except OSError as e:
        logging.error(f"Error removing named pipe: {e}")

# Funkcja do uruchamiania Pipera
def start_piper(model_path):
    """Uruchamia usługę Piper i utrzymuje ją w stanie aktywnym do przetwarzania dźwięku."""
    log_file = open('piper_logs.txt', 'a')  # Otwiera plik dziennika w trybie dołączania
    piper_command = ['./piper', '--model', model_path, '--output-raw']  # Definiuje polecenie do uruchomienia Pipera z określonym modelem i surowym wyjściem
    piper_process = subprocess.Popen(piper_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log_file, bufsize=0)  # Uruchamia proces Pipera z potokami wejściowymi, wyjściowymi i błędów
    threading.Thread(target=play_audio, args=(piper_process.stdout,), daemon=True).start()  # Uruchamia oddzielny wątek do odtwarzania dźwięku z wyjścia Pipera
    return piper_process  # Zwraca obiekt procesu Pipera

# Funkcja do odtwarzania dźwięku z Pipera
def play_audio(pipe):
    """Odtwarza dźwięk z podanego potoku za pomocą aplay z optymalnymi ustawieniami bufora."""
    aplay_command = ['aplay', '-r', '22050', '-f', 'S16_LE', '-t', 'raw', '-B', '2048']  # Definiuje polecenie do odtwarzania dźwięku za pomocą aplay z określonymi ustawieniami
    aplay_process = subprocess.Popen(aplay_command, stdin=pipe, stderr=subprocess.PIPE)  # Uruchamia proces aplay z potokiem wejściowym i potokiem błędów

    for line in aplay_process.stderr:  # Iteruje po liniach wyjścia błędów aplay
        logging.error(f"aplay Error: {line.decode().strip()}")  # Rejestruje wszelkie błędy z aplay

# Funkcja do uruchamiania serwera Ollama
def start_ollama_server():
    """Uruchamia serwer Ollama i czeka na jego gotowość."""
    try:
        server_process = subprocess.Popen(['ollama', 'serve'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)  # Uruchamia proces serwera Ollama z potokami wyjściowymi i błędów
        time.sleep(10)  # Czeka 10 sekund, aby umożliwić uruchomienie serwera
        return server_process  # Zwraca obiekt procesu serwera
    except Exception as e:  # Przechwytuje wszelkie wyjątki, które wystąpią
        logging.error(f"Failed to start Ollama server: {e}")  # Rejestruje komunikat o błędzie
        return None  # Zwraca None, aby wskazać niepowodzenie

# Funkcja do obsługi strumieniowej odpowiedzi JSON z Ollama
def handle_streamed_json(response, piper_process):
    """Przetwarza strumieniowe dane JSON z Ollama i wysyła je do Pipera."""
    try:
        sentence = ""  # Inicjalizuje pusty ciąg zdania
        for chunk in response.iter_lines(decode_unicode=True):  # Iteruje po liniach w odpowiedzi strumieniowej
            if chunk:  # Jeśli fragment nie jest pusty
                try:
                    json_data = json.loads(chunk)  # Analizuje dane JSON z fragmentu
                    partial_response = json_data.get("response", "")  # Pobiera częściową odpowiedź z danych JSON
                    done = json_data.get("done", False)  # Pobiera flagę zakończenia z danych JSON
                    if partial_response:  # Jeśli istnieje częściowa odpowiedź
                        sentence += partial_response  # Dołącza częściową odpowiedź do zdania
                        if any(punctuation in partial_response for punctuation in ['.', '?', '!', ',', ';', ':']):  # Jeśli częściowa odpowiedź zawiera jakikolwiek znak interpunkcyjny
                            piper_process.stdin.write((sentence + '\n').encode('utf-8'))  # Zapisuje zdanie do potoku wejściowego Pipera
                            piper_process.stdin.flush()  # Opróżnia potok wejściowy, aby upewnić się, że dane zostały wysłane
                            print(sentence, end="", flush=True)  # Wyświetla zdanie bez nowej linii
                            sentence = ""  # Resetuje ciąg zdania
                    if done:  # Jeśli odpowiedź jest zakończona
                        print()  # Wyświetla nową linię po zakończeniu odpowiedzi
                except json.JSONDecodeError as e:  # Przechwytuje błędy dekodowania JSON
                    logging.error(f"Error decoding JSON in streamed response: {e}")  # Rejestruje komunikat o błędzie
    except Exception as e:  # Przechwytuje wszelkie inne wyjątki, które wystąpią
        logging.error(f"Error handling streamed JSON: {e}")  # Rejestruje komunikat o błędzie

# Funkcja do uzyskania odpowiedzi z Ollama
def get_response_from_ollama(input_text, model_name, piper_process):
    """Wysyła dane wejściowe do Ollama i obsługuje odpowiedź."""
    print(f"{YELLOW}Processing your input...{RESET}")  # Wyświetla komunikat wskazujący, że dane wejściowe są przetwarzane
    url = 'http://localhost:11434/api/generate'  # Definiuje adres URL dla punktu końcowego API Ollama
    data = {
        "model": model_name,  # Określa nazwę modelu
        "prompt": input_text,  # Określa tekst wejściowy jako prompt
        "stream": True,  # Włącza tryb strumieniowy
        "options": {
            "num_ctx": 2048,  # Określa liczbę tokenów kontekstowych
        }
    }
    try:
        response = requests.post(url, json=data, stream=True)  # Wysyła żądanie POST do API Ollama z danymi wejściowymi i włącza strumieniowanie
        response.raise_for_status()  # Zgłasza wyjątek, jeśli kod statusu odpowiedzi wskazuje na błąd

        print(f"{YELLOW}Ollama: {RESET}", end="", flush=True)  # Wyświetla komunikat wskazujący, że Ollama odpowiada
        handle_streamed_json(response, piper_process)  # Obsługuje strumieniową odpowiedź JSON z Ollama i wysyła ją do Pipera
    except requests.exceptions.RequestException as e:  # Przechwytuje wyjątki związane z żądaniami
        logging.error(f"Error sending request to Ollama: {e}")  # Rejestruje komunikat o błędzie
        print(f"{RED}Error sending request to Ollama: {e}{RESET}")  # Wyświetla komunikat o błędzie w konsoli
        return 'Error from server.'  # Zwraca komunikat o błędzie
    except Exception as e:  # Przechwytuje wszelkie inne wyjątki, które wystąpią
        logging.error(f"Unexpected error: {e}")  # Rejestruje komunikat o błędzie
        print(f"{RED}Unexpected error: {e}{RESET}")  # Wyświetla komunikat o błędzie w konsoli
        return 'Unexpected error occurred.'  # Zwraca komunikat o błędzie

# Funkcja do uruchamiania rozpoznawania mowy
def start_voice_recognition(args, piper_process, transcript_queue):
    global running, transcript

    pipe_name = 'voice_recognition_pipe'
    if not os.path.exists(pipe_name):
        try:
            os.mkfifo(pipe_name)
            logging.info("Named pipe created")
        except OSError as e:
            logging.error(f"Error creating named pipe: {e}")
            return

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    def transcribe_audio():
        global running, transcript

        print(f"\n{GREEN}Press 'w' to send the transcript, 'e' to clear the screen and input buffer, or 'q' to quit: {RESET}")

        while running:
            command = [
                'docker', 'exec', '-i', 'charming_benz',
                'python3', '-u', 'examples/asr.py',
                '--mic', '11',
                '--pipe', pipe_name,
            ]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logging.info("Voice recognition process started")

            try:
                process.wait(timeout=5)
                break  # Dodanie `break` do zakończenia pętli po zakończeniu procesu
            except subprocess.TimeoutExpired:
                logging.error("Voice recognition process timed out")
                process.terminate()
                continue

            try:
                for line in iter(process.stdout.readline, b''):
                    partial_transcript = line.decode('utf-8').strip()
                    if partial_transcript:
                        transcript.append(partial_transcript + " ")
                        print(f"\rYou: {''.join(transcript)}", end="", flush=True)

                for line in iter(process.stderr.readline, b''):
                    logging.error(f"Error: {line.decode('utf-8').strip()}")

                if transcript:
                    user_input = input()
                    handle_user_input(user_input, transcript, process, transcript_queue)

            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                time.sleep(5)

    remove_pipe(pipe_name)

    transcription_thread = threading.Thread(target=transcribe_audio, daemon=True)
    transcription_thread.start()
    transcription_thread.join()

# Funkcja główna
def main():
    parser = argparse.ArgumentParser(description='Ollama Conversational Interface')  # Tworzy parser argumentów z opisem
    parser.add_argument('--piper-model', default='en_GB-cori-medium.onnx', help='Path to the Piper model')  # Dodaje argument dla ścieżki modelu Piper
    parser.add_argument('--ollama-model', default='tinydolphin', help='Name of the Ollama model')  # Dodaje argument dla nazwy modelu Ollama
    args = parser.parse_args()  # Parsuje argumenty wiersza poleceń

    print(f"{BLUE}Starting other services...{RESET}")  # Wyświetla komunikat wskazujący, że inne usługi są uruchamiane
    piper_process = start_piper(args.piper_model)  # Uruchamia proces Pipera z określonym modelem
    ollama_process = start_ollama_server()  # Uruchamia proces serwera Ollama

    transcript_queue = Queue()  # Tworzy kolejkę do przechowywania transkrypcji

    # Uruchamia rozpoznawanie mowy w oddzielnym wątku
    start_voice_recognition(args, piper_process, transcript_queue)

    if not ollama_process or not piper_process:  # Jeśli serwer Ollama lub proces Pipera nie zostały uruchomione
        print(f"{RED}Failed to start services. Exiting.{RESET}")  # Wyświetla komunikat o błędzie wskazujący na niepowodzenie
        return  # Kończy działanie programu

    try:
        while running:
            transcript = transcript_queue.get()
            if transcript:
                print(f"\nTranscribed: {transcript}")
                get_response_from_ollama(transcript, args.ollama_model, piper_process)
                time.sleep(1)  # Dodaje opóźnienie 1 sekundy, aby zmniejszyć obciążenie systemu
    finally:
        print(f"{BLUE}Stopping services...{RESET}")  # Wyświetla komunikat wskazujący, że usługi są zatrzymywane
        if ollama_process:  # Jeśli istnieje proces serw
            ollama_process.terminate()  # Kończy proces serwera Ollama
            ollama_process.wait()  # Czeka na zakończenie procesu
        if piper_process:  # Jeśli istnieje proces Pipera
            piper_process.terminate()  # Kończy proces Pipera


if __name__ == "__main__":
    main()  # Wywołuje funkcję główną
