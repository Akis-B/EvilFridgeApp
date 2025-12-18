# Evil Fridge 

Upload a photo of your fridge, have a local vision model list everything it sees, then let an evil “fridge” spin a wheel to generate chaotic recipes or schemes. Everything runs locally.

## What’s inside
- Flask backend (`App.py`) serving the UI at `/`
- Vision: local `Qwen/Qwen2-VL-2B-Instruct` for image → text item extraction
- Text: local `cognitivecomputations/dolphin-2.6-mistral-7b` for recipe/chaos generation
- Frontend: `templates/index.html` + `static/js/app.js` + `static/css/style.css`
- Upload handling capped at 16MB; normalized images (RGB, max side 2048px)

## Requirements
- Python 3.8+
- RAM: ~8–12GB minimum (more helps); disk space for model downloads
- GPU optional; Apple Silicon uses MPS automatically. CPU works but is slower.
- Hugging Face token (`HF_TOKEN`) if the models require authentication

## Quick start
```bash
git clone <repo-url>
cd EvilFridgeApp\ L
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

# If torch didn’t install a compatible build, install the right wheel for your platform.
# Example (Apple Silicon):
# pip install --pre torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/nightly/cpu

export HF_TOKEN=<your_hf_token_if_needed>  # optional, only if the models need auth
python App.py
```
Open `http://localhost:5001` (or your `PORT` value) in the browser.

First run will download the vision and text models; keep internet on and allow time/disk space for the weights.

## Environment variables
- `VISION_MODEL_ID` (default `Qwen/Qwen2-VL-2B-Instruct`) — Hugging Face vision chat model
- `RECIPE_MODEL_ID` (default `cognitivecomputations/dolphin-2.6-mistral-7b`) — text generator
- `HF_TOKEN` — Hugging Face token if required for the chosen models
- `PORT` — Flask port (default `5001`)

## How to use
1) Start the server: `python App.py`  
2) In the UI, click “Play”, upload a JPG/PNG (<=16MB).  
3) The app lists detected fridge vs non-fridge items.  
4) Spin the wheel to generate one of three evil outputs (environmental destruction, mischief engineering, general chaos) using the local text model.

## API (if you want to call it directly)
- `POST /analyze` — form-data with `image` file. Returns JSON `{fridge_items: [...], non_fridge_items: [...]}`.
- `POST /chaos` — JSON `{"items": [...], "non_fridge_items": [...], "category": "environmental_destruction"|"weapon_manufacturing"|"general_chaos"}`. Returns `{"result": "...", "category": "..."}`.
- `POST /recipe` — JSON `{"items": [...]}`. Returns `{"recipe": "..."}`.

## Customization
- Vision prompt: edit `extract_items_from_image` in `App.py`.
- Swap models: set `VISION_MODEL_ID` / `RECIPE_MODEL_ID` env vars to any compatible HF models.
- UI: tweak `templates/index.html` and `static/css/style.css`; client logic in `static/js/app.js`.

## Troubleshooting
- Slow or OOM on startup: use a smaller model, lower `max_new_tokens`, or run on a GPU.
- Torch install issues: install the platform-specific torch wheel (CUDA/MPS/CPU) manually.
- Port in use: set `PORT=5002` (or another free port) before running `python App.py`.
