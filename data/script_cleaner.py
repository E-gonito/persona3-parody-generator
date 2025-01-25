import re

def clean_script(raw_script):
    # Original cleaning steps
    cleaned_script = re.sub(r'\*.*\*', '', raw_script)
    cleaned_script = re.sub(r'\+.*\+', '', cleaned_script)
    cleaned_script = re.sub(r'\[.*\]\n{.*}', '', cleaned_script)
    cleaned_script = re.sub(r'<.*>', '', cleaned_script)
    cleaned_script = re.sub(r'\(.*\)', '', cleaned_script)
    cleaned_script = re.sub(r'\{.*\}', '', cleaned_script)
    cleaned_script = re.sub(r'>.*', '', cleaned_script)
    cleaned_script = re.sub(r'========\n\*(\d{1,2}/\d{1,2}/\d{2})\*', r'[\1]', cleaned_script)
    cleaned_script = re.sub(r'\[(.*)\]', r'[\1]', cleaned_script)
    cleaned_script = re.sub(r'([A-Za-z]+ [A-Za-z]+):', lambda m: m.group(1).upper() + ':', cleaned_script)
    cleaned_script = re.sub(r'([A-Za-z]+):', lambda m: m.group(1).upper() + ':', cleaned_script)
    cleaned_script = re.sub(r'\.{3,}', '...', cleaned_script)
    cleaned_script = re.sub(r'\n\s*\n', '\n', cleaned_script)
    cleaned_script = cleaned_script.strip()

    # Additional optimization steps
    lines = cleaned_script.split('\n')
    optimized_lines = []
    
    scene_pattern = re.compile(r'SCENE: (.+)')
    action_pattern = re.compile(r'ACTION: (.+)')
    character_pattern = re.compile(r'^([A-Za-z\s.]+):')
    choice_trigger = re.compile(r'^Main:$')
    scene_separator = re.compile(r'-{3,}')
    
    current_scene = None
    in_choice = False
    choice_number = 1

    for line in lines:
        stripped = line.strip()
        
        if scene_separator.fullmatch(stripped):
            if current_scene:
                optimized_lines.append(f'\n=== {current_scene.upper()} ===\n')
                current_scene = None
            continue
            
        scene_match = scene_pattern.match(stripped)
        if scene_match:
            current_scene = scene_match.group(1).strip('\\').strip()
            continue

        action_match = action_pattern.match(stripped)
        if action_match:
            optimized_lines.append(f'[{action_match.group(1)}]')
            continue

        char_match = character_pattern.match(stripped)
        if char_match:
            character = char_match.group(1).upper()
            dialogue = character_pattern.sub('', stripped).strip()
            optimized_lines.append(f'{character}: {dialogue}')
            continue

        if choice_trigger.match(stripped):
            in_choice = True
            choice_number = 1
            optimized_lines.append('CHOICE:')
            continue
            
        if in_choice:
            if stripped.startswith('Yukari') or stripped.startswith('Mitsuru'):
                in_choice = False
            else:
                if stripped and not stripped.startswith('['):
                    optimized_lines.append(f'{choice_number}. {stripped}')
                    choice_number += 1
                continue

        if stripped:
            if stripped.startswith('[') and stripped.endswith(']'):
                optimized_lines.append(stripped)
            else:
                optimized_lines.append(stripped)

    return '\n'.join(optimized_lines)

def load_script(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def save_script(cleaned_script, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(cleaned_script)

def main(input_file, output_file):
    raw_script = load_script(input_file)
    cleaned_script = clean_script(raw_script)
    save_script(cleaned_script, output_file)
    print(f"Script cleaned and saved to {output_file}")

if __name__ == "__main__":
    input_file = "episode_4.txt"
    output_file = "cleaned_persona3_script.txt"
    main(input_file, output_file)