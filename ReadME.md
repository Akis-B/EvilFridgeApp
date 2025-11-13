# Fridge Item Analyzer Web App

A web-based application that uses AI to analyze fridge images and list all items detected.

## Features
- Upload images via click or drag-and-drop
- Real-time image preview
- AI-powered item detection using Qwen2-VL-7B model
- Clean, modern user interface
- Mobile-friendly responsive design

## Prerequisites
- Python 3.8 or higher
- At least 16GB RAM (for running the 7B model)
- GPU recommended (but CPU will work, just slower)

## Installation

1. Install the required packages:
```bash
pip install -r requirements.txt
```

2. If you're using a Mac with Apple Silicon:
```bash
pip install torch torchvision torchaudio
```

## Running the App

1. Start the Flask server:
```bash
python app.py
```

2. Open your web browser and go to:
```
http://localhost:5000
```

3. Upload a fridge image and click "Analyze Image"

## How It Works

1. User uploads an image through the web interface
2. The image is sent to the Flask backend
3. The Qwen2-VL model analyzes the image
4. Items are extracted and displayed as a list

## Project Structure
```
.
├── app.py              # Flask backend application
├── templates/
│   └── index.html      # Web interface
├── uploads/            # Temporary upload folder (created automatically)
└── requirements.txt    # Python dependencies
```

## Notes

- The model loads when the app starts, which takes 1-2 minutes
- First image analysis may be slower as the model initializes
- Max upload size is 16MB
- Supported formats: JPG, PNG, JPEG

## Deployment Options

### For Local Use:
Run as shown above with `python app.py`

### For Production:
Consider using:
- **Gunicorn** as the WSGI server
- **Nginx** as a reverse proxy
- Deploy on platforms like:
  - AWS EC2 (with GPU instance for better performance)
  - Google Cloud Platform
  - Heroku (though the model may be too large)
  - DigitalOcean

### Example with Gunicorn:
```bash
pip install gunicorn
gunicorn -w 1 -b 0.0.0.0:5000 app:app --timeout 120
```

Note: Use `-w 1` (1 worker) to avoid loading the model multiple times in memory.

## Customization

### Change the prompt:
Edit line 56 in `app.py` to modify what the model looks for:
```python
{"type": "text", "text": "Your custom prompt here"}
```

### Modify the UI:
Edit `templates/index.html` to change colors, layout, or styling.

### Change the model:
Replace `model_id` in `app.py` with a different Hugging Face model (must be compatible with Vision2Seq).

## Troubleshooting

**Model loading is slow:**
- This is normal for large models. Consider using a smaller model or GPU acceleration.

**Out of memory errors:**
- Try using a smaller model or reducing `max_new_tokens` in the generate call.
- Close other applications to free up RAM.

**Port already in use:**
- Change the port in `app.py`: `app.run(port=5001)`

## License
This project uses the Qwen2-VL model which has its own license terms. Please check Hugging Face for details.
