# Spec: `run_agent()`

**File:** `agent.py`
**Status:** Partially pre-filled — complete the two blank fields before implementing

---

## Purpose

Orchestrate a single conversational turn for the Plant Advisor agent. Given a user message and the conversation history, call the LLM with available tools, execute any tool calls the LLM requests, and return the final text response.

This is the core of what makes Plant Advisor an *agent* rather than a simple chatbot: the ability to decide which tools to call, use their results to inform its response, and loop until it has everything it needs.

---

## Input / Output Contract

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_message` | `str` | The user's current message |
| `history` | `list` | Gradio conversation history — list of `{"role": ..., "content": ...}` message dicts |

**Output:** `str`

The agent's final text response for this turn. Should never be empty — if something goes wrong, return a user-readable fallback message.

---

## Design Decisions

*Read `specs/system-design.md` (especially the "How the Groq Tool Calling API Works" section) before reviewing these. Complete the two blank fields before writing any code.*

---

### Messages list structure

The messages list must start with the system prompt, then replay the conversation
history, then add the new user message. The app creates its chat UI with
`type="messages"`, so Gradio history arrives as a list of API-format dicts with
`role` and `content` keys. Gradio may include extra keys (like `metadata`), so
copy only the two fields the API expects:

```python
messages = [{"role": "system", "content": SYSTEM_PROMPT}]

for msg in history:
    messages.append({"role": msg["role"], "content": msg["content"]})

messages.append({"role": "user", "content": user_message})
```

---

### Initial LLM call

Pass the model, the messages list, the tool definitions, and `tool_choice="auto"`
so the LLM can decide whether to call a tool or respond directly:

```python
response = client.chat.completions.create(
    model=LLM_MODEL,
    messages=messages,
    tools=TOOL_DEFINITIONS,
    tool_choice="auto",
)
```

---

### Detecting tool calls in the response

The response object has a `choices` list. Index 0 gives the assistant message.
Check its `tool_calls` attribute — if it's truthy, the LLM wants to call tools:

```python
assistant_message = response.choices[0].message

if not assistant_message.tool_calls:
    # No tool calls — LLM has a final answer
    ...
```

---

### Appending the assistant message

When there are tool calls, append the full assistant message object to `messages`
**before** appending any tool results. The API requires this ordering — a tool
result message must immediately follow the assistant message that requested it:

```python
messages.append(assistant_message)  # must come first
```

---

### Executing and appending tool results

For each tool call, extract the name and arguments, call `dispatch_tool()`, and
append the result as a `"tool"` role message. The `tool_call_id` links this result
back to the specific tool call that requested it.

⚠️ For a no-argument tool call (like `get_seasonal_conditions` with no season),
the model may send `arguments` as the JSON string `"null"` — `json.loads` turns
that into `None`, not `{}`. Normalize before dispatching:

```python
for tool_call in assistant_message.tool_calls:
    tool_name = tool_call.function.name
    raw_args = tool_call.function.arguments
    tool_args = json.loads(raw_args) if raw_args else {}
    if not isinstance(tool_args, dict):
        tool_args = {}
    tool_result = dispatch_tool(tool_name, tool_args)

    messages.append({
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": tool_result,
    })
```

---

### Loop termination conditions

*The loop should stop when: (a) the LLM returns a response with no tool calls, OR (b) the MAX_TOOL_ROUNDS limit is reached. Describe how you will detect each condition and what you will return in each case.*

```
The loop is `for _ in range(MAX_TOOL_ROUNDS):` — each iteration is one LLM call.

(a) No tool calls: after each call, check `if not assistant_message.tool_calls:`.
    If true, the LLM has a final answer — return `assistant_message.content`
    immediately, exiting the loop early (this is the common case).

(b) MAX_TOOL_ROUNDS reached: if every iteration of the loop had tool calls
    (the LLM never returned a tool-call-free response within the budget),
    the `for` loop exits normally without an early return. After the loop,
    return a fixed fallback string (the same one used for the API-error
    case below) so the Output Contract's "never empty" guarantee holds.

A try/except around the LLM call also returns this fallback string if the
API call itself raises (see note below) — also part of "if something goes
wrong, return a user-readable fallback message."
```

---

### Extracting the final text response

*Once the loop exits because there are no more tool calls, how do you extract the text content from the response object? What field holds the string you should return?*

```
`response.choices[0].message.content` — i.e. `assistant_message.content`,
the same message object whose `.tool_calls` we already checked. When
`tool_calls` is empty/None, `.content` holds the LLM's final answer text.
```

---

## Implementation Notes

*Fill this in after implementing and testing.*

**Trace of a working agent turn (what tools were called and in what order):**

```
Query: "How should I care for my calathea?"
Round 1 tool call: lookup_plant({"plant_name": "calathea"}) -> found, full
  calathea care dict returned.
Round 2: assistant_message.tool_calls is empty -> loop exits.
Final response: a grounded answer citing the calathea's watering, light,
  humidity, temperature, and seasonal_notes from the looked-up data.
```

**What happens when you ask about a plant that isn't in the database?**

```
Query: "How do I care for my venus flytrap?"
lookup_plant returns {"found": false, "name": "venus flytrap", "message": "..."}.
The agent reads the not-found message, tells the user it has no specific data
for that plant, and falls back to general carnivorous-plant care advice based
on what the user described -- matching the SYSTEM_PROMPT's instruction to say
so clearly and offer general guidance.
```

**One thing about the tool call API that surprised you:**

```
The Groq API can return a 400 `tool_use_failed` error directly from
`chat.completions.create()` -- not a normal response with empty tool_calls
-- when the model emits a malformed function call (e.g. `<function=...>` text
instead of structured JSON, or omits a parameter the tool schema marks as
required). This happened on a multi-tool query where the model tried to call
get_seasonal_conditions with no arguments, but TOOL_DEFINITIONS marked
"season" as required even though the function treats it as optional/
auto-detected. Without a try/except around the API call, this raises an
exception that would crash run_agent() entirely -- the loop's "no tool_calls"
check never even runs.

Two fixes went in: (1) the try/except around the LLM call returns the
fallback string for any such failure, and (2) the root cause was corrected
by changing TOOL_DEFINITIONS' "required" list for get_seasonal_conditions
from ["season"] to [] so it matches the function's actual (optional)
contract. After fix (2), the same multi-tool query succeeds:
get_seasonal_conditions({}) auto-detects the season, then both plants are
looked up, all in one round.
```
