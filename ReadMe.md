# System Context Conversation Bot with Speaking Avatar

A Gradio app that lets you chat with an LLM (Groq) and get a text reply plus a **speaking-avatar video** of the response, powered by [Tavus](https://tavus.io).

## Features

- **Chat**: Send a message and optional system context; pick a Groq model and conversation tone.
- **Text response**: The chatbot replies using Swarmauri (SimpleConversationAgent + MaxSystemContextConversation).
- **Optional avatar video**: Check "Generate avatar video" to send the reply to Tavus and show the video when ready (polling). Uncheck for text-only replies.
- **Structured code**: Config (`config.py`), Tavus client (`tavus_client.py`), and agent logic (`agent_service.py`) are separate from the Gradio UI (`app.py`) for easier testing and maintenance.

## Requirements

- Python 3.10+
- [Groq](https://console.groq.com) API key
- [Tavus](https://tavus.io) API key and a **Replica** (for the speaking avatar)

## Setup

1. **Clone or enter the project directory**
   ```bash
   cd chat_app
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python3 -m venv chat_ai_venv
   source chat_ai_venv/bin/activate   # Linux/macOS
   # or: chat_ai_venv\Scripts\activate   # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   Create a `.env` file in the project root with:
   ```env
   GROQ_API_KEY=your_groq_api_key
   TAVUS_API_KEY=your_tavus_api_key
   TAVUS_REPLICA_ID=your_tavus_replica_id
   ```
   - **GROQ_API_KEY**: From [Groq Console](https://console.groq.com).
   - **TAVUS_API_KEY**: From [Tavus](https://tavus.io) (API keys).
   - **TAVUS_REPLICA_ID**: Your Replica ID from the Tavus dashboard (required for video generation).

## Run

```bash
python3 app.py
```

The app runs at `http://127.0.0.1:7860` and prints a public Gradio share URL. Open either in a browser to use the bot.

## Usage

1. **Your message**: Type your question or prompt.
2. **System context**: Optional instructions (e.g. "You are a helpful assistant.").
3. **Model**: Choose a Groq model from the dropdown.
4. **Tone**: e.g. Friendly, Formal, Neutral, Professional.
5. **Generate avatar video**: Check to request a Tavus speaking-avatar video of the reply; uncheck for text-only.
6. Click **Send**; you get the text reply and, if video was requested, the video when ready.

Video generation can take a few minutes; the app polls every 10 seconds for up to 20 minutes. Logs go to the terminal (level set by config).

## Troubleshooting

- **"One or more API keys are missing"**: Set `GROQ_API_KEY` and `TAVUS_API_KEY` in `.env`.
- **"Failed to queue video generation" / "Invalid replica_id"**: Set a valid `TAVUS_REPLICA_ID` from your Tavus account.
- **401 / Invalid token**: Regenerate your Tavus API key and update `TAVUS_API_KEY`.
- **No video, only text**: Check the terminal for Tavus errors (e.g. invalid replica, script too long, or rate limits).

## License

Use and modify as needed for your project.
