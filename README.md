# PERSONA 3 PARODY GENERATOR CUSTOMIZATION GUIDE

A parody script generator for Persona 3 Parodies (specifically in the style of MasterDank47) built with Python. Uses Claude API for content generation.

## Prerequisites

- Docker installed on your system
- Docker Compose (recommended)

## Local Environment Setup

1. Create a `.env` file in the root directory
2. Add your DeepSeek API key:

```
DEEPSEEK_API_KEY=your_api_key_here
```

## API Settings

**File:** `persona_parody_generator.py`  
**Location:** `def __init__(self):`

```python
self.api_key = os.getenv('API_KEY')  # Replace with your API key (Never hardcode)
```

## Quick Start With Docker

```bash
# Build Docker image
docker build -t persona-parody-gen .

# Run container (Linux/MacOS)
docker run -it \
  --env-file secrets.env \
  -v "${PWD}\output:/app/output"\
  persona-parody-gen

# (Windows)
docker run -it `
  --env-file secrets.env `
  -v "${PWD}\output:/app/output" `
  persona-parody-gen

# Run script
python3 persona_parody_generator.py
```

````

## Usage Example

```bash
# Interactive prompt example
Enter setting (e.g., Dorm, Tartarus, School, Mall): Dorm
Enter characters (comma-separated): YUKARI,JUNPEI
Enter context: Studying for exams

# Example output
[RETURNED SCRIPT]

# Available actions
1. [R]efine scene
2. [N]ew scenario
3. [E]xit

Choose action (R/N/E):
````

The results will be saved to `parody_archive.txt`, to copy over-

```bash
# Copy results from container
docker cp <container-name>:/app/parody_archive.txt ./output/
```

pip install bitsandbytes
