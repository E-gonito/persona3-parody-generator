# Import required libraries
import json
import re
import hashlib
import random
import os
import traceback

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments, DataCollatorForLanguageModeling
from datasets import load_dataset, Dataset

import bitsandbytes as bnb  # Import BitsAndBytes

class LocalLLMParodyGenerator:
    def __init__(self):
        # Configurable parameters
        self.episode_weight = 10
        self.pattern_strictness = 0.6
        self.tag_weight = 1
        self.max_tags = 3
        self.use_examples = True

        # Initialize components
        self.patterns = self.load_patterns()
        self.full_script = self.load_script()
        self.cache = {}
        self.valid_characters = [char.upper() for char in self.patterns.get('CHARACTER_SPECIFICS', {}).keys()]
        
        # Generation configuration (used during inference)
        self.generation_config = {
            "temperature": 1.5,
            "max_new_tokens": 1024,
            "top_p": 0.9,
            "repetition_penalty": 1.1,
            "do_sample": True
        }

        # Load local model and tokenizer with 8-bit quantization for fine-tuning
        model_path = "./gemma-2-Ataraxy-v4d-9B"  # Path to your saved model
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        
        try:
            # Attempt to load model in 8-bit mode with device mapping
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                load_in_8bit=True,              # Enable 8-bit loading
                device_map='auto'               # Automatically map layers to available devices
            )
            print("Model loaded in 8-bit mode with device mapping.")
        except Exception as e:
            print(f"8-bit loading failed: {str(e)}")
            print("Attempting to load model in float16 mode on CUDA.")
            try:
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    torch_dtype=torch.float16
                )
                self.model = self.model.to("cuda")
                print("Model loaded in float16 mode on CUDA.")
            except Exception as e2:
                print(f"Float16 loading failed: {str(e2)}")
                print("Attempting to load model on CPU in float32 mode.")
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    torch_dtype=torch.float32
                )
                self.model = self.model.to("cpu")
                print("Model loaded on CPU in float32 mode.")
        
        # Clear CUDA cache if available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

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

        base_prompt = f"""Create a parody scene based on this scenario: {user_input}

        Style Suggestions:
        Character vibes: {', '.join(self.patterns['GENERAL'][0]['tags'][:3])}
        {self._get_character_inspiration(characters)}
        Tone: Satirical, absurdist, with dark or dry humor
        Humor Style: South Park-style - irreverent, exaggerated, and often politically incorrect 

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

        Each scene should escalate tension and conclude with a comedic reversal or punchline.

        Comedic Conflict Ideas:
        - Each character has an exaggerated motivation or secret that drives them to behave absurdly.
        - Unexpected obstacles or bizarre coincidences heighten comedic tension.
        - Use comedic pacing—set up, escalate, and deliver a punchline—at least once per scene.

        Tags: Comedy, Adventure, Parody, Satire, Surreal Humour {', '.join(characters)}

        Character Backgrounds:
        {'\n'.join(character_profiles)}

        Story Context:
        {context_examples if context_lines else '(No direct context found)'}

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
        {self._get_style_examples()}

        Format output as:
        [CHARACTER]: [Dialogue]
        END SCENE"""

        return base_prompt

    def _get_character_inspiration(self, characters):
        """
        Generates inspiration suggestions for each character based on their personality tags.
        """
        inspirations = []
        for char in characters:
            tags = self.get_character_tags(char)[:2]  # Get up to 2 tags per character
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

        try:
            # Create a single prompt string
            system_prompt = "You are an expert parody writer creating funny scenes with Characters from Persona 3."
            full_prompt = f"{system_prompt}\n\n{prompt}"
            
            # Tokenize input
            inputs = self.tokenizer(full_prompt, return_tensors="pt")
            
            # Determine model's device
            model_device = next(self.model.parameters()).device
            
            # Move inputs to the model's device
            inputs = {key: value.to(model_device) for key, value in inputs.items()}
            
            # Generate response
            outputs = self.model.generate(
                **inputs,
                **self.generation_config
            )
            
            # Decode and clean response
            full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            raw_result = full_response[len(full_prompt):].strip()  # Remove input prompt
            result = self._clean_response(raw_result)
            
            self.cache[cache_key] = result
            return result
            
        except Exception as e:
            print(f"Generation Error: {str(e)}")
            traceback.print_exc()
            return "Could not generate parody - here's a fallback joke: Why did Aigis refuse to play cards? She kept getting dealt motherboard!"

    def _generate_refinement(self, original_input, previous_scene, notes):
        refinement_key = hashlib.md5(f"{previous_scene}{notes}".encode()).hexdigest()
        if refinement_key in self.cache:
            return self.cache[refinement_key]

        try:
            # Create a single prompt string for refinement
            refinement_prompt = f"Original scenario: {original_input}\nCurrent scene:\n{previous_scene}\n\nRevision notes: {notes}\n\nRevised scene:"
            
            # Determine model's device
            model_device = next(self.model.parameters()).device
            
            # Tokenize input
            inputs = self.tokenizer(refinement_prompt, return_tensors="pt").to(model_device)
            
            # Generate refined response
            outputs = self.model.generate(
                **inputs,
                **self.generation_config
            )
            
            # Decode and clean response
            full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            raw_result = full_response[len(refinement_prompt):].strip()
            result = self._clean_response(raw_result)
            
            self.cache[refinement_key] = result
            return result
            
        except Exception as e:
            print(f"Generation Error: {str(e)}")
            traceback.print_exc()
            return previous_scene

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

    def fine_tune_model(self, train_file_path, output_dir, epochs=3, batch_size=2, learning_rate=5e-5):
        """
        Fine-tunes the model using the provided training data.

        Args:
            train_file_path (str): Path to the training data file.
            output_dir (str): Directory to save the fine-tuned model.
            epochs (int): Number of training epochs.
            batch_size (int): Training batch size per device.
            learning_rate (float): Learning rate for the optimizer.
        """
        try:
            # Load dataset
            dataset = load_dataset('text', data_files={'train': train_file_path})
            train_dataset = dataset['train']

            # Tokenize the dataset
            def tokenize_function(examples):
                return self.tokenizer(examples['text'], return_special_tokens_mask=True)

            tokenized_datasets = train_dataset.map(tokenize_function, batched=True, remove_columns=["text"])

            # Initialize data collator
            data_collator = DataCollatorForLanguageModeling(
                tokenizer=self.tokenizer,
                mlm=False,
            )

            # Define Training Arguments
            training_args = TrainingArguments(
                output_dir=output_dir,
                overwrite_output_dir=True,
                num_train_epochs=epochs,
                per_device_train_batch_size=batch_size,
                learning_rate=learning_rate,
                fp16=True,  # Enable mixed precision
                logging_steps=10,
                save_steps=10_000,
                save_total_limit=2,
                optim="adamw_bnb_8bit",  # Use BitsAndBytes 8-bit Adam optimizer
            )

            # Initialize Trainer
            trainer = Trainer(
                model=self.model,
                args=training_args,
                train_dataset=tokenized_datasets,
                data_collator=data_collator,
                tokenizer=self.tokenizer,
            )

            # Start Training
            trainer.train()

            # Save the fine-tuned model
            trainer.save_model(output_dir)
            print(f"Model fine-tuned and saved to {output_dir}.")

        except Exception as e:
            print(f"Fine-Tuning Error: {str(e)}")
            traceback.print_exc()

if __name__ == "__main__":
    generator = LocalLLMParodyGenerator()
    generator.interactive_mode()

    # Example usage of fine-tuning (uncomment to use)
    # train_data_path = "path_to_your_training_data.txt"
    # fine_tuned_output_dir = "./fine_tuned_model"
    # generator.fine_tune_model(train_data_path, fine_tuned_output_dir, epochs=3, batch_size=2, learning_rate=5e-5)
