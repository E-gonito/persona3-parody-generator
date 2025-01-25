=== PERSONA 3 PARODY GENERATOR CUSTOMIZATION GUIDE ===
A parody script generator for Persona 3 Parodies (Specifically in the style of MasterDank47) built with python. Using API calls to DeepSeek.

[API SETTINGS]
File: persona_parody_generator.py
Location: generate_parody_scenario() method

Adjust these values:

Example Configurations:

Strict Pattern Adherence
self.pattern_strictness = 0.9
self.tag_weight = 2.0
self.max_tags = 4
self.use_examples = True

Creative Mode
self.pattern_strictness = 0.3  
self.tag_weight = 1.2
self.max_tags = 2
self.use_examples = False

Balanced Default
self.pattern_strictness = 0.7
self.tag_weight = 1.5  
self.max_tags = 3
self.use_examples = True
