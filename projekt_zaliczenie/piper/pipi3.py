import subprocess
import requests
import time
import json
import threading
import argparse
import logging
import queue
from queue import Queue

# ANSI escape codes for colors
RED = "\033[31m"
GREEN = "\033[32m"
BLUE = "\033[34m"
YELLOW = "\033[33m"
RESET = "\033[0m"

# Set up logging
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to start Piper
def start_piper(model_path):
    """Starts the piper service and keeps it running for audio processing."""
    log_file = open('piper_logs.txt', 'a')  # Append to the log file
    piper_command = ['./piper', '--model', model_path, '--output-raw']
    piper_process = subprocess.Popen(piper_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log_file, bufsize=0)
    threading.Thread(target=play_audio, args=(piper_process.stdout,), daemon=True).start()
    return piper_process

# Function to play audio from Piper
def play_audio(pipe):
    """Plays audio from the given pipe using aplay with optimized buffer settings."""
    # Adjust buffer settings as needed: -B (buffer size) and -F (fragment size)
    aplay_command = ['aplay', '-r', '22050', '-f', 'S16_LE', '-t', 'raw', '-B', '2048']
    aplay_process = subprocess.Popen(aplay_command, stdin=pipe, stderr=subprocess.PIPE)  # Redirect stderr for error handling

    for line in aplay_process.stderr:  # Read and print aplay errors
        logging.error(f"aplay Error: {line.decode().strip()}")

# Function to start Ollama server
def start_ollama_server():
    """Starts the ollama server and waits for it to become ready."""
    try:
        server_process = subprocess.Popen(['ollama', 'serve'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(10)  # Wait for the server to start
        return server_process
    except Exception as e:
        logging.error(f"Failed to start Ollama server: {e}")
        return None

# Function to handle streamed JSON response from Ollama
def handle_streamed_json(response_text, piper_process, response_queue):
    """Processes streamed JSON data from Ollama and sends it to Piper."""
    sentence = ""
    for line in response_text.strip().split("\n"):
        if line.strip():
            try:
                json_obj = json.loads(line)
                partial_response = json_obj.get("response", "")
                if partial_response:
                    sentence += partial_response
                    if any(punctuation in partial_response for punctuation in [',', '.', '?', '!']):
                        response_queue.put(sentence.strip())
                        sentence = ""
            except json.JSONDecodeError as e:
                logging.error(f"Error decoding JSON in streamed response: {e}")
    if sentence:
        response_queue.put(sentence.strip())

# Function to get response from Ollama
def get_response_from_ollama(input_text, model_name, piper_process):
    """Sends input to Ollama and handles the response."""
    print(f"{YELLOW}Processing your input...{RESET}")
    url = 'http://localhost:11434/api/generate'
    data = {
        "model": model_name,
        "prompt": input_text,
	"keep_alive": -1,
        "options": {
            "num_ctx": 2048,
        }
    }
    response = requests.post(url, json=data)

    if response.status_code == 200:
        response_queue = Queue()
        threading.Thread(target=handle_streamed_json, args=(response.text, piper_process, response_queue), daemon=True).start()

        print(f"{YELLOW}Ollama: ", end="", flush=True)
        while True:
            try:
                partial_response = response_queue.get(timeout=0.1)
                print(partial_response, end=" ", flush=True)
                piper_process.stdin.write((partial_response + '\n').encode('utf-8'))
                piper_process.stdin.flush()
            except queue.Empty:
                if response_queue.empty():
                    break
                else:
                    continue
        print(f"{RESET}")
    else:
        print(f"{RED}Error: HTTP {response.status_code} - {response.text}{RESET}")
        return 'Error from server.'

# Main function
def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Ollama Conversational Interface')
    parser.add_argument('--piper-model', default='en_GB-cori-medium.onnx', help='Path to the Piper model')
    parser.add_argument('--ollama-model', default='tinydolphin', help='Name of the Ollama model')
    args = parser.parse_args()

    print(f"{BLUE}Starting services...{RESET}")
    piper_process = start_piper(args.piper_model)
    ollama_process = start_ollama_server()

    if not ollama_process or not piper_process:
        print(f"{RED}Failed to start services. Exiting.{RESET}")
        return

    try:
        while True:
            user_input = input(f"{GREEN}You: {RESET}")
            if user_input.lower() == 'exit':
                print(f"{RED}Exiting chat.{RESET}")
                break

            get_response_from_ollama(user_input, args.ollama_model, piper_process)

    finally:
        print(f"{BLUE}Stopping services...{RESET}")
        if ollama_process:
            ollama_process.terminate()
            ollama_process.wait()
        if piper_process:
            piper_process.terminate()

if __name__ == "__main__":
    main()
