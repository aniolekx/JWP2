#!/bin/bash

# Define the fixed model files for ollama and piper
OLLAMA_MODEL="tinydolphin"
PIPER_MODEL="en_GB-cori-medium.onnx"

# Run ollama and capture its output
TEXT=$(ollama run $OLLAMA_MODEL)

# Check if ollama produced any output
if [ -z "$TEXT" ]; then
  echo "ollama did not produce any output."
  exit 1
fi

# Echo the text for debugging purposes (optional)
echo "Text from ollama: $TEXT"

# Send the text from ollama to piper
echo "$TEXT" | ./piper --model "$PIPER_MODEL" --output-raw | \
  aplay -r 22050 -f S16_LE -t raw -

