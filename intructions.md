# Tinker 2: Plant Advisor
A chatbot that answers questions from a script is not an agent. An agent is a system that determines — given a goal and a set of tools — what to do next. Plant Advisor has access to two tools: a plant database and seasonal care data. Your job is to implement the tools and the loop that drives the agent to use them, observe how the LLM decides what to call and when, and confront what happens when a user asks about something the agent doesn't know.

🎯 Goals
By completing this activity, you will be able to:

Implement tool functions that retrieve structured data and return it to an agent loop.
Build a tool-calling agent loop using the Groq function calling API.
Design a graceful degradation response for the case where an agent's tools can't fulfill a request.

🪄 How this works: Work together as a group throughout the activity using the Driver/Navigator model. The Driver shares their screen and implements the solution while Navigators help guide decisions, ask questions, discuss tradeoffs, and troubleshoot challenges. At each checkpoint, pause to reflect on your group's progress, discuss key implementation decisions, and make sure everyone understands the solution before moving on.
🛠️ Tools and Setup

Fork the Plant Advisor starter repo and clone your fork locally.


Create and activate a virtual environment:

python -m venv .venv
source .venv/bin/activate          # Mac/Linux
source .venv/Scripts/activate      # Windows (Git Bash)
# or: .venv\Scripts\activate       # Windows (Command Prompt)

Install dependencies:

pip install -r requirements.txt

Copy .env.example to .env:

cp .env.example .env

Replace your_key_here with your key from console.groq.com.


Run the app:

python app.py
Plant Advisor will open in your browser. Type a question — you'll get the placeholder message until Milestone 2 is complete. That's expected.



Milestone 1: Implement the Tool Functions
⏰ ~20 min

The agent has two tools. get_seasonal_conditions is already implemented — your job is to implement lookup_plant, which is the harder of the two. Without a working lookup_plant, the agent loop has nothing to work with even after Milestone 2.

🧠 Before You Start
📔 Agents vs Chatbots

A chatbot takes a message, passes it to an LLM, and returns whatever the LLM says. It's a single function call. There's no decision-making beyond what the model does internally.

An agent is different. An agent has access to tools — functions that can look things up, fetch data, or take actions — and it selects dynamically which tools to call based on what the user asked. The same question might require calling one tool, two tools in sequence, or no tools at all. The agent figures that out on the fly.

Plant Advisor has two tools: one that looks up plant care data, and one that checks seasonal conditions. A user asking "How often should I water my pothos in winter?" needs both — the plant lookup gives the care requirements, and the seasonal check tells the agent what "winter" conditions actually look like right now. A user asking "What's a good plant for low light?" needs neither, because the answer doesn't require any external data.

The LLM is what makes these decisions. Your job in this lab is to build the tools the LLM can call (Milestone 1) and the loop that enables it to call them (Milestone 2).

📔 Tools and Tool Definitions

A tool in the context of an AI agent is a regular Python function — one that takes arguments, does something, and returns a result. What makes it a "tool" rather than just a function is that it's registered with the LLM via a tool definition: a structured description that tells the LLM what the function does, what arguments it takes, and when it should be called.

The description field in a tool definition is critical — it's literally what the LLM processes to determine whether to invoke this tool. A vague description produces unreliable tool selection.

Weak description: "Gets plant data"

Strong description:

"Looks up care requirements for a specific houseplant by name, including watering frequency, light needs, soil type, and common issues. Use this when the user mentions a specific plant by name."
The second version tells the LLM three things: what data the tool returns, what it takes as input, and when to use it. That level of specificity is what makes the agent call the right tool at the right time.

What correct tool output looks like:

lookup_plant("devil's ivy") should return something like:

{"found": true, "plant": {"display_name": "Pothos", "watering": "every 7-10 days", ...}}
lookup_plant("dragon tree") (not in the database) should return:

{"found": false, "message": "No plant matching 'dragon tree' found in the database."}
The found field is what the agent uses to determine what to do next — so the message in the found: false case matters. A helpful message gives the LLM something to work with; "not found" alone leaves the agent with nothing useful to say to the user.


