# PERSONA 3 PARODY GENERATOR CUSTOMIZATION GUIDE

A parody script generator for Persona 3 Parodies (specifically in the style of MasterDank47) built with Python. Uses DeepSeek API for content generation.

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
self.api_key = os.getenv('DEEPSEEK_API_KEY')  # Replace with your API key (Never hardcode)
```

## Configuration Examples

### Strict Adherence

```python
# Configurable parameters
self.pattern_strictness = 0.9  # Range: 0.0 (creative) to 1.0 (strict)
self.tag_weight = 2.0         # Range: 0.1 to 3.0
self.max_tags = 4            # Range: 1 to 5
self.use_examples = True     # Options: True/False
```

### Creative Mode

```python
self.pattern_strictness = 0.3
self.tag_weight = 1.2
self.max_tags = 2
self.use_examples = False
```

### Balanced Default

```python
self.pattern_strictness = 0.7
self.tag_weight = 1.5
self.max_tags = 3
self.use_examples = True
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
