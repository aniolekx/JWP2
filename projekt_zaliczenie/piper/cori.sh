#!/bin/bash

# Check if an argument is provided
if [ -z "$1" ]; then
  echo "No argument provided. Please provide a sentence."
  exit 1
fi

# Use the provided argument
echo "$1"

./piper --model en_GB-cori-medium.onnx --output-raw | \
  aplay -r 22050 -f S16_LE -t raw -