Read the system design in specs/system-design.md. Read the whole thing before opening any code file — it describes what's already built, how the tool calling API works, and what you're responsible for implementing.


Open specs/tool-functions-spec.md. The get_seasonal_conditions section is already pre-filled — read through it, then open tools.py and read the implementation. Notice how it handles the valid-season vs. auto-detect branches and the detected_season flag. Understanding this pattern will help you design lookup_plant.


Work through the two blank fields for lookup_plant in the spec:

Alias matching approach — Open data/plants.json and look at the structure. Plant keys are slugs like "snake_plant", but users might say "sansevieria" or "mother-in-law's tongue" and expect the same result. Before filling in this field, ask your AI tool to help you think through the options:

"Given a dict of plant slugs like 'snake_plant', each with a display_name and an aliases list, what's the most reliable way to do case-insensitive name matching across all three?"
"What Python data structure would make alias lookups faster if this database grew to thousands of plants?"
Not-found message — this field deserves more thought than it looks like it does. The message you return is what the LLM reads when a plant isn't in the database. Work backward from what a useful agent response looks like.

⚠️ AI usage guardrail: The AI prompts above are for understanding tradeoffs, not for generating your implementation. Understand the options first, make a decision, and write it in the spec. A spec field that says "use whatever AI suggested" isn't a design decision — it's a placeholder.

Implement lookup_plant() in tools.py. Share the alias matching approach and search order fields from your spec with your AI tool — those are the decisions the code needs to reflect.

⚠️ Watch Out: Normalize the input before matching. A user might type "Pothos", "POTHOS", or " pothos " and expect the same result. Handle casing and whitespace before any comparison.

Test your tools. In your terminal, run:

python -c "from tools import lookup_plant, get_seasonal_conditions; print(lookup_plant(\"devil's ivy\")); print(get_seasonal_conditions())"

Fill in the Implementation Notes for both functions in specs/tool-functions-spec.md.

🤔 Test Yourself
lookup_plant() returns {"found": False, ...} when a plant isn't in the database, but get_seasonal_conditions() always returns valid data. Why the asymmetry?
Because lookup_plant() queries a finite local database, while get_seasonal_conditions() computes its result from the system calendar — so the second function always has something valid to return regardless of what it receives as input
Because seasons are a closed set with four known values — every possible input maps to a valid output — while plant names are open-ended user input that may have no match in the database
Because returning {"found": False} lets the LLM acknowledge the missing plant gracefully and fall back to general knowledge, whereas returning an error for an unrecognized season would leave the agent with no useful context at all
Because lookup_plant() is designed to be called first in the agent loop, and the found: False result acts as a signal for the loop to skip the seasonal lookup entirely and go straight to generation

📍 Checkpoint
lookup_plant("devil's ivy") should return {"found": True, "plant": {...}} with the full Pothos entry. get_seasonal_conditions() should return a full season dict with "detected_season": True. If lookup returns found: False for a known alias, your alias matching logic needs another look.

If found is False for a plant you know is in the database: Print the normalized input and compare it to the keys and aliases in plants.json. The most common cause is a case mismatch or a whitespace character that wasn't stripped.
If get_seasonal_conditions() raises a KeyError: Check that your season detection logic is returning one of the exact keys that exist in _season_data. Print the detected season value before the lookup to confirm.


Milestone 2: Build the Agent Loop
⏰ ~20 min

The tools work. Now you need to build the loop that lets the LLM use them. This is the architectural center of the activity. Make sure you understand the full loop before implementing any part of it!

🧠 Before You Start
📔 How the Function Calling API Works

Before implementing a single line of the agent loop, you need to understand the full cycle — because the loop has to handle each step correctly, in the right order.

The messages list is the backbone of every interaction. It's a list of message objects that grows with each turn:

[
  {"role": "system",    "content": "You are a plant care assistant..."},
  {"role": "user",      "content": "How do I care for my pothos?"},
  {"role": "assistant", "tool_calls": [{"id": "call_abc", "function": {"name": "lookup_plant", "arguments": "{\"plant_name\": \"pothos\"}"}}]},
  {"role": "tool",      "tool_call_id": "call_abc", "content": "{\"found\": true, \"plant\": {...}}"},
  {"role": "assistant", "content": "Your pothos needs watering every 7-10 days..."}
]
The full cycle for one turn:

