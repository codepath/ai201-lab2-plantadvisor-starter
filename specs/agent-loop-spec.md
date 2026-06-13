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

These are two different *exits* from the loop, not two checks side by side. The
function returns a `str` (the final text), never the messages list.

Failure modes this plan defends against:
- **Loop forever** — impossible: bounded by `range(MAX_TOOL_ROUNDS)`, not `while True`. No counter to forget to increment.
- **Empty return** — both exits guard `content` with `or FALLBACK`; a no-tool-call message can still have `content == None`.
- **Exception** — the LLM call and per-tool-call arg parsing are wrapped, so an API error, malformed tool-call JSON, or missing arg degrades to an error result / fallback instead of crashing the turn.

```
FALLBACK = "Sorry — I couldn't finish that request. Please try rephrasing."

try:
    for round_num in range(MAX_TOOL_ROUNDS):
        response = client.chat.completions.create(
            model=LLM_MODEL, messages=messages,
            tools=TOOL_DEFINITIONS, tool_choice="auto",
        )
        assistant_message = response.choices[0].message

        # Condition (a): no tool calls → the model has its final answer.
        if not assistant_message.tool_calls:
            return assistant_message.content or FALLBACK

        # Otherwise append the assistant message + run the tools, then loop again.
        messages.append(assistant_message)
        for tool_call in assistant_message.tool_calls:
            try:
                raw_args = tool_call.function.arguments
                tool_args = json.loads(raw_args) if raw_args else {}
                tool_result = dispatch_tool(tool_call.function.name, tool_args)
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                tool_result = json.dumps({"error": f"Bad tool call: {e}"})
            messages.append({
                "role": "tool", "tool_call_id": tool_call.id, "content": tool_result,
            })

    # Condition (b): loop ran out → MAX_TOOL_ROUNDS used up and the model STILL
    # wanted tools. Force one text-only answer; its content may be empty, so guard.
    final = client.chat.completions.create(
        model=LLM_MODEL, messages=messages, tool_choice="none",
    )
    return final.choices[0].message.content or FALLBACK

except Exception:
    # Any API/network/parse error: degrade to a fallback, never raise into the UI.
    return FALLBACK
```

- **(a)** detected *inside* the loop via `not assistant_message.tool_calls`; return `assistant_message.content or FALLBACK`.
- **(b)** detected by the `for` loop *finishing*. The last message still wanted tools, so its `content` is usually empty — don't return it. One final `tool_choice="none"` call makes the model summarize as text; `or FALLBACK` guarantees a non-empty return.
---

### Extracting the final text response

*Once the loop exits because there are no more tool calls, how do you extract the text content from the response object? What field holds the string you should return?*

The text lives at `response.choices[0].message.content` — the same `assistant_message`
object used to check `tool_calls`, so once `tool_calls` is falsy, read `.content` off it.

```python
assistant_message = response.choices[0].message
return assistant_message.content or FALLBACK
```

`content` is the assistant's text reply (a `str`). It can be `None` — notably when
`tool_calls` is present (the model "spoke" only by requesting tools). On the no-tool-call
exit it's normally a real string, but guard with `or FALLBACK` anyway, because the API
can return an empty/`None` content on a stop, and the contract forbids returning empty.

---

## Implementation Notes

*Fill this in after implementing and testing.*

**Trace of a working agent turn (what tools were called and in what order):**

```
Query: "How should I care for my calathea?"
Round 1 tool call: [tool name, args]
Round 2 tool call: [tool name, args] (if any)
Final response: [brief description]
```

**What happens when you ask about a plant that isn't in the database?**

```
[describe the behavior you observed]
```

**One thing about the tool call API that surprised you:**

```
[your answer here]
```
