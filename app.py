"""
Gradio UI for the System Context Conversation Bot with Speaking Avatar.
"""
import logging
from typing import Any, Generator, Optional

import gradio as gr

from agent_service import get_available_models, run_conversation
from config import get_config
from tavus_client import TavusClient

# Configure logging before other imports that may log
logging.basicConfig(
    level=getattr(logging, get_config().log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Constants for UI
TONE_CHOICES = [
    "Friendly", "Formal", "Casual", "Neutral", "Professional",
    "Empathetic", "Humorous", "Angry", "Romantic",
]
DEFAULT_TONE = "Neutral"


def _converse(
    input_text: str,
    system_context: str,
    model_name: str,
    tone: str,
    generate_video: bool,
) -> Generator[tuple[Any, Any], None, None]:
    """
    One turn: run conversation, optionally queue video and poll until ready.
    Yields (text_output, video_component_update) for progressive UI updates.
    """
    # 1) Run LLM conversation
    result_text, err = run_conversation(
        user_input=input_text or "",
        system_context=system_context or "",
        model_name=model_name,
        tone=tone or DEFAULT_TONE,
    )
    if err:
        yield result_text or err, gr.update(value=None, label=err, visible=True)
        return
    if not result_text:
        yield "No response from the model.", gr.update(value=None, visible=True)
        return

    # 2) Optional video
    if not generate_video:
        yield result_text, gr.update(value=None, visible=False)
        return

    client = TavusClient()
    create_result = client.create_video(result_text)
    if create_result.error:
        yield result_text, gr.update(
            value=None, label=f"Video: {create_result.error}", visible=True
        )
        return

    # Show loading state
    yield result_text, gr.update(
        value="Video is being generated, please wait...",
        visible=True,
    )

    # Poll until ready or terminal state
    for status_result in client.wait_for_video(create_result.status_url):
        if status_result.status == "ready" and status_result.download_url:
            yield result_text, gr.update(
                value=status_result.download_url, visible=True
            )
            return
        if status_result.status in ("error", "deleted"):
            msg = status_result.status_details or f"Video {status_result.status}"
            logger.warning("Video failed: %s", msg)
            yield result_text, gr.update(value=None, label=msg, visible=True)
            return
        if status_result.status == "timeout":
            yield result_text, gr.update(
                value=None,
                label=status_result.status_details or "Video generation timed out.",
                visible=True,
            )
            return
        # Still generating
        logger.debug("Video status: %s", status_result.status)


def _build_interface() -> gr.Blocks:
    """Build and return the Gradio interface."""
    try:
        models = get_available_models()
    except Exception as e:
        logger.warning("Could not load models: %s", e)
        models = ["default-model"]

    with gr.Blocks(
        title="Conversation Bot with Speaking Avatar",
        theme=gr.themes.Soft(),
    ) as demo:
        gr.Markdown(
            "## System Context Conversation Bot with Speaking Avatar\n"
            "Chat with the model and optionally get a speaking-avatar video of the reply."
        )
        with gr.Row():
            with gr.Column(scale=1):
                input_text = gr.Textbox(
                    label="Your message",
                    placeholder="Type your message here...",
                    lines=3,
                )
                system_context = gr.Textbox(
                    label="System context (optional)",
                    placeholder="e.g. You are a helpful assistant.",
                    lines=2,
                )
                model_name = gr.Dropdown(
                    label="Model",
                    choices=models,
                    value=models[0] if models else "default-model",
                )
                tone = gr.Dropdown(
                    label="Tone",
                    choices=TONE_CHOICES,
                    value=DEFAULT_TONE,
                )
                generate_video = gr.Checkbox(
                    label="Generate avatar video (Tavus)",
                    value=True,
                )
                submit_btn = gr.Button("Send", variant="primary")

            with gr.Column(scale=1):
                response_text = gr.Textbox(
                    label="Chatbot response",
                    lines=10,
                    interactive=False,
                )
                video_out = gr.Video(
                    label="Avatar video",
                    autoplay=True,
                    visible=True,
                )

        submit_btn.click(
            fn=_converse,
            inputs=[
                input_text,
                system_context,
                model_name,
                tone,
                generate_video,
            ],
            outputs=[response_text, video_out],
        )

    return demo


def main() -> None:
    """Run the Gradio app."""
    demo = _build_interface()
    demo.launch(
        share=True,
        debug=True,
        server_name="0.0.0.0",
    )


if __name__ == "__main__":
    main()