Send the messages list to the API with your tool definitions attached
The API returns an assistant message — it either contains content (a final answer) or tool_calls (a request to invoke one or more tools)
If tool_calls: append the assistant message to your messages list, execute each requested tool, and append a tool result message for each — then go back to step 1
If content: you have the final response — return it
Why the order of appending matters:

Each tool result message contains a tool_call_id that references the tool call in the preceding assistant message. If you append the tool result before the assistant message that requested it, the API can't match the result to its request — it'll either error or produce garbage. The assistant message must come first, always.

What correct loop behavior looks like:

dispatch_tool() prints to the terminal every time a tool is called. When your loop is working, you should see lines like:

→ Tool call: lookup_plant({'plant_name': 'pothos'})
→ Tool call: get_seasonal_conditions({})
If you ask a plant question and see no tool calls in the terminal, the LLM is answering from its general knowledge rather than using the tools — which means the system prompt needs to be more explicit, not the loop logic.

The infinite loop risk:

The loop runs until the LLM stops requesting tools. But if a tool returns an empty result and the LLM keeps retrying, the loop never exits. MAX_TOOL_ROUNDS is the safety valve — when it's hit, the loop should exit gracefully rather than crash.


Open specs/agent-loop-spec.md. Most fields are already pre-filled — read through them carefully, then complete the two blank fields before writing any code:

Loop termination conditions — describe how you'll detect each of the two exit conditions (no tool calls, and MAX_TOOL_ROUNDS reached) and what you return in each case. Before filling this in, ask your AI tool to surface the failure modes: "Here's my plan for the run_agent loop: [describe your approach]. What edge cases could cause this to loop forever, return an empty string, or raise an exception?" Revise your plan until it handles all the cases.

Extracting the final text response — describe which field on the response object holds the string you should return, and how to access it.


Implement run_agent() in agent.py. Share your completed spec with your AI tool — the pre-filled fields are the blueprint. Verify the generated code matches every field you specified before accepting it.

💡 Restart the app after implementing run_agent(). Changes to agent.py aren't picked up until you stop the app (Ctrl+C) and run python app.py again.
💡 Tip: dispatch_tool() already prints to the terminal every time a tool is called. Once your loop is working, you'll see lines like → Tool call: lookup_plant({'plant_name': 'monstera'}) appear in the terminal as each question is answered. If you're not seeing any output, the loop isn't calling tools yet.
Ask Plant Advisor a few questions and watch the terminal:
"How do I care for my pothos?" — which tools get called? In what order?
"How often should I water my snake plant in winter?" — does the agent call both tools? Why or why not?
"My calathea has brown edges" — does it look up the plant? Does it check the season?
Watch the → Tool call lines. If you expect a tool to fire and it doesn't, the LLM may be answering from general knowledge rather than using the tool — which means the system prompt needs to be more explicit, not the loop.

🌱 Going Deeper: The pattern you just built — messages list, LLM call, tool dispatch, append and repeat — is the same core loop behind production agent systems like LangChain's AgentExecutor, LlamaIndex's ReActAgent, and OpenAI Assistants. The APIs differ, but the pattern is identical. Understanding it from scratch means you can reason about and debug those frameworks rather than just using them as black boxes.
Fill in the Implementation Notes in specs/agent-loop-spec.md — specifically the tool call trace for a working query.
🤔 Test Yourself
Your agent calls two tools in sequence: first lookup_plant("zz plant"), then get_seasonal_conditions(). After each tool call, the result needs to be appended to the messages list before the LLM can use it. Why does the assistant message (the one containing the tool call request) need to be appended to the list before the tool result — rather than after?
The LLM uses the assistant message's position in the list to determine how much context weight to assign each tool result — appending it after the result would cause the model to assign zero weight to the tool output
The tool result message contains a tool_call_id that references the specific call recorded in the preceding assistant message — without that message appearing first, the API can't match the result to the request that generated it
The messages list is processed sequentially, and the model builds its understanding of the conversation incrementally — receiving a tool result before the request that prompted it would put the conversation in an inconsistent internal state
The Groq API validates that each tool result is immediately preceded by the assistant message that requested it, and rejects the entire request if any result appears out of that strict alternating order

