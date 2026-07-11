import json
import os
import gradio as gr
from config import DATA_PATH
from agent import run_agent

# Load plant list for the sidebar
with open(os.path.join(DATA_PATH, "plants.json"), encoding="utf-8") as f:
    _plants = json.load(f)

_plant_names = sorted(p["display_name"] for p in _plants.values())

EXAMPLE_QUESTIONS = [
    "How do I care for my pothos?",
    "My monstera leaves are turning yellow. What's wrong?",
    "How often should I water my snake plant in winter?",
    "I just got a fiddle leaf fig. Where should I put it?",
    "What's the difference between overwatering and underwatering a peace lily?",
    "My orchid finished blooming. Will it bloom again?",
    "How do I fix a succulent that's stretching toward the light?",
    "My calathea has brown edges. Is it the humidity?",
    "What are some good low-light plants for my apartment?",
    "Why does my boston fern keep losing fronds?",
    "How do I care for my string of pearls?",   # not in database — tests graceful degradation
]


def chat(message: str, history: list) -> str:
    """Pass the user message and conversation history to the agent."""
    return run_agent(message, history)


# ──────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────

with gr.Blocks(
    title="Plant Advisor",
    theme=gr.themes.Default(
        primary_hue="green",
        secondary_hue="emerald",
        neutral_hue="stone",
        font=[gr.themes.GoogleFont("Inter"), "sans-serif"],
    ),
) as demo:

    gr.Markdown(
        """
# 🌿 Plant Advisor
*Ask me anything about caring for your houseplants.*
"""
    )

    with gr.Row():
        # Sidebar
        with gr.Column(scale=1, min_width=220):
            gr.Markdown("### 🪴 Plants in My Database")
            gr.Markdown(
                "\n".join(f"- {name}" for name in _plant_names),
                label="Plants",
            )
            gr.Markdown("---")
            gr.Markdown(
                "**Tip:** Ask about any plant above by its common name, "
                "scientific name, or nickname (e.g., *devil's ivy*, "
                "*mother-in-law's tongue*, *swiss cheese plant*)."
            )

        # Chat
        with gr.Column(scale=3):
            chatbot = gr.ChatInterface(
                fn=chat,
                type="messages",
                examples=EXAMPLE_QUESTIONS,
                chatbot=gr.Chatbot(
                    height=520,
                    placeholder="<em>Ask me about your plants...</em>",
                    show_label=False,
                    type="messages",
                ),
                textbox=gr.Textbox(
                    placeholder="e.g. How often should I water my monstera?",
                    show_label=False,
                    scale=7,
                    submit_btn="Ask",
                ),
            )

if __name__ == "__main__":
    demo.launch()
