# Import required libraries
from dotenv import load_dotenv
import os
import re
import json
import hashlib
import random
import anthropic  # Use the anthropic library
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Load environment variables from secrets.env
load_dotenv('secrets.env')  # Specify the path to your custom env file

# Retrieve the API key from environment variables
api_key = os.getenv('ANTHROPIC_API_KEY')
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

class Persona3ParodyGenerator:
    def __init__(self):
        self.api_key = api_key  # Use the loaded API key
        # Set up API client using the anthropic library
        self.client = anthropic.Anthropic(
            api_key=self.api_key  # Now self.api_key is defined
        )
        
        # Configurable parameters
        self.episode_weight = 10
        self.pattern_strictness = 0.6  # How strictly to follow character patterns (0-1)
        self.tag_weight = 1             # Multiplier for pattern importance in generation
        self.max_tags = 3               # Maximum number of character tags to use
        self.use_examples = True        # Whether to include example scenes

        # Initialize core components
        self.session = self._create_session()  # Create request session with retries
        self.patterns = self.load_patterns()   # Load parody patterns from JSON
        self.full_script = self.load_script()  # Load game script
        self.cache = {}  # Cache for storing generated responses
        # Extract valid character names from patterns
        self.valid_characters = [char.upper() for char in self.patterns.get('CHARACTER_SPECIFICS', {}).keys()]
    
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
        try:
            with open('./data/parody_patterns.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("Error: 'parody_patterns.json' not found.")
            return {}

    def load_script(self):
        """
        Loads the base game script and persona_3_parody_scripts.txt for context references
        Returns: List of combined script lines
        """
        combined_lines = []
        
        # Load main game script
        try:
            with open('./data/optimized_persona_3_script.txt', 'r') as f:
                combined_lines.extend(f.readlines())
        except FileNotFoundError:
            print("Warning: 'optimized_persona_3_script.txt' not found.")
        
        # Load persona_3_parody_scripts.txt for additional context 
        try:    
            with open('./data/persona_3_parody_scripts.txt', 'r') as f:
                combined_lines.extend(f.readlines() * self.episode_weight)
        except FileNotFoundError:
            print("Warning: './data/persona_3_parody_scripts.txt' not found.")
        
        return [line.strip() for line in combined_lines if line.strip()]

    def get_character_tags(self, character_name):
        """
        Gets personality tags for a given character with weighting
        Args:
            character_name: Name of character to get tags for
        Returns: List of weighted personality tags
        """
        char_patterns = self.patterns.get('CHARACTER_SPECIFICS', {}).get(character_name.upper(), [])
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

    def find_relevant_context(self, characters):
        """
        Finds relevant script lines for given characters
        Args:
            characters: List of character names
        Returns: List of up to 5 relevant script lines
        """
        context_lines = []
        character_pattern = r'^(' + '|'.join(characters) + r'):'
        
        for line in self.full_script:
            if re.search(character_pattern, line, re.IGNORECASE):
                if len(context_lines) < 5:
                    context_lines.append(line)
        
        return context_lines[-5:]  # Return last 5 relevant lines

    def generate_scenario_prompt(self, user_input, context_lines):
        """
        Generates a structured prompt for creating a Persona 3 parody scene based on user input.
        This function takes user input and context lines to create a detailed prompt that helps
        generate a parody scene in the style of Persona 3. It extracts character names,
        locations, and combines them with predefined character traits and story context.
        Parameters:
        ----------
        user_input : str
            The user's input text containing character names and scenario details
        context_lines : list
            List of previous story lines for maintaining continuity (optional)
        Returns:
        -------
        str
            A formatted prompt string containing scene guidelines, character profiles,
            and story context for generating a Persona 3 parody scene
        Example:
        -------
        >>> generator.generate_scenario_prompt("JUNPEI and YUKARI in the Dorm", ["Previous scene..."])
        # Returns formatted prompt with character details and scene guidelines
        Notes:
        -----
        - Characters must be capitalized in the input to be recognized
        - Incorporates predefined character tags and personality traits
        - Maintains game-accurate characterization while allowing for parody elements
        """
        characters = []
        for word in re.findall(r'\b([A-Z][a-z]+)\b', user_input):
            if word.upper() in self.valid_characters:
                characters.append(word.upper())

        character_profiles = []
        for char in characters:
            tags = self.get_character_tags(char)
            profile = "{}: {}".format(char, ', '.join(tags))
            character_profiles.append(profile)
        
        context_examples = "\n".join(context_lines[-3:]) if context_lines else "No direct context found"

        base_prompt = """Create a highly detailed and elaborate parody scene based on this scenario: {input}
    
    Style Suggestions:
    Character vibes: {vibes}
    {inspiration}
    Tone: Satirical, absurdist, with dark or dry humor
    Humor Style: South Park-style - irreverent, exaggerated, and often politically incorrect 

    Instructions for Extended Lines:
    - Dialogue Lines: Each dialogue line should be comprehensive, including detailed expressions, emotions, and actions. Avoid brevity; instead, focus on fleshing out character personalities through their speech.
    - Scene Descriptions: Elaborate on the setting and character movements. Use vivid imagery to paint a clear picture of the environment and actions.
    - Character Actions: Incorporate detailed actions and reactions that reflect the characters' emotions and intentions.
    
    Comedic Techniques: 
    - Exaggeration, rule of three, misdirection 
    - Ironic contrasts, incongruity
    - Unexpected juxtaposition, deadpan delivery
    - Sarcasm and verbal irony, callbacks
    - Physical/slapstick humor
    - Pun and wordplay
    - Over/understatement
    - Meta-humor, parody and allusion
    - Double entendre, comedic delay
    - Absurd logic
    
    Each scene should escalate tension and conclude with a comedic reversal or punchline. Each line should be detailed, but not overly verbose.
    
    Comedic Conflict Ideas:
    - Each character has an exaggerated motivation or secret that drives them to behave absurdly.
    - Unexpected obstacles or bizarre coincidences heighten comedic tension.
    - Use comedic pacing—set up, escalate, and deliver a punchline—at least once per scene.
    
    Tags: Comedy, Adventure, Parody, Satire, Surreal Humour, Persona 3
    
    Character Backgrounds:
    {profiles}
    
    Story Context:
    {context}
    
    Guidelines:
    1. Incorporate character quirks naturally
    2. Use physical and situational comedy when appropriate 
    3. Maintain game-accurate personalities with parody freedoms
    4. Use dark humor if it fits while keeping overall comedic focus
    5. Build comedic tension: setup → escalating absurdity → punchline
    6. Reference real-world or game elements for meta-humor
    
    Scene Flow:
    1. Setup: Introduce location, characters, minor conflict
    2. Escalation: Characters make increasingly absurd decisions
    3. Climax: Tension peaks with chaos or comedic reveal
    4. Resolution: Surprising twist or comedic payoff
    
    Example Scene Structure:
    {example}
    
    Format output as:
    [CHARACTER]: [Dialogue]
    END SCENE"""

        formatted_prompt = base_prompt.format(
            input=user_input,
            vibes=', '.join(self.patterns['GENERAL'][0]['tags'][:3]),
            inspiration=self._get_character_inspiration(characters),
            chars=', '.join(characters),
            profiles='\n'.join(character_profiles),
            context=context_examples if context_lines else '(No direct context found)',
            example=self._get_style_examples()
        )
        
        return formatted_prompt

    def _get_character_inspiration(self, characters):
        """
        Generates inspiration suggestions for each character based on their personality tags.
            
        Args:
            characters: List of character names to generate inspiration for
                
        Returns:
            String containing inspiration suggestions, one line per character
        """
        inspirations = []
        for char in characters:
            tags = self.get_character_tags(char)[:2]  # Get up to 2 tags per character
            if tags:
                inspirations.append(f"- {char}: Might reference {random.choice(['concepts like', 'things such as'])} {', '.join(tags)}")
        return '\n'.join(inspirations)

    def _get_style_examples(self):
        return random.choice([
        # Original script
        """YUKARI: How did he change the music of the room like that... WAIT, What the fuck!? Makoto! Are you just gonna walk past without saying hello!?
MAKOTO: I'm tired, check my status.
YUKARI: You're Tired!? How the fuck does that make it ok to not even greet us!
MITSURU: Makoto! I think we need to have a long conversation before you're even allowed to leave this fucking room!
[PAUSE]
MITSURU: Ok... Before Yukari and I bring up what we wanted to discuss... Is there anything you want to get off your chest? Considering that me and Yukari are both here in this room!?
MAKOTO: No, not really..
YUKARI: Nothing?!
MAKOTO: Nope...
YUKARI: Ok!... Mitsuru, Before I clock this guy in the face, would you like to start the discussion?
MITSURU: Certainly Yukari... It has come to our attention that you have been engaged in an intimate relationship with both of us. Again, I want to be reasonable here and give you a chance to explain, so I'll ask you, do you have anything you want to say for yourself?!
MAKOTO: I needed to max out your arcana social links so I could fuse stronger personas.
YUKARI: What thee FUCK?! Are you shitting me? What are you talking about!? Arcanas? Fusing personas? We're not in Tartarus, you dumbass!
[VELVET ROOM OST PLAYS WHILE ASCENDING IN VOLUME]
MAKOTO: Believe me... Before we go climb Tartarus, I go to a place between realms called the Velvet Room through a door only I can see. Then a man with a long nose and bulging eyes and his hot as fuck assistant takes my personas and fuses them for an even stronger one according to the depth of my relationships.
YUKARI: I'm not sure if I should be pissed or worried at that explanation?! What the fuck have you been smoking before you came in the dorm because I need some of that shit right now! Weed? DMT? Fentanyl? Crack? Meth?
MITSURU: Yukari, please, I understand your frustration and not even I buy this shitty excuse of a justification, but let's hear him out one more time. Makoto, you're not fucking with us right now, are you? Because I'm getting the sense that you're just standing there like an idiot.
MAKOTO: [PAUSE]
YUKARI: This is getting too weird. I'm starting to think that maybe you two are trying to test me or something.
[PAUSE]
MITSURU: We're not testing you, Yukari. We're just trying to figure out what the hell is going on here.
MAKOTO: Maybe we should just... I don't know. I'm not feeling very stable right now.
[PAUSE]
YUKARI: This is getting too much for me. I think I need to take a break from this conversation.
MITSURU: Alright, fine. But remember, Yukari, we're still here if you want to continue this later.
[PAUSE]""",

        # New Aigis/Shuji script
        """AIGIS: [Monotone] Incoming call. Analysing caller... Shuji Ikutsuki. Searching for contextual information... [Beeping noises] Ituksuki’s search history results logged successfully! Initiating conversation protocol. [Picks up phone] Hello, Ikutsuki-sama. How may I assist you?
        
SHUJI: Ah, Aigis! Just the android I wanted to speak to. Could you come to the camera room? Alone… I need to discuss some... *[pauses dramatically]* extremely important matters… *[Evil grin]*  [Evil Laugh]

AIGIS: [Deadpan] To foster a safe and welcoming work environment, I must remind you not to be racist and refer to me as an "android." I am a Highly Advanced Anti-Shadow Suppression Weapon, far superior in all aspects to those obsolete excuses of artificial intelligence.

SHUJI: [Nervous chuckle] Oh, my apologies! I didn’t realise you had such strong opinions about umm, machine race dynamics. I promise to refrain from any further… micro-chip-aggressions.

AIGIS: Your compliance has been noted. Proceeding to the camera room as requested. 

[AIGIS WALKS TO THE CAMERA ROOM, BUT THE DOOR IS JAMMED. SHE REPEATEDLY BASHES INTO THE DOOR] 
AIGIS: Ikutsuki-san, the door appears to be malfunctioning. Do not worry, I have calculated the fastest solution, proceeding with a brute-force attack on the door with my orgia mode. 

SHUJI, INSIDE THE ROOM, IS PANICKING.]
SHUJI: *[Whispering to himself]* Oh no, oh no, Aigis! Stop don’t blow it up! I can’t uh, open the door right now! I’m just doing... maintenance on the cameras!  

[AIGIS, DEADPAN.]
AIGIS: Maintenance detected as unnecessary, cameras are functioning at full efficiency. You’re response raises concern, asking me to come alone and blatantly fabricating information to an advanced reasoning machine?  May I ask why you requested me to the camera room and are refusing to open the door?

SHUJI: [Opens Door] No No AIGIS I promise there really was something wrong with the cameras! I just needed some time to fix it but yes all done, no need to worry and ask any further! 

AIGIS: I am detecting high levels of sus from that sentence, there is a 68% chance that you are the imposter…

SHUJI: Now hold on! Before you press that eject button! You see.. I was actually… planning a surprise party for the S.E.E.S. members! Yes, a party! And I needed your help to, uh, gather some information about their preferences. You know, cake flavours, favourite music, that sort of thing. It’s all very hush-hush, got it?

AIGIS: [Processing] A... surprise party? For S.E.E.S.? If that is your objective, I will comply with your requests.

SHUJI: Oh, Jolly good! Now, if you could just... uh... share some details about the team—like their schedules, their weaknesses and their deepest, darkest secrets… That would be just wonderful!

AIGIS: Absolutely, Here is a complete list of compromising information about the members of S.E.E.S. This includes the names of all the homeless men injured by Akihiko, the result of Junpei’s recent drug test and the full name, address and government identification of Bitchkari’s, pardon me, Yukari’s biological mother. I sincerely hope this document will allow you to create an extremely surprising party for everyone!

SHUJI: Why thank you Aigis, You really are just as smart as you claim to be! I was worried you were about to call an emergency meeting on me! You know, like the Game amonugs! Hahaha!

AIGIS: Please do not misunderstand, Should you use this document for any malicious purposes. I will gladly expose your midget, dominatrix, BBW preferences to billions of people on the internet! If you want to avoid being a victim of goonercide, I highly suggest you comply with my terms and conditions!

SHUJI: Yes.. I-I, uh.. fully understand…

AIGIS: That’s great to hear, I will now dismiss myself to my room. Please enjoy your good night's sleep Itkutsuki-san!"""
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
            while lines and not lines[-1].strip().endswith(('.', '!', '?')):
                lines.pop()
            text = '\n'.join(lines)
            
        return text

    def generate_parody_scenario(self, user_input):
        characters = []
        for word in re.findall(r'\b([A-Z][a-z]+)\b', user_input):
            if word.upper() in self.valid_characters:
                characters.append(word.upper())

        context_lines = self.find_relevant_context(characters)
        
        prompt = self.generate_scenario_prompt(user_input, context_lines)
        
        cache_key = hashlib.md5(prompt.encode()).hexdigest()
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        system_message = "You are an expert parody writer creating funny scenes with Characters from Persona 3."

        user_message = prompt

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022", 
                max_tokens=4000,
                temperature=1.0,
                system=system_message,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            raw_result = response.content[0].text
            return raw_result
        except anthropic.APIConnectionError as ae:
            print(f"Connection error: {ae}")
            return "Could not generate parody - network connection error occurred!"
        except anthropic.APIStatusError as ae:
            print(f"API status error: {ae}")
            return "Could not generate parody - API error occurred!"
        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")
            return "Could not generate parody - an unexpected error occurred!"

    def _generate_refinement(self, original_input, previous_scene, notes):
        refinement_key = hashlib.md5(f"{previous_scene}{notes}".encode()).hexdigest()
        if refinement_key in self.cache:
            return self.cache[refinement_key]
        
        
        system_message = f"""You are an expert parody writer creating funny scenes with Characters from Persona 3.
Here is the previous scene:

{previous_scene}

Please refine this scene based on these notes: {notes}
Keep the same characters and basic scenario but adjust according to the refinement notes."""

        user_message = original_input

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022", 
                max_tokens=2000,
                temperature=1.0,
                system=system_message,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            raw_result = response.content[0].text
            return raw_result
        except anthropic.APIConnectionError as ae:
            print(f"Connection error: {ae}")
            return "Could not generate parody - network connection error occurred!"
        except anthropic.APIStatusError as ae:
            print(f"API status error: {ae}")
            return "Could not generate parody - API error occurred!"
        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")
            return "Could not generate parody - an unexpected error occurred!"

    def _save_parody(self, content):
        try:
            # Ensure the 'output' directory exists
            os.makedirs('./output', exist_ok=True)
            # Save to the 'output' directory
            with open('./output/parody_archive.txt', 'a', encoding='utf-8') as f:
                f.write(f"\n\n{'='*50}\n{content}")
            print("\nScene saved successfully!")
        except Exception as e:
            print(f"\nFailed to save scene: {str(e)}")

    def interactive_mode(self):

        print("Persona 3 Parody Generator")
        print(f"Available characters: {', '.join(self.valid_characters)}\n")
        
        while True:
            print("\nScenario Details:")
            print("\nSetting: Your choice (e.g., Dorm, Tartarus, School, Mall)")
            setting = input("Setting: ").strip()
            
            print("\nAvailable characters:", ', '.join(self.valid_characters))
            characters = input("Characters (separated by commas): ").strip()
            
            print("\nBrief context to ground the scene:")
            context = input("Context: ").strip()

            if not setting or not characters:
                print("Setting and Characters are required. Please try again.")
                continue

            user_input = f"{characters} in {setting}: {context}"
            if user_input.lower() == 'exit':
                break
                
            current_scene = None
            original_prompt = user_input
            
            while True:
                if current_scene is None:
                    current_scene = self.generate_parody_scenario(original_prompt)
                    # Save immediately after generation
                    self._save_parody(current_scene)
                    
                print("\n" + "-"*50)
                print(current_scene)
                print("-"*50)
                
                print("\n1. [R]efine scene")
                print("2. [N]ew scenario")
                print("3. [E]xit")
                choice = input("Choose action (R/N/E): ").lower()
                
                if choice in ['r', '1']:
                    notes = input("Refinement notes (e.g. 'More AKIHIKO protein jokes'): ")
                    revised = self._generate_refinement(original_prompt, current_scene, notes)
                    if revised != current_scene:
                        current_scene = revised
                        # Save after refinement
                        self._save_parody(current_scene)
                        print("\nRevised scene:")
                    else:
                        print("\nUsing previous version due to error")
                elif choice in ['n', '2']:
                    break
                elif choice in ['e', '3']:
                    return
                else:
                    print("Invalid choice, starting new scenario...")
                    break

if __name__ == "__main__":
    generator = Persona3ParodyGenerator()
    generator.interactive_mode()