📍 Checkpoint
Ask Plant Advisor: "How should I water my monstera this time of year?" You should see two tool calls in the terminal: one to lookup_plant and one to get_seasonal_conditions. The response should cite the monstera's specific watering guidance and connect it to the current season. If you only see one tool call, check the system prompt — the agent may not be consistently calling both tools for season-specific questions.

If you see no tool calls at all: The loop is likely not passing the tool definitions to the API call. Check that TOOL_DEFINITIONS is included in your _client.chat.completions.create() call.
If you get an API error about message ordering: You're appending the tool result before the assistant message. Check the order of your messages.append() calls inside the loop.
If the loop runs but returns an empty string: Your final response extraction is pulling from the wrong field. Print the full API response object to inspect its structure — the content is at response.choices[0].message.content.


Milestone 3: Design for the Unknown
⏰ ~10 min

Your agent can answer questions about plants in its database. Now find out what it does when it can't.

🧠 Before You Start
📔 Graceful Degradation

Every knowledge-limited system has edges — places where the data runs out. What makes a system trustworthy or embarrassing is almost always how it handles those edges, not how well it handles the common case.

There's a spectrum of responses when a user asks about something the agent doesn't know:

Confidently wrong (worst): The agent invents care instructions for bird of paradise as if it had real data. Sounds helpful. Is actively harmful.

Silent failure: The agent says "I don't have information about that plant" and stops. Technically honest, but leaves the user with nothing.

Graceful degradation (best): The agent acknowledges what it doesn't know and offers something genuinely useful given that limitation — whether that's general advice, a redirect, or a clarifying question.

Example:

"Bird of paradise isn't in my plant database, but based on your description it sounds like a large tropical species. Tropicals generally need bright indirect light and consistent moisture without waterlogging. For specific care data, the American Horticultural Society has detailed profiles."

The behavior you get depends on where you intervene in the system. The lookup_plant() return value sets the context the LLM sees. The system prompt tells the LLM what to do with a found: False result. The LLM's own defaults fill in whatever neither of those covers. Knowing which layer controls the behavior is what lets you improve it deliberately rather than by trial and error.


Trigger the not-found case. Click the "How do I care for my string of pearls?" example question below the chat input — or ask about any plant you know isn't in the database. Watch the terminal: what does lookup_plant return? What does the agent say?


Evaluate the response. Is it actually helpful? A user with a string of pearls on their shelf probably wants more than "I don't have data on that plant." Talk through these questions with your group:

Where does the behavior you just observed come from — the lookup_plant() return value, the system prompt, or the LLM's own defaults?
What's the difference between the agent saying "I don't know" and the agent saying "I don't have specific data, but here's what I can offer"?
If you wanted to improve it, which layer would you change first, and why?

Try one targeted change if time allows. Options:

Tweak the not-found message you wrote in lookup_plant() to give the LLM more to work with
Add a sentence to the system prompt in agent.py that explicitly instructs the agent on how to handle unknown plants
Restart the app after any change and compare the response to what you saw before.

🎯 Real World: This is one of the defining design decisions in every knowledge-limited AI system. Retrieval-augmented assistants, customer service bots, and enterprise copilots all have edges where their data runs out — and the difference between a trustworthy product and an embarrassing one is often just how gracefully it handles those edges. "I don't know" is acceptable. "I don't know, but here's how you can find out / here's what I can offer" is better. Confidently wrong is unacceptable.
Discussion Prompts
Take a few minutes to talk through these with your group.

Your agent has two tools, but lookup_plant already includes brief seasonal notes in the plant data it returns. Did your agent consistently call get_seasonal_conditions for season-specific questions, or sometimes skip it? What does that tell you about how the LLM interprets tool descriptions? How would you change the tool description or system prompt to make the behavior more predictable?

