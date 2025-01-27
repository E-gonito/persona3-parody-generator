# Import required libraries
import json
import re
import hashlib
import random
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file
import os

class DeepSeekParodyGenerator:
    def __init__(self):
        # Get API key from environment variables
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is not set")
            
        # Set up API configuration
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Initialize core components
        self.episode_weight = 10
        self.session = self._create_session()  # Create request session with retries
        self.patterns = self.load_patterns()   # Load parody patterns from JSON
        self.full_script = self.load_script()  # Load game script
        self.cache = {}  # Cache for storing generated responses
        # Extract valid character names from patterns
        self.valid_characters = [char.upper() for char in self.patterns['CHARACTER_SPECIFICS'].keys()]
        
        # Configurable parameters
        self.pattern_strictness = 0.8  # How strictly to follow character patterns (0-1)
        self.tag_weight = 1.5         # Multiplier for pattern importance in generation
        self.max_tags = 3             # Maximum number of character tags to use
        self.use_examples = True      # Whether to include example scenes

    def _create_session(self):
        """
        Creates a requests session with retry logic for API calls
        Returns: Session object configured with retry settings
        """
        session = requests.Session()
        retries = Retry(
            total=5,  # Maximum number of retries
            backoff_factor=1,  # Wait 1, 2, 4... seconds between retries
            status_forcelist=[429, 500, 502, 503, 504]  # HTTP codes to retry on
        )
        session.mount('https://', HTTPAdapter(max_retries=retries))
        return session

    def load_patterns(self):
        """
        Loads character patterns and dialogue rules from JSON file
        Returns: Dictionary containing parody patterns
        """
        with open('parody_patterns.json', 'r') as f:
            return json.load(f)

    def load_script(self):
        """
        Loads the base game script and episode4.txt for context references
        Returns: List of combined script lines
        """
        combined_lines = []
        
        # Load main game script
        try:
            with open('optimized_persona_script.txt', 'r') as f:
                combined_lines.extend(f.readlines())
        except FileNotFoundError:
            print("Warning: Main script file not found")
        
        # Load episode4 script
        try:    
            with open('episode4.txt', 'r') as f:
                combined_lines.extend(f.readlines() * self.episode_weight)
        except FileNotFoundError:
            print("Warning: episode4.txt not found")
        
        return [line.strip() for line in combined_lines if line.strip()]

    def get_character_tags(self, character_name):
        """
        Gets personality tags for a given character with weighting
        Args:
            character_name: Name of character to get tags for
        Returns: List of weighted personality tags
        """
        char_patterns = self.patterns['CHARACTER_SPECIFICS'].get(character_name.upper(), [])
        all_tags = []
        for pattern_data in char_patterns:
            # Calculate weight based on tag count and weight multiplier
            weight = int(len(pattern_data['tags']) * self.tag_weight) + 1
            all_tags.extend(pattern_data['tags'] * weight)
        
        # Randomly reduce tags based on strictness setting
        if self.pattern_strictness < 0.5:
            all_tags = random.sample(all_tags, int(len(all_tags)*self.pattern_strictness*2))
        
        # Return unique tags up to max limit
        return list(set(all_tags))[:self.max_tags]

    def find_relevant_context(self, characters, location):
        """
        Finds relevant script lines for given characters and location
        Args:
            characters: List of character names
            location: Optional location to filter by
        Returns: List of up to 5 relevant script lines
        """
        context_lines = []
        character_pattern = r'^(' + '|'.join(characters) + r'):'
        
        for line in self.full_script:
            if re.search(character_pattern, line, re.IGNORECASE):
                if location and location.lower() in line.lower():
                    context_lines.append(line)
                elif len(context_lines) < 5:
                    context_lines.append(line)
        
        return context_lines[-5:]  # Return last 5 relevant lines

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

        Style Suggestions:
        - Character vibes: {', '.join(self.patterns['GENERAL'][0]['tags'][:3])}
        {self._get_character_inspiration(characters)}

        Character Backgrounds:
        {'\n'.join(character_profiles)}

        Story Context:
        {context_examples if context_lines else '(No direct context found)'}

        Guidelines:
        1. Incorporate character quirks naturally
        2. Blend Persona mechanics with absurd humor
        3. Use physical comedy when appropriate
        4. Maintain game-accurate personalities
        5. Use dark humour if it fits the scene

        Example Scene Flow:
        {self._get_style_examples()}
        
        Format:
        [CHARACTER]: [Dialogue]
        END SCENE"""

    def _get_character_inspiration(self, characters):
        inspirations = []
        for char in characters:
            tags = self.get_character_tags(char)[:2]
            if tags:
                inspirations.append(f"- {char}: Might reference {random.choice(['concepts like', 'things such as'])} {', '.join(tags)}")
        return '\n'.join(inspirations)

    def _get_style_examples(self):
        return random.choice([
                "[YUKARI AND MITSURU IN THE DORM],"
                "[AKIHIKO WALKS IN],"
                "AKIHIKO: Hey Mitsuru and Yukari... you wanna join us walking Koromaru to the shrine? Everyone else is already outside waiting."
                "MITSURU: Oh... Thanks for the offer Akihiko, but me and Yukari will wait here for Makoto to get back home."
                "YUKARI: Yea, we got a few things we need to discuss... so we won't be coming today."
                "AKIHIKO: Well, good luck with whatever it is... we'll be back soon anyways. See ya."
                "YUKARI: Yea, see ya senpai!"
                "MITSURU: Goodbye Akihiko."
                "[AKIHIKO LEAVES],"
                "YUKARI: Mitsuru... let's call a truce from now on, the only person we should be against right now is not each other, but our son of a bitch leader!"
                "MITSURU: You're right Yukari! I believe we've matured enough to know who the real perpetrator is..."
                "YUKARI: Oh Bestie!! Slay!"
                "MITSURU: Slay indeed.."
                "[PAUSE WITH COCKROACH SONG PLAYING AND GETTING LOUDER],"
                "MITSURU: You hear that?"
                "YUKARI: That overly loud emo music? Yes, I think he's gonna come through the \"door\" any second now..."
                "[DOOR OPENING SOUND EFFECT],"
                "[THEY TURN AROUND],"
                "[MAKOTO, IN FRONT OF THE DOOR BACKGROUND, LOOKS AT THEM THEN PAUSES THE MUSIC WITH A CLICK, THEN PLAYS DORM OST],"
                "[FOOTSTEPS, LOOKING AT YUKARI AND MITSURU, THEY TURN AROUND AS FOOTSTEPS COME AND PASS THEM],"
                "YUKARI: How did he change the music of the room like that... WAIT, What the fuck!? Makoto! Are you just gonna walk past without saying hello!?"
                "MAKOTO: I'm tired, check my status."
                "YUKARI: You're Tired!? How the fuck does that make it ok to not even greet us!"
                "MITSURU: Makoto! I think we need to have a long conversation before you're even allowed to leave this fucking room!"
                "[PAUSE],"
                "MITSURU: Ok... Before Yukari and I bring up what we wanted to discuss... Is there anything you want to get off your chest? Considering that me and Yukari are both here in this room!?!"
                "MAKOTO: No, not really.."
                "YUKARI: Nothing?!"
                "MAKOTO: Nope.."
                "YUKARI: Ok!... Mitsuru, Before I clock this guy in the face, would you like to start the discussion?"
                "MITSURU: Certainly Yukari... It has come to our attention that you have been engaged in an intimate relationship with both of us. Again, I want to be reasonable here and give you a chance to explain, so I'll ask you, do you have anything you want to say for yourself?!"
                "MAKOTO: I needed to max out your arcana social links so I could fuse stronger personas."
                "YUKARI: What thee FUCK?! Are you shitting me? What are you talking about!? Arcanas? Fusing personas? We're not in Tartarus, you dumbass!"
                "[VELVET ROOM OST PLAYS WHILE ASCENDING IN VOLUME],"
                "MAKOTO: Believe me... Before we go climb Tartarus, I go to a place between realms called the Velvet Room through a door only I can see. Then a man with a long nose and bulging eyes and his hot as fuck assistant takes my personas and fuses them for an even stronger one according to the depth of my relationships."
                "YUKARI: I'm not sure if I should be pissed or worried at that explanation?! What the fuck have you been smoking before you came in the dorm because I need some of that shit right now! Weed? DMT? Fentanyl? Crack? Meth?"
                "MITSURU: Yukari, please, I understand your frustration and not even I buy this shitty excuse of a justification, but let's hear him out one, more, time. Makoto, you're not fucking with us right now, are you? Because I'm seriously losing my patience here. Why are you going out with both me and Yukari at the same time!?"
                "MAKOTO: There's no option for a platonic route in Persona 3 Fez."
                "MITSURU: Ok... Yukari, he's fucking with us, get me my sabre and a cross, I'm going to crucify this son of a bitch and hang him in front of the dorm."
                "YUKARI: What a good idea Mitsuru! I'm glad we can finally come to terms on one thing, which is making sure this motherfucker experiences the worst possible pain a human can experience!"
                "MITSURU: Yes, as members of SEES and victims of our leader's womanizing, we need to stick together if we want to make sure that this asshole is never able to touch his cock with his hands ever again!"
                "YUKARI: Oh, speaking of cocks, I say we take turns with my bow, taking shots and see who can hit his dick first!"
                "MITSURU: Oh Tres Bien... Yukari, I didn't know you had that girl boss energy inside of you, I think we'll make a great team today."
                "YUKARI: Yea, actually... I can feel a really strong bond growing between us..."
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
                    "temperature": 0.75,
                    "max_tokens": 2000,
                    "stop": ["END SCENE"]
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
        try:
            with open('parody_archive.txt', 'a', encoding='utf-8') as f:
                f.write(f"\n\n{'='*50}\n{content}")
            print("\nScene saved successfully!")
        except Exception as e:
            print(f"\nFailed to save scene: {str(e)}")

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