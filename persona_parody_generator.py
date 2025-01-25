import json
import re
import hashlib
import random
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
        self.pattern_strictness = 0.8  # 0-1 (0=ignore patterns, 1=strict adherence)
        self.tag_weight = 1.5  # Multiplier for pattern importance
        self.max_tags = 3  # Max tags per character
        self.use_examples = True  # Whether 

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
            # Adjustable weight calculation
            weight = int(len(pattern_data['tags']) * self.tag_weight) + 1
            all_tags.extend(pattern_data['tags'] * weight)
        
        # Apply pattern strictness filter
        if self.pattern_strictness < 0.5:
            all_tags = random.sample(all_tags, int(len(all_tags)*self.pattern_strictness*2))
        
        return list(set(all_tags))[:self.max_tags]  # Use configurable max

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
        characters = []
        for word in re.findall(r'\b([A-Z][a-z]+)\b', user_input):
            if word.upper() in self.valid_characters:
                characters.append(word.upper())
        
        location_match = re.search(r'in the (\w+)', user_input)
        location = location_match.group(1) if location_match else ""

        character_profiles = []
        for char in characters:
            tags = self.get_character_tags(char)
            profile = f"{char}: {', '.join(tags)}"
            character_profiles.append(profile)
        
        context_examples = "\n".join(context_lines[-3:]) if context_lines else "No direct context found"

        return f"""Create a parody scene based on this scenario: {user_input}

        {"CHARACTER INSPIRATION:" if self.pattern_strictness > 0.4 else "SUGGESTIONS:"}
        {self._get_character_inspiration(characters) if self.pattern_strictness > 0.3 else ''}

        {"REQUIRED ELEMENTS:" if self.pattern_strictness > 0.7 else "OPTIONAL IDEAS:"} 
        {', '.join(random.sample(self.patterns['GENERAL'][0]['tags'], int(3*self.pattern_strictness)))}

        {"EXAMPLE SCENES:" if self.use_examples else ""}
        {self._get_style_examples() if self.use_examples else ""}

        CHARACTER BACKGROUNDS:
        {' | '.join(character_profiles)}  # More compact format

        RELEVANT CONTEXT:
        {context_examples if context_lines else 'No specific context found'}

        CORE GUIDELINES:
        1. Persona game logic + absurd twist
        2. Physical comedy where natural
        3. Stay true to character voices
        4. At least one meta element

        FORMAT RULES:
        - One exchange per line
        - Actions in parentheses
        - End with END SCENE
        - Max 3 main exchanges
        """

# Removed duplicate sections and fixed these issues:

    def _get_character_inspiration(self, characters):
        inspirations = []
        for char in characters:
            tags = self.get_character_tags(char)[:2]
            if tags:
                inspirations.append(f"- {char}: Might reference {random.choice(['concepts like', 'things such as'])} {', '.join(tags)}")
        return '\n'.join(inspirations)

    def _get_style_examples(self):
        return random.choice([
            "AKIHIKO: (punching vending machine) 'This better drop a Muscle Drink!'",
            "KOTONE: (checking phone) 'Sorry, my Social Link meter is flashing...'",
            "YUKARI: (hiding blunt) 'This is... herbal medicine! For stress!'"
        ])

    def _clean_response(self, text):
        text = text.split("END SCENE")[0].strip()
        if not text:
            return text
            
        last_punct = max(text.rfind('.'), text.rfind('!'), text.rfind('?'))
        if last_punct != -1:
            text = text[:last_punct+1]
        else:
            lines = text.split('\n')
            while lines and not lines[-1].strip().endswith(('.','!','?')):
                lines.pop()
            text = '\n'.join(lines)
            
        return text

    def generate_parody_scenario(self, user_input):
        characters = []
        for word in re.findall(r'\b([A-Z][a-z]+)\b', user_input):
            if word.upper() in self.valid_characters:
                characters.append(word.upper())
        
        location = re.search(r'in the (\w+)', user_input)
        location = location.group(1) if location else ""
        context_lines = self.find_relevant_context(characters, location)
        
        prompt = self.generate_scenario_prompt(user_input, context_lines)
        
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
                            "content": "You are a expert parody writer creating funny Persona 3 scenes. Use character tags and meme patterns naturally."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 1.25 - (self.pattern_strictness * 0.5),  # Auto-adjust based on strictness
                    "max_tokens": 1000,
                    "stop": ["END SCENE"],
                    "presence_penalty": -0.5 if self.pattern_strictness > 0.7 else 0

                },
                timeout=30
            )
            response.raise_for_status()
            
            raw_result = response.json()['choices'][0]['message']['content'].strip()
            result = self._clean_response(raw_result)
            self.cache[cache_key] = result
            return result
            
        except Exception as e:
            print(f"API Error: {str(e)}")
            return "Could not generate parody - here's a fallback joke: Why did Aigis refuse to play cards? She kept getting dealt motherboard!"

    def _generate_refinement(self, original_input, previous_scene, notes):
        refinement_key = hashlib.md5(f"{previous_scene}{notes}".encode()).hexdigest()
        if refinement_key in self.cache:
            return self.cache[refinement_key]

        try:
            response = self.session.post(
                self.base_url,
                headers=self.headers,
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are editing an existing parody scene. Implement requested changes while maintaining character consistency."
                        },
                        {
                            "role": "user",
                            "content": f"Original scenario: {original_input}\nCurrent scene:\n{previous_scene}\n\nRevision notes: {notes}"
                        }
                    ],
                    "temperature": 0.6,
                    "max_tokens": 1000,
                    "stop": ["END SCENE"]
                },
                timeout=30
            )
            response.raise_for_status()
            
            raw_result = response.json()['choices'][0]['message']['content'].strip()
            result = self._clean_response(raw_result)
            self.cache[refinement_key] = result
            return result
            
        except Exception as e:
            print(f"API Error: {str(e)}")
            return previous_scene

    def _save_parody(self, content):
        with open('parody_archive.txt', 'a') as f:
            f.write(f"\n\n{'='*50}\n{content}")
        print("\nScene saved to parody_archive.txt!")

    def interactive_mode(self):
        print("Persona 3 Parody Generator")
        print(f"Available characters: {', '.join(self.valid_characters)}\n")
        
        while True:
            user_input = input("\nEnter scenario (e.g. 'Yukari and Akihiko gym mishap') or 'exit': ")
            if user_input.lower() == 'exit':
                break
                
            current_scene = None
            original_prompt = user_input
            
            while True:
                if current_scene is None:
                    current_scene = self.generate_parody_scenario(original_prompt)
                print("\n" + "-"*50)
                print(current_scene)
                print("-"*50)
                
                print("\n1. [R]efine scene")
                print("2. [N]ew scenario")
                print("3. [S]ave & exit")
                choice = input("Choose action (R/N/S): ").lower()
                
                if choice in ['r', '1']:
                    notes = input("Refinement notes (e.g. 'More Akihiko protein jokes'): ")
                    revised = self._generate_refinement(original_prompt, current_scene, notes)
                    if revised != current_scene:
                        current_scene = revised
                        print("\nRevised scene:")
                    else:
                        print("\nUsing previous version due to error")
                elif choice in ['n', '2']:
                    break
                elif choice in ['s', '3']:
                    self._save_parody(current_scene)
                    return
                else:
                    print("Invalid choice, starting new scenario...")
                    break

if __name__ == "__main__":
    generator = DeepSeekParodyGenerator()
    generator.interactive_mode()