Right now, if a user asks "what plants are good for low light?", the agent has no good way to answer — it can't query the plant database by attribute, only by name. How would you add that capability? What would the tool look like? What would the spec for it look like?

The agent loop runs until the LLM stops calling tools. What would have to be true for an agent loop to run forever? How does MAX_TOOL_ROUNDS help — and what should the agent do when it hits that limit?

🤔 Test Yourself
Your agent calls lookup_plant("pothos") and gets back a successful result. The LLM then calls get_seasonal_conditions() with no argument. Which of the following best describes why the LLM made a second tool call instead of answering immediately?
The LLM determined — from the user's question or the tool description — that seasonal context was relevant to giving a complete answer, so it chose to call a second tool before responding
The first tool returned found: True, and the agent loop is designed to always make a follow-up call when the initial lookup succeeds, to enrich the response with additional context
lookup_plant returned the plant's base care data but flagged that seasonal adjustments were required, prompting the agent to retrieve the missing context before generating a response
The system prompt instructed the agent to always call both tools before answering any plant care question, so the second call was required regardless of what the first returned
You implement run_agent() and it works for simple questions, but for complex ones it sometimes returns the wrong content or an empty string. The most likely root cause is:
The final response extraction is pulling from the wrong field on the API response — returning the raw message object or tool_calls instead of message.content, which works when there's only one call but fails when the loop runs multiple iterations
MAX_TOOL_ROUNDS is set too low for complex questions that require multiple tool calls, causing the loop to exit before the LLM has gathered enough context to generate a complete response
The loop is checking the wrong condition to detect when the LLM has finished calling tools — it exits one iteration too early and returns the assistant message with tool_calls still set, rather than the final content response
Tool results are being appended to the messages list in the wrong order — the result appears before the assistant message that requested it, which the API handles tolerantly for single-tool calls but not for multi-tool sequences
A user asks your Plant Advisor about a plant not in the database. Your agent returns: "Based on my knowledge, here is detailed care advice for your rare orchid species..." — drawing entirely on the LLM's training data rather than the tool results. What is the most direct fix?
Update lookup_plant() to raise an exception when a plant isn't found, which would halt the agent loop and prevent the LLM from generating a response based on training data
Update the system prompt to explicitly instruct the agent not to answer from general knowledge when lookup_plant returns found: False — and to acknowledge the gap while offering general guidance instead
Improve the not-found message in lookup_plant() to include the instruction "do not use outside knowledge — acknowledge this plant is not in your database," so the LLM reads it directly in the tool result
Add a third tool that retrieves live plant data from an external source, so the agent always has a real data source to fall back on when the local database doesn't have a match

📍 Checkpoint
Ask Plant Advisor: "How do I care for my bird of paradise?" The response should clearly acknowledge the plant isn't in the database but still offer something useful — whether that's general tropical plant care advice, a suggestion about what to look for, or a redirect to a better source. It should not invent specific care instructions for bird of paradise as if it had real data.

If the agent still invents specific data after your fix: The system prompt change may not be specific enough. Instead of "try to be helpful even when you don't have data," try "when lookup_plant returns found: False, do not invent specific care instructions — instead, offer general guidance for the plant type and acknowledge what you don't know."


Optional Challenges
If your group finishes early, pair up and take one of these on together:


Add a get_plant_list() tool. Implement a third tool that returns the names and difficulty levels of all plants in the database. Add it to TOOL_DEFINITIONS and dispatch_tool(). Then ask "what plants do you know about?" and "what's a good beginner plant?" — watch the terminal to see when the agent calls it. Update the spec files to document the new tool.


Add conversation memory. Right now, the agent uses the full Gradio history but doesn't do anything smart with it. What if it could track which plants a user has mentioned before and proactively connect them? For example: a user asks about their pothos, then later asks a general question about watering — could the agent say "since you mentioned you have a pothos..."? Think through the spec before implementing anything.


Stress-test the loop. Try to get the agent to hit MAX_TOOL_ROUNDS. What question or sequence of questions causes the most tool calls? What does the agent return when it hits the limit? Is that the right behavior — and if not, how would you change it?