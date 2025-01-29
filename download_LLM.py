# Download and save script
from transformers import AutoTokenizer, AutoModelForCausalLM

# Configuration
model_name = "lemon07r/Gemma-2-Ataraxy-v4d-9B"
save_directory = "./" # Save to current directory

# Download model and tokenizer
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# Save to directory
tokenizer.save_pretrained(save_directory)
model.save_pretrained(save_directory)

print(f"Model and tokenizer saved to {save_directory}")

