from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

device = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Using device: {device}")

model_name = "microsoft/phi-2"

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32)
model.to(device)

#prompt = """Generate a short detective story with a quiet great detective investigating a mysterious murder in a small town. Include multiple suspects with distinct motives. Perspective: the detective. Length: 1000-1200 words."""
prompt = """You are a creative writer. Create a rough outline for a short detective story set in a small town, featuring a quiet but brilliant detective, murder and inheritance. Define the outline as a series of events as they unfold, including motives and leads required for the investigation."""
# prompt = """Generate a short detective story from the detective's perspective using the following Outline:
# Length: 1000-1200 words."""

inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

output_tokens = model.generate(
    **inputs,
    max_new_tokens=1200,
    temperature=0.9,
    top_p=0.95,
    do_sample=True,
    pad_token_id=tokenizer.eos_token_id
)

story = tokenizer.decode(output_tokens[0], skip_special_tokens=True)
print(story)