from flask import Flask, render_template, request, jsonify
from transformers import AutoProcessor, AutoModelForVision2Seq
from PIL import Image
import torch
import io
import os

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Load model once when app starts
print("Loading model... This may take a minute...")
model_id = "Qwen/Qwen2-VL-7B-Instruct"
processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
model = AutoModelForVision2Seq.from_pretrained(
    model_id,
    trust_remote_code=True,
    torch_dtype=torch.float16,
    device_map="auto"
)
print("Model loaded successfully!")

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
            # Read image from upload
            image = Image.open(io.BytesIO(file.read()))
            
            # Prepare messages for Qwen2-VL
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": "List all the items in this fridge. Provide only the item names, one per line, with no additional description or explanation."}
                    ]
                }
            ]
            
            # Process and generate
            text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = processor(
                text=[text],
                images=[image],
                return_tensors="pt",
                padding=True
            ).to(model.device)
            
            output = model.generate(**inputs, max_new_tokens=512)
            result = processor.decode(output[0], skip_special_tokens=True)
            
            # Extract just the list part (remove the prompt echo)
            # The result usually includes the prompt, so we need to extract just the response
            if "List all the items" in result:
                result = result.split("List all the items")[-1].strip()
            
            # Split into individual items
            items = [item.strip() for item in result.split('\n') if item.strip()]
            
            return jsonify({'items': items})
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
