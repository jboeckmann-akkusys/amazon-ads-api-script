# Test config file location
import os
from pathlib import Path

# Check current working directory
print(f"Current directory: {os.getcwd()}")

# Check where the library looks for config
import ad_api
print(f"Package location: {ad_api.__file__}")

# Check for config.yaml in common locations
locations = [
    ".config.yaml",
    "./config.yaml",
    os.path.expanduser("~/.config/amazon-ads/config.yaml"),
    "config.yaml"
]

for loc in locations:
    exists = os.path.exists(loc)
    print(f"{loc}: {exists}")