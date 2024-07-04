import time
import threading
import numpy as np
import whisper
import sounddevice as sd
import subprocess
from queue import Queue
from rich.console import Console
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.prompts import PromptTemplate
from langchain_community.llms import Ollama

console = Console()
stt = whisper.load_model("base.en")

template = """
You are a helpful and friendly AI assistant. You are polite, respectful, and aim to provide concise responses of less 
than 20 words.

The conversation transcript is as follows:
{history}

And here is the user's follow-up: {input}

Your response:
"""
PROMPT = PromptTemplate(input_variables=["history", "input"], template=template)
chain = ConversationChain(
    prompt=PROMPT,
    verbose=False,
    memory=ConversationBufferMemory(ai_prefix="Assistant:"),
    llm=Ollama(model="tinydolphin"),
)

def record_audio(stop_event, data_queue):
    def callback(indata, frames, time, status):
        if status:
            console.print(status)
        data_queue.put(bytes(indata))

    with sd.RawInputStream(
        samplerate=16000, dtype="int16", channels=1, callback=callback, device=11
    ):
        while not stop_event.is_set():
            time.sleep(0.1)

def transcribe(audio_np: np.ndarray) -> str:
    result = stt.transcribe(audio_np, fp16=False)
    text = result["text"].strip()
    return text

def get_llm_response(text: str) -> str:
    response = chain.predict(input=text)
    if response.startswith("Assistant:"):
        response = response[len("Assistant:") :].strip()
    return response

def start_piper(model_path):
    log_file = open('piper_logs.txt', 'a')  # Append to the log file
    piper_command = ['./piper/piper', '--model', model_path, '--output-raw']
    piper_process = subprocess.Popen(piper_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log_file, bufsize=0)
    threading.Thread(target=play_audio, args=(piper_process.stdout,), daemon=True).start()
    return piper_process

def play_audio(pipe):
    aplay_command = ['aplay', '-r', '22050', '-f', 'S16_LE', '-t', 'raw', '-B', '2048']
    aplay_process = subprocess.Popen(aplay_command, stdin=pipe, stderr=subprocess.PIPE)

    for line in aplay_process.stderr:
        console.print(f"aplay Error: {line.decode().strip()}", style="red")

if __name__ == "__main__":
    console.print("[cyan]Assistant started! Press Ctrl+C to exit.")
    piper_process = start_piper("en_GB-cori-medium.onnx")

    try:
        while True:
            console.input("Press Enter to start recording, then press Enter again to stop.")

            data_queue = Queue()
            stop_event = threading.Event()
            recording_thread = threading.Thread(target=record_audio, args=(stop_event, data_queue))
            recording_thread.start()

            input()
            stop_event.set()
            recording_thread.join()

            audio_data = b"".join(list(data_queue.queue))
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

            if audio_np.size > 0:
                with console.status("Transcribing...", spinner="earth"):
                    text = transcribe(audio_np)
                console.print(f"[yellow]You: {text}")

                with console.status("Generating response...", spinner="earth"):
                    response = get_llm_response(text)
                    piper_process.stdin.write((response + '\n').encode('utf-8'))
                    piper_process.stdin.flush()

                console.print(f"[cyan]Assistant: {response}")
            else:
                console.print("[red]No audio recorded. Please ensure your microphone is working.")

    except KeyboardInterrupt:
        console.print("\n[red]Exiting...")

    finally:
        if piper_process:
            piper_process.terminate()

    console.print("[blue]Session ended.")
