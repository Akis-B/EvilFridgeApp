from flask import Flask, render_template, request, jsonify
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoProcessor
from PIL import Image
import torch
import io
import os
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

hf_token = os.getenv("HF_TOKEN")

# Load local vision model (override via env VISION_MODEL_ID)
print("Loading vision model...")
vision_model_id = os.getenv("VISION_MODEL_ID", "Qwen/Qwen2-VL-2B-Instruct")
vision_device_map = "mps" if torch.backends.mps.is_available() else "auto"
vision_processor = AutoProcessor.from_pretrained(
    vision_model_id,
    trust_remote_code=True,
    token=hf_token,
)
vision_model = AutoModelForCausalLM.from_pretrained(
    vision_model_id,
    trust_remote_code=True,
    torch_dtype="auto",
    device_map=vision_device_map,
    token=hf_token,
    low_cpu_mem_usage=True,
)
print("Vision model loaded!")

# Load recipe text model (override via env RECIPE_MODEL_ID)
print("Loading recipe model...")
recipe_model_id = os.getenv("RECIPE_MODEL_ID", "cognitivecomputations/dolphin-2.6-mistral-7b")
recipe_device_map = "mps" if torch.backends.mps.is_available() else "auto"
recipe_tokenizer = AutoTokenizer.from_pretrained(
    recipe_model_id,
    trust_remote_code=True,
    token=hf_token,
    use_fast=False  # avoid tiktoken conversion requirement
)
recipe_model = AutoModelForCausalLM.from_pretrained(
    recipe_model_id,
    trust_remote_code=True,
    torch_dtype=torch.float16,
    device_map=recipe_device_map,
    token=hf_token,
    low_cpu_mem_usage=True
)
print("Recipe model loaded!")

MAX_IMAGE_SIDE = 2048


def normalize_image(image: Image.Image) -> Image.Image:
    """Ensure RGB format and constrain size to avoid huge buffers."""
    if image.mode != "RGB":
        image = image.convert("RGB")
    if max(image.size) > MAX_IMAGE_SIDE:
        image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), Image.Resampling.LANCZOS)
    return image


def extract_items_from_image(image: Image.Image) -> dict[str, list[str]]:
    """Run the vision model and return cleaned item names separated by location."""
    image = normalize_image(image)

    vision_prompt = (
        "Look carefully at this image and identify all visible food items, beverages, and anything else "
        "that exists with the fridge including people, plants, fridge magnets, furniture - literally anything. "
        "Categorize them into two lists:\n\n"
        "IN FRIDGE:\n"
        "- List every item you can see INSIDE the refrigerator (on shelves, in drawers, in door compartments)\n"
        "- Be specific about what you see (e.g., 'milk carton', 'orange juice', 'eggs', 'cheese')\n\n"
        "NOT IN FRIDGE:\n"
        "- List items that are visible in the image but OUTSIDE the refrigerator (on counters, tables, etc.)\n"
        "- Include any food, drinks, or products visible in the surrounding area\n\n"
        "Format: Write each item on a new line under the appropriate heading. Be thorough and list everything you can identify."
    )

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": vision_prompt},
            ],
        }
    ]

    chat_template = vision_processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = vision_processor(
        text=[chat_template],
        images=[image],
        return_tensors="pt",
    ).to(vision_model.device)

    pad_token_id = None
    if hasattr(vision_processor, "tokenizer"):
        pad_token_id = vision_processor.tokenizer.pad_token_id
    if pad_token_id is None:
        pad_token_id = vision_model.config.eos_token_id

    generated_ids = vision_model.generate(
        **inputs,
        max_new_tokens=768,
        do_sample=False,
        temperature=0.0,
        pad_token_id=pad_token_id,
    )
    generated_only_ids = generated_ids[:, inputs["input_ids"].shape[1]:]
    result = vision_processor.batch_decode(
        generated_only_ids, skip_special_tokens=True
    )[0].strip()

    # Parse the result to separate fridge vs non-fridge items
    fridge_items = []
    non_fridge_items = []
    current_category = None

    for line in result.split('\n'):
        line = line.strip()
        if not line:
            continue

        lower = line.lower()

        # Check for category headers
        if "in fridge" in lower and "not in fridge" not in lower:
            current_category = "fridge"
            continue
        elif "not in fridge" in lower:
            current_category = "non_fridge"
            continue

        # Skip instructional text
        if "analyze this image" in lower or "separate them" in lower or "provide only" in lower:
            continue

        # Clean the item name
        cleaned = line
        if cleaned[:1] in {"-", "•", "*"}:
            cleaned = cleaned[1:].strip()
        cleaned = re.sub(r'^\d+\s*[.)]\s*', '', cleaned)
        cleaned = cleaned.strip()

        if cleaned:
            if current_category == "fridge":
                fridge_items.append(cleaned)
            elif current_category == "non_fridge":
                non_fridge_items.append(cleaned)

    return {
        "fridge_items": fridge_items,
        "non_fridge_items": non_fridge_items
    }


def analyze_image_file(path: str) -> dict[str, list[str]]:
    """Open an image from disk and return detected items."""
    with open(path, "rb") as f:
        data = f.read()
    image = Image.open(io.BytesIO(data))
    return extract_items_from_image(image)


