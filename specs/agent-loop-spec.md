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
(a) No tool calls: after every API call, check
    response.choices[0].message.tool_calls. If it's None/empty, the LLM has a
    final answer — return its content immediately (with a fallback string if
    content is somehow empty, so the function never returns "").

(b) MAX_TOOL_ROUNDS reached: structure the loop as
    `for _round in range(MAX_TOOL_ROUNDS)` so it can't run forever. If the
    loop exhausts all rounds with the LLM still requesting tools, make one
    final API call WITHOUT the tools parameter — the model can't request
    another tool, so it must generate a text answer from whatever context it
    has gathered. Return that, or a user-readable fallback if it's empty.

Edge cases handled: empty content on a no-tool-call response (the `or
fallback` guard), arguments arriving as JSON "null" for no-arg tools
(normalized to {} before dispatch), and any Groq API exception (caught;
returns a friendly error message instead of crashing the Gradio app).
```

---

### Extracting the final text response

*Once the loop exits because there are no more tool calls, how do you extract the text content from the response object? What field holds the string you should return?*

```
The final text lives at response.choices[0].message.content — the same
assistant message object whose tool_calls we checked; when tool_calls is
empty, its content attribute holds the answer string. Return
`assistant_message.content or <fallback message>` to guard against a None
or empty content field.
```

---

## Implementation Notes

*Fill this in after implementing and testing.*

**Trace of a working agent turn (what tools were called and in what order):**

```
Query: "How should I care for my calathea?"
Round 1 tool call: lookup_plant({'plant_name': 'calathea'})
Round 2 tool call: none — the LLM answered in text after one lookup
Final response: cited the calathea care data (filtered water, low-to-medium
indirect light, >50% humidity) and prefixed it with "According to the care
data for your Calathea..."

Season-specific query: "How should I water my monstera this time of year?"
Round 1 tool call: lookup_plant({'plant_name': 'monstera'})
Round 2 tool call: get_seasonal_conditions({})
Final response: combined the monstera watering data (top 2 inches dry,
every 1-2 weeks) with the auto-detected Summer conditions (water more often
in heat).
```

**What happens when you ask about a plant that isn't in the database?**

```
Asked "How do I care for my bird of paradise?" — lookup_plant returned
{"found": false, ...} with the not-found message. The agent acknowledged the
plant isn't in its database and offered general guidance, but it still
drifted into specific claims from training data (scientific name, "repot
every 2-3 years"). That's the graceful-degradation gap Milestone 3
addresses: the tool result and system prompt need to steer harder against
inventing specifics.
```

**One thing about the tool call API that surprised you:**

```
You append the SDK's assistant message *object* (ChatCompletionMessage)
directly into a list that otherwise holds plain dicts, and the client
serializes it correctly — mixing the two felt wrong but is the intended
pattern. Also, for a no-argument tool call the arguments field is the JSON
string "null", and json.loads("null") gives None rather than {} — without
normalizing, dispatch would crash on .get().
```
