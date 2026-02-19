import os
import gradio as gr
import importlib
import requests
import time
from typing import TYPE_CHECKING

from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVUS_API_KEY = os.getenv("TAVUS_API_KEY")
TAVUS_REPLICA_ID = os.getenv("TAVUS_REPLICA_ID")

if not GROQ_API_KEY or not TAVUS_API_KEY:
    raise ValueError("One or more API keys are missing. Please set them in your .env file.")

if TYPE_CHECKING:
    from swarmauri.agents import SimpleConversationAgent  # type: ignore[import-untyped]
    from swarmauri.conversations import MaxSystemContextConversation  # type: ignore[import-untyped]
    from swarmauri.llms import GroqModel  # type: ignore[import-untyped]
    from swarmauri.messages import SystemMessage  # type: ignore[import-untyped]

_modules_map = {
    "GroqModel": "swarmauri.llms.GroqModel",
    "SystemMessage": "swarmauri.messages.SystemMessage",
    "SimpleConversationAgent": "swarmauri.agents.SimpleConversationAgent",
    "MaxSystemContextConversation": "swarmauri.conversations.MaxSystemContextConversation",
}
for _name, _module_path in _modules_map.items():
    _mod = importlib.import_module(_module_path)
    globals()[_name] = getattr(_mod, _name)

llm = GroqModel(api_key=GROQ_API_KEY)
allowed_models = llm.allowed_models if llm.allowed_models else ["default-model"]


def load_model(selected_model):
    try:
        return GroqModel(api_key=GROQ_API_KEY, name=selected_model)
    except Exception as e:
        print(f"Error loading model: {e}")
        return None


def generate_avatar_video(text):
    try:
        script = (text or "").strip()
        if not script:
            print("Video generation skipped: script is empty.")
            return None, None
        url = "https://tavusapi.com/v2/videos"
        payload = {"replica_id": TAVUS_REPLICA_ID, "script": script}
        headers = {"x-api-key": TAVUS_API_KEY, "Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)
        try:
            response_data = response.json()
        except Exception:
            response_data = {}
        if not response.ok:
            msg = response_data.get("error") or response_data.get("message") or response.reason or f"HTTP {response.status_code}"
            print(f"Tavus API error: {msg}")
            return None, None
        if response_data.get("status") != "queued":
            msg = response_data.get("error") or response_data.get("message") or f"Unexpected status: {response_data.get('status')}"
            print(f"Failed to queue video generation: {msg}")
            return None, None
        video_id = response_data.get("video_id")
        if not video_id:
            print("Failed to queue video: no video_id in response.")
            return None, None
        video_check_url = f"https://tavusapi.com/v2/videos/{video_id}"
        return video_id, video_check_url
    except Exception as e:
        print(f"Error generating avatar video: {e}")
        return None, None


def converse(input_text, system_context, model_name, tone):
    conversation = MaxSystemContextConversation()
    llm = load_model(model_name)
    if not llm:
        return "Error loading language model.", gr.update(value=None)
    # Initialize conversation agent
    agent = SimpleConversationAgent(llm=llm, conversation=conversation)
    agent.conversation.system_context = SystemMessage(content=f"{system_context}\nTone: {tone}")
    result = agent.exec(input_text)
    # Generate avatar video
    video_id, video_check_url = generate_avatar_video(result)
    if not video_id:
        return result, gr.update(value=None, label="Error generating video.")
    # Initial response with loading message
    loading_message = gr.update(value="Video is being generated, please wait...", visible=True)
    yield result, loading_message
    # Poll for video status (max 20 minutes), every 10 seconds
    headers = {"x-api-key": TAVUS_API_KEY}
    poll_interval = 10
    max_wait_seconds = 20 * 60  # 20 minutes
    elapsed = 0
    while elapsed < max_wait_seconds:
        time.sleep(poll_interval)
        elapsed += poll_interval
        try:
            status_response = requests.get(video_check_url, headers=headers).json()
        except Exception as e:
            print(f"Error checking video status: {e}")
            yield result, gr.update(value=None, label="Error checking video status.", visible=True)
            return
        status = status_response.get("status")
        print(f"Video status: {status}")
        if status == "ready":
            download_url = status_response.get("download_url")
            if not download_url:
                yield result, gr.update(value=None, label="Video ready but no download URL.", visible=True)
                return
            yield result, gr.update(value=download_url, visible=True)
            return
        if status in ("error", "deleted"):
            msg = status_response.get("status_details") or f"Video status: {status}"
            print(msg)
            yield result, gr.update(value=None, label=msg, visible=True)
            return
        print("Video generation in progress...")
    yield result, gr.update(value=None, label="Video generation timed out.", visible=True)


with gr.Interface(
    fn=converse,
    inputs=[
        gr.Textbox(label="Your Input", placeholder="Type your message here..."),
        gr.Textbox(label="System Context", placeholder="Enter the system context..."),
        gr.Dropdown(label="Model Name", choices=allowed_models, value=allowed_models[0]),
        gr.Dropdown(label="Conversation Tone", choices=["Friendly", "Formal", "Casual", "Neutral", "Professional", "Empathetic", "Humorous", "Angry", "Romantic"], value="Neutral")
    ],
    outputs=[
        gr.Textbox(label="Chatbot Response"),
        gr.Video(label="Avatar Video", autoplay=True)
    ],
    title="System Context Conversation Bot with Speaking Avatar",
    description="Interact with the chatbot, and receive a lifelike video response."
) as demo:
    demo.launch(share=True, debug=True)