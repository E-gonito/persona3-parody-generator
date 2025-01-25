import json
import re
import hashlib
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv
load_dotenv()
import os

class DeepSeekParodyGenerator:
    def __init__(self):
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is not set")
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        self.session = self._create_session()
        self.patterns = self.load_patterns()
        self.full_script = self.load_script()
        self.cache = {}
        self.valid_characters = [char.upper() for char in self.patterns['CHARACTER_SPECIFICS'].keys()]

    def _create_session(self):
        session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        session.mount('https://', HTTPAdapter(max_retries=retries))
        return session

    def load_patterns(self):
        with open('parody_patterns.json', 'r') as f:
            return json.load(f)

    def load_script(self):
        with open('optimized_persona_script.txt', 'r') as f:
            return [line.strip() for line in f.readlines()]

    def get_character_tags(self, character_name):
        char_patterns = self.patterns['CHARACTER_SPECIFICS'].get(character_name.upper(), [])
        all_tags = []
        for pattern_data in char_patterns:
            all_tags.extend(pattern_data['tags'])
        return list(set(all_tags))[:5]  # Return top 5 unique tags

    def find_relevant_context(self, characters, location):
        context_lines = []
        character_pattern = r'^(' + '|'.join(characters) + r'):'
        
        for line in self.full_script:
            if re.search(character_pattern, line, re.IGNORECASE):
                if location and location.lower() in line.lower():
                    context_lines.append(line)
                elif len(context_lines) < 5:
                    context_lines.append(line)
        
        return context_lines[-5:]

    def generate_scenario_prompt(self, user_input, context_lines):
        # Extract entities with proper character validation
        characters = []
        for word in re.findall(r'\b([A-Z][a-z]+)\b', user_input):
            if word.upper() in self.valid_characters:
                characters.append(word.upper())
        
        location_match = re.search(r'in the (\w+)', user_input)
        location = location_match.group(1) if location_match else ""

        # Build character profiles using tags
        character_profiles = []
        for char in characters:
            tags = self.get_character_tags(char)
            profile = f"{char}: Known for {', '.join(tags)}"
            character_profiles.append(profile)
        
        # Build context examples
        context_examples = "\n".join(context_lines[-3:]) if context_lines else "No direct context found"

        return f"""Create a parody scene based on this scenario: {user_input}

        Character Profiles:
        {'\n'.join(character_profiles)}

        Original Context Examples:
        {context_examples}

        Guidelines:
        1. Use tags from character profiles for humor
        2. Include at least one meme reference from GENERAL patterns
        3. Maintain character voice consistency
        4. Add meta-commentary about Persona mechanics
        5. Keep dialogues snappy (under 200 characters per line)
        6. Include physical comedy elements

        Format:
        [CHARACTER]: [Dialogue] [Funny action/metajoke in parentheses]
        """

    def generate_parody_scenario(self, user_input):
        # Find relevant context
        characters = []
        for word in re.findall(r'\b([A-Z][a-z]+)\b', user_input):
            if word.upper() in self.valid_characters:
                characters.append(word.upper())
        
        location = re.search(r'in the (\w+)', user_input)
        location = location.group(1) if location else ""
        context_lines = self.find_relevant_context(characters, location)
        
        # Generate enhanced prompt
        prompt = self.generate_scenario_prompt(user_input, context_lines)
        
        # Check cache
        cache_key = hashlib.md5(prompt.encode()).hexdigest()
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            response = self.session.post(
                self.base_url,
                headers=self.headers,
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a expert parody writer creating funny Persona 3 scenes. Use character tags and meme patterns from the provided data."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.85,
                    "max_tokens": 500
                },
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()['choices'][0]['message']['content'].strip()
            self.cache[cache_key] = result
            return result
            
        except Exception as e:
            print(f"API Error: {str(e)}")
            return "Could not generate parody - here's a fallback joke: Why did Aigis refuse to play cards? She kept getting dealt motherboard!"

    def interactive_mode(self):
        print("Persona 3 Parody Generator - Enter your scenario (e.g. 'Yukari and Mitsuru argue about cooking')")
        print(f"Available characters: {', '.join(self.valid_characters)}\n")
        
        while True:
            user_input = input("\nScenario prompt (type 'exit' to quit): ")
            if user_input.lower() == 'exit':
                break
            print("\nGenerating parody...\n")
            parody = self.generate_parody_scenario(user_input)
            print(parody)
            print("\n" + "-"*50 + "\n")

if __name__ == "__main__":
    generator = DeepSeekParodyGenerator()
    generator.interactive_mode()