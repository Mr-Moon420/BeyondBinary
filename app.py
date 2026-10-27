import os
import sys

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

from backend.main import app as fastapi_app
import gradio as gr

# Minimal Gradio interface mounted on /gradio so HF Gradio runner is satisfied
with gr.Blocks(title="BeyondBinary - Media Credibility API") as demo:
    gr.Markdown("# ⚖️ BeyondBinary Media Credibility System")
    gr.Markdown(
        "Welcome to the BeyondBinary API engine! "
        "The full interactive editorial newsroom is live on the homepage: "
        "[Open BeyondBinary App](/)"
    )

# Mount Gradio onto the existing FastAPI application at /gradio
app = gr.mount_gradio_app(fastapi_app, demo, path="/gradio")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=7860)
