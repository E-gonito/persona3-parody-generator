=== PERSONA 3 PARODY GENERATOR CUSTOMIZATION GUIDE ===
A parody script generator for Persona 3 Parodies (Specifically in the style of MasterDank47) built with python. Using API calls to DeepSeek.

[API SETTINGS]
File: persona_parody_generator.py
Location: generate_parody_scenario() method

Adjust these values:

- model: "deepseek-chat" (try other available models)
- temperature: 0.85 (range 0-2, 0.7=structured, 1.5=chaotic)
- max_tokens: 500 (response length, 500≈3 paragraphs)
- top_p: 1.0 (diversity control, 0.9=strict, 1.0=creative)

[CONTENT RULES]
File: generate_scenario_prompt() method
Edit the guidelines section to modify:

- Humor types required
- Dialogue length limits
- Comedy style requirements

[CHARACTER BEHAVIOR]
File: parody_patterns.json
Structure:
{
"CHARACTER_SPECIFICS": {
"CHARACTER_NAME": [
{
"pattern": "regex triggers",
"tags": ["associated_memes"]
}
]
}
}

[COMMON CUSTOMIZATIONS]

1. Longer Scenes:

- Set max_tokens: 750
- Reduce temperature: 0.7

2. Darker Humor:
   Edit system message to:
   "You are a expert parody writer specializing in dark comedy..."

3. Game Mechanics Focus:
   Add to GAMEPLAY_MECHANICS in parody_patterns.json:
   {
   "pattern": "social link",
   "tags": ["#sigma_grindset"]
   }

[VALIDATION]

1. Data Loading Check:
   Add to load_patterns():
   print(f"Loaded {len(patterns['CHARACTER_SPECIFICS'])} characters")

2. Prompt Inspection:
   Add to generate_parody_scenario():
   print("\n--- SENT PROMPT ---\n", prompt, "\n--- END PROMPT ---")

3. Tag Verification:
   Test with:
   print("YUKARI TAGS:", self.get_character_tags("YUKARI"))

[EXAMPLE CUSTOMIZATION]
Goal: Dramatic 4-character scenes

1. Increase response length:
   max_tokens: 800

2. Add drama tags:
   In GENERAL patterns:
   {
   "pattern": "drama|conflict",
   "tags": ["#soap_opera_mode"]
   }

3. Expand context matching:
   Change find_relevant_context() return to:
   return context_lines[-8:]

=== END GUIDE ===
