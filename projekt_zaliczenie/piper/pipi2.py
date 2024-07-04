import subprocess
import requests
import time
import json
import threading

# ANSI escape codes for colors
RED = "\033[31m"
GREEN = "\033[32m"
BLUE = "\033[34m"
YELLOW = "\033[33m"
RESET = "\033[0m"

def start_piper():
    """Starts the piper service and keeps it running for audio processing."""
    log_file = open('piper_logs.txt', 'a')  # Append to the log file
    piper_command = ['./piper', '--model', 'en_GB-cori-medium.onnx', '--output-raw']  # Use the correct model name
    piper_process = subprocess.Popen(piper_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log_file, bufsize=0)
    threading.Thread(target=play_audio, args=(piper_process.stdout,), daemon=True).start()
    return piper_process

def play_audio(pipe):
    """Plays audio from the given pipe using aplay with optimized buffer settings."""
    # Adjust buffer settings as needed: -B (buffer size) and -F (fragment size)
    aplay_command = ['aplay', '-r', '22050', '-f', 'S16_LE', '-t', 'raw', '-B', '2048']
    aplay_process = subprocess.Popen(aplay_command, stdin=pipe, stderr=subprocess.PIPE)  # Redirect stderr for error handling
    for line in aplay_process.stderr:  # Read and print aplay errors
        print(f"{RED}aplay Error: {line.decode().strip()}{RESET}")

def start_ollama_server():
    """Starts the ollama server and waits for it to become ready."""
    try:
        server_process = subprocess.Popen(['ollama', 'serve'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(10)
        return server_process
    except Exception as e:
        print(f"{RED}Failed to start Ollama server: {e}{RESET}")
        return None

def handle_streamed_json(response_text):
    """Processes streamed JSON data from Ollama."""
    full_response = ""
    for line in response_text.strip().split("\n"):
        if line.strip():
            try:
                json_obj = json.loads(line)
                full_response += json_obj.get("response", "")
                if json_obj.get("done", False):
                    break
            except json.JSONDecodeError as e:
                print(f"{RED}Error decoding JSON in streamed response: {e}{RESET}")
                return None
    return full_response

def get_response_from_ollama(input_text):
    """Sends input to Ollama and handles the response."""
    print(f"{YELLOW}Processing your input...{RESET}")
    url = 'http://localhost:11434/api/generate'
    data = {
        "model": "tinydolphin",
        "prompt": input_text,
	"keep_alive": -1,
        "options": {
            "num_ctx": 2048
        }
    }
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return handle_streamed_json(response.text)
    else:
        print(f"{RED}Error: HTTP {response.status_code} - {response.text}{RESET}")
        return 'Error from server.'

def main():
    print(f"{BLUE}Starting services...{RESET}")
    piper_process = start_piper()
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

            response_data = get_response_from_ollama(user_input)
            if response_data:
                print(f"{YELLOW}Ollama: {response_data}{RESET}")
                piper_process.stdin.write((response_data + '\n').encode('utf-8'))
                piper_process.stdin.flush()
            else:
                print(f"{RED}No valid response or failed to receive data.{RESET}")
    finally:
        print(f"{BLUE}Stopping services...{RESET}")
        if ollama_process:
            ollama_process.terminate()
            ollama_process.wait()
        if piper_process:
            piper_process.terminate()

if __name__ == "__main__":
    main()

