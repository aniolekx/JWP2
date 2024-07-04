import os
import subprocess
import threading
import logging
import time
import signal
import argparse

# Ustawienie poziomu logowania
logging.basicConfig(level=logging.INFO)

# Globalne zmienne
running = True
transcript = []

# Funkcje pomocnicze
def signal_handler(sig, frame):
    global running
    print(f"\nSignal {sig} received, exiting.")
    running = False

def handle_user_input(user_input, transcript, process):
    global running
    user_input = user_input.lower()
    if user_input == 'q':
        print("Exiting voice recognition.")
        running = False
    elif user_input == 'e':
        transcript.clear()
        print("\033c", end="")
    else:
        print("Invalid input. Please try again.")

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

def start_voice_recognition(container_name):
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
        print("\nPress 'e' to clear the screen and input buffer, or 'q' to quit.")
        last_input_time = time.time()

        while running:
            command = [
                'docker', 'exec', '-i', container_name,
                'python3', '-u', 'examples/asr.py',
                '--mic', '11',
                '--pipe', pipe_name,
            ]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logging.info("Voice recognition process started")

            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logging.error("Voice recognition process timed out")
                process.terminate()
            except Exception as e:
                logging.error(f"Unexpected error during process execution: {e}")
            finally:
                if process.returncode != 0:
                    logging.error("Voice recognition process exited with an error")
                    running = False
                else:
                    time.sleep(0.1)  # Dodanie opóźnienia 100 ms
                    continue

            try:
                for line in iter(process.stdout.readline, b''):
                    partial_transcript = line.decode('utf-8').strip()
                    if partial_transcript:
                        transcript.append(partial_transcript + " ")
                        print(f"\rYou: {''.join(transcript)}", end="", flush=True)

                for line in iter(process.stderr.readline, b''):
                    logging.error(f"Error: {line.decode('utf-8').strip()}")

                current_time = time.time()
                if current_time - last_input_time >= 1.0:
                    user_input = input()
                    handle_user_input(user_input, transcript, process)
                    last_input_time = current_time

            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                time.sleep(5)

        remove_pipe(pipe_name)

    transcription_thread = threading.Thread(target=transcribe_audio, daemon=True)
    transcription_thread.start()
    transcription_thread.join()

# Funkcja main
def main():
    parser = argparse.ArgumentParser(description='Voice Recognition Script')
    parser.add_argument('--container', default='infallible_roentgen', help='Name of the Docker container')
    args = parser.parse_args()

    container_name = args.container

    start_voice_recognition(container_name)

if __name__ == "__main__":
    main()
