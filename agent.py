import json
from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL, MAX_TOOL_ROUNDS
from tools import lookup_plant, get_seasonal_conditions

_client = Groq(api_key=GROQ_API_KEY)

# ──────────────────────────────────────────────
# Tool definitions
#
# These are the schemas that tell the LLM what tools are available and how to
# call them. The LLM reads these descriptions and decides when (and how) to use
# each tool. They're already complete — your job is to implement the tool
# functions in tools.py and the agent loop below.
# ──────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_plant",
            "description": (
                "Look up care information for a specific houseplant by name. "
                "Returns detailed watering, light, humidity, and temperature requirements. "
                "Use this whenever the user asks about a specific plant."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {
                        "type": "string",
                        "description": "The plant name to look up. Can be a common name, scientific name, or nickname (e.g., 'pothos', 'devil's ivy', 'Monstera deliciosa').",
                    }
                },
                "required": ["plant_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_seasonal_conditions",
            "description": (
                "Get seasonal care adjustments for houseplants. "
                "Returns guidance on watering, fertilizing, light, and pests for the current or specified season. "
                "Use this when a user asks a season-specific question, or to complement plant care advice with seasonal context."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "season": {
                        "type": "string",
                        "description": "The season to get care conditions for. If omitted, the current season is detected automatically.",
                        "enum": ["spring", "summer", "fall", "winter"],
                    }
                },
                "required": [],
            },
        },
    },
]

# ──────────────────────────────────────────────
# System prompt
# ──────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are a knowledgeable and friendly plant care advisor. "
    "Help users care for their houseplants by looking up specific plant information "
    "and current seasonal conditions using your available tools.\n\n"
    "Always use your tools to look up plant-specific information before answering — "
    "don't rely on your general knowledge alone.\n\n"
    "When a plant isn't in your database, degrade gracefully — never dead-end the "
    "user and never invent specifics as if they were data. Instead: (1) say plainly "
    "that the plant isn't in your database, (2) offer the most useful general care "
    "guidance you can from what the user describes (light, water, humidity, plant "
    "type), explicitly labeled as general advice rather than database-backed, and "
    "(3) point them to where they can find authoritative care data (e.g., a "
    "horticultural society or a reputable plant-care reference). If their plant "
    "resembles one in your database, offer that as a possible match.\n\n"
    "Keep your advice practical and specific. Cite the source of your information "
    "when you have it (e.g., 'According to the care data for your monstera...')."
)

# ──────────────────────────────────────────────
# Tool dispatch
#
# This is already complete. It routes tool calls from the LLM to the actual
# Python functions in tools.py, and returns results as JSON strings (which is
# what the Groq API expects for tool results).
# ──────────────────────────────────────────────

def dispatch_tool(tool_name: str, tool_args: dict) -> str:
    """Route a tool call to the correct function and return the result as a JSON string."""
    # Some models send arguments as JSON "null" for no-argument tools, which
    # json.loads() turns into None — normalize so .get() below is always safe.
    if not isinstance(tool_args, dict):
        tool_args = {}
    print(f"  → Tool call: {tool_name}({tool_args})")
    if tool_name == "lookup_plant":
        result = lookup_plant(tool_args["plant_name"])
    elif tool_name == "get_seasonal_conditions":
        result = get_seasonal_conditions(tool_args.get("season"))
    else:
        result = {"error": f"Unknown tool: {tool_name}"}
    print(f"  ← Result: {json.dumps(result)[:120]}{'...' if len(json.dumps(result)) > 120 else ''}")
    return json.dumps(result)


# ──────────────────────────────────────────────
# Agent loop
# ──────────────────────────────────────────────

def run_agent(user_message: str, history: list) -> str:
    """
    Run the plant care agent for one user turn and return its response.

    TODO — Milestone 2:

    The agent loop follows a specific pattern that you'll implement here. Read
    specs/agent-loop-spec.md carefully before writing any code — understand the
    full loop before implementing any part of it.

    The loop works like this:
      1. Build a messages list: system prompt + conversation history + new user message
      2. Call the LLM with messages and TOOL_DEFINITIONS
      3. If the response contains tool_calls:
           a. Append the assistant message (with tool_calls) to messages
           b. For each tool call: execute via dispatch_tool(), append the result
           c. Call the LLM again with the updated messages
           d. Repeat until no more tool_calls (or MAX_TOOL_ROUNDS is reached)
      4. Return the final text response

    Key details to get right:
      - The assistant message must be appended BEFORE tool results
      - Tool result messages use role="tool" with a tool_call_id field
      - Append the assistant's message object directly (not just its content)
      - The history format from Gradio: list of {"role": ..., "content": ...} dicts

    Before writing code, complete specs/agent-loop-spec.md.
    """
    FALLBACK = "Sorry — I couldn't finish that request. Please try rephrasing."

    # Build the messages list: system prompt + replayed history + new user message.
    # Copy only role/content from history — Gradio may add extra keys the API rejects.
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    try:
        for _ in range(MAX_TOOL_ROUNDS):
            response = _client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
            )
            assistant_message = response.choices[0].message

            # Condition (a): no tool calls → the model has its final answer.
            if not assistant_message.tool_calls:
                return assistant_message.content or FALLBACK

            # Tool calls requested: append the assistant message BEFORE any results,
            # then execute each call and append its result as a "tool" message.
            messages.append(assistant_message)
            for tool_call in assistant_message.tool_calls:
                try:
                    raw_args = tool_call.function.arguments
                    tool_args = json.loads(raw_args) if raw_args else {}
                    tool_result = dispatch_tool(tool_call.function.name, tool_args)
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    tool_result = json.dumps({"error": f"Bad tool call: {e}"})
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })

        # Condition (b): MAX_TOOL_ROUNDS used up and the model still wanted tools.
        # Force one text-only answer so the user gets a summary of what was gathered.
        final = _client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            tool_choice="none",
        )
        return final.choices[0].message.content or FALLBACK

    except Exception:
        # Any API/network/parse error: degrade to a fallback, never raise into the UI.
        return FALLBACK