def generate_recipe_text(items: list[str]) -> str:
    """Generate a recipe from a list of items."""
    if not items:
        raise ValueError("No items provided for recipe generation.")

    prompt = (
        "You are an evil chef. Given the available ingredients from the fridge below, "
        "List a title, servings, ingredients from fridge with amounts, staple ingredients being used with amounts, and numbered steps. "
        "Keep it concise and practical. Be evil extreme and unhinged. Nothing you make actually has to lead to a recipe just evilness and chaos you love drugs, destruction and breaking the law and your recipes reflect that.\n\n"
        f"Ingredients from fridge: {', '.join(items)}\n\nRecipe:"
    )

    inputs = recipe_tokenizer(prompt, return_tensors="pt").to(recipe_model.device)
    output = recipe_model.generate(
        **inputs,
        max_new_tokens=400,
        temperature=0.7,
        top_p=0.9,
        do_sample=True,
    )
    generated = output[0][inputs.input_ids.shape[1]:]
    return recipe_tokenizer.decode(generated, skip_special_tokens=True).strip()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']

    if file.filename == '':
        return jsonify({'error': 'No image selected'}), 400

    if file:
        try:
            image = Image.open(io.BytesIO(file.read()))
            result = extract_items_from_image(image)

            return jsonify({
                'items': result['fridge_items'],
                'fridge_items': result['fridge_items'],
                'non_fridge_items': result['non_fridge_items']
            })

        except Exception as e:
            message = str(e)
            if "Invalid buffer size" in message:
                return jsonify({'error': 'The uploaded image appears corrupted or reports an impossible size. Please re-save the image (e.g., screenshot or re-export) and try again.'}), 400
            return jsonify({'error': message}), 500

@app.route('/recipe', methods=['POST'])
def generate_recipe():
    payload = request.get_json(force=True, silent=True) or {}
    items = payload.get('items', [])
    if not isinstance(items, list) or not items:
        return jsonify({'error': 'No items provided for recipe generation.'}), 400
    try:
        recipe_text = generate_recipe_text(items)
        return jsonify({'recipe': recipe_text})
    except Exception as e:
        msg = str(e)
        if "401" in msg or "Unauthorized" in msg:
            return jsonify({'error': 'Recipe model download requires access. Set HF_TOKEN or change RECIPE_MODEL_ID to a public model.'}), 500
        return jsonify({'error': f'Failed to generate recipe: {msg}'}), 500


def generate_chaos_text(items: list[str], non_fridge_items: list[str], category: str) -> str:
    """Create themed output based on the spin result."""
    if not items:
        raise ValueError("No items provided for generation.")

    category = category.lower()
    base = ", ".join(items)
    non_fridge_base = ", ".join(non_fridge_items) if non_fridge_items else "None"

    if category == "environmental_destruction":
        prompt = (
            "Think about which of the ingredients took the most carbon footprint to produce. "
            "The last step you generate is the most important make sure you use what you have made to outline you are creating the most havoc"
            "That means  calculating the recipe that takes up the most carbon footprint. Then give instructions on how to use the creation to destroy the environment if applicable.\n\n"
            "The last step is the most important explain how you are destroying the environment with this creation and give an estimate of how bad this recipe was for the environment. No more than 7 steps"
            f"Fridge items: {base}\n"
            f"Non-fridge items: {non_fridge_base}\n\nRecipe:"
        )
    elif category == "weapon_manufacturing":
        prompt = (
            "Design a weapon using the ingredients in the fridge. "
            "Think of what you can freeze to make bullets or what is outside the fridge that can be disassembled to make a weapon. Dont do more than 7 steps. "
            "Use up to 5 of these fridge items and outside items if they exist. Your recipe should not be actually edible, so using items like shoes or chairs is encouraged. The last step you generate is the most important make sure you use what you have made to outline you are creating the most havoc. Keep it concise.\n\n"
            f"Fridge items: {base}\n"
            f"Non-fridge items: {non_fridge_base}\n\nRecipe:"
        )
    elif category == "general_chaos":
        prompt = (
            "Think of the most chaotic and illegal recipe you can make using these ingredients from the fridge and out. "
            "Find a law that can be broken with your recipe. Maybe it can pertain to drug manufacturing. Dont do more than 7 steps"
            "Use up to 5 of these fridge items in absurd ways. Keep it short yet detailed.\n\n"
            "The last step you generate is the most important make sure you use what you have made to outline you are creating the most havoc"
            f"Fridge items: {base}\n"
            f"Non-fridge items: {non_fridge_base}\n\nRecipe:"
        )
    else:
        raise ValueError("Unknown category.")

    inputs = recipe_tokenizer(prompt, return_tensors="pt").to(recipe_model.device)
    output = recipe_model.generate(
        **inputs,
        max_new_tokens=960,
        temperature=0.9,
        top_p=0.9,
        do_sample=True,
    )
    generated = output[0][inputs.input_ids.shape[1]:]
    return recipe_tokenizer.decode(generated, skip_special_tokens=True).strip()


@app.route('/chaos', methods=['POST'])
def chaos():
    payload = request.get_json(force=True, silent=True) or {}
    items = payload.get('items', [])
    non_fridge_items = payload.get('non_fridge_items', [])
    category = payload.get('category', '')
    if not isinstance(items, list) or not items:
        return jsonify({'error': 'No items provided.'}), 400
    allowed = {"environmental_destruction", "weapon_manufacturing", "general_chaos"}
    if category not in allowed:
        return jsonify({'error': 'Invalid category.'}), 400
    try:
        text = generate_chaos_text(items, non_fridge_items, category)
        return jsonify({'result': text, 'category': category})
    except Exception as e:
        msg = str(e)
        if "401" in msg or "Unauthorized" in msg:
            return jsonify({'error': 'Recipe model download requires access. Set HF_TOKEN or change RECIPE_MODEL_ID to a public model.'}), 500
        return jsonify({'error': f'Failed to generate content: {msg}'}), 500


if __name__ == '__main__':
    # Serve the browser UI (original flow)
    port = int(os.getenv("PORT", 5001))
    # Disable Werkzeug reloader so checkpoint shards load only once when starting python App.py
    app.run(debug=True, host='0.0.0.0', port=port, use_reloader=False)
