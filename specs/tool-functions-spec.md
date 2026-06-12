# Spec: Tool Functions

**File:** `tools.py`
**Status:** `get_seasonal_conditions` — Pre-implemented, read through. `lookup_plant` — complete spec fields before implementing.

---

## Purpose

These two functions are the tools the agent can call. They retrieve structured data from the local plant database and seasonal data files and return it to the agent loop, which passes it to the LLM as context for generating a response.

---

## Function 1: `lookup_plant()`

### Input / Output Contract

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `plant_name` | `str` | The plant name as entered by the user or chosen by the LLM — may be any casing, common name, scientific name, or alias |

**Output:** `dict`

When the plant is **found**, return:
```python
{"found": True, "plant": <the full plant dict from _plant_db>}
```

When the plant is **not found**, return:
```python
{"found": False, "name": <normalized input>, "message": <helpful string>}
```

---

### Design Decisions

*Complete the two blank fields below before writing code. The others are pre-filled for you.*

---

#### Input normalization

Strip leading/trailing whitespace and convert to lowercase before any comparison.

```python
normalized = plant_name.strip().lower()
```

---

#### Search order

Search in this order: direct key → display name → scientific name → aliases.
Keys are the fastest lookup (O(1) dict access), so check those first. Display
names are the next most likely match for clean user input. Scientific names
matter because the tool definition tells the LLM it can pass them. Aliases are
the broadest net, so they go last.

```
1. Direct key match: normalized in _plant_db
2. Display name match: plant["display_name"].lower() == normalized
3. Scientific name match: plant["scientific_name"].lower() == normalized
4. Alias match: normalized in [alias.lower() for alias in plant["aliases"]]
```

---

#### Alias matching approach

*Aliases are stored as a list of strings. How will you check if the normalized input matches any alias in the list? Write your approach in pseudocode or plain English.*

```
For each plant in _plant_db, iterate through its aliases list and compare
each alias lowercased against the normalized input. If any alias matches,
return that plant. A linear scan is fine at 15 plants; if the database grew
to thousands, build a precomputed dict mapping every lowercased key, name,
and alias to its plant slug for O(1) lookups.
```

---

#### Not-found message

*When a plant isn't found, the agent will read your message and use it to decide what to tell the user. Write the exact string you'll return — make it useful to the agent, not just to a human reading logs.*

```
"No plant matching '{normalized}' found in the database. Do not invent specific
care data (watering schedules, exact temperatures, fertilizing intervals) for
this plant. Acknowledge the gap, offer general care principles for its broader
plant type if the user's description makes that clear, and suggest a detailed
source for specifics. If helpful, mention similar plants that ARE in the
database: {comma-separated display names}."
```

*(Milestone 1 refinement: dropped the original "the data referenced is located
in data/plants.json" sentence — the LLM reads this message and could echo an
internal file path to the user, which isn't actionable for them.)*

*(Milestone 3 refinement: the first version just said the plant wasn't found
and suggested retrying. Observed behavior: the agent acknowledged the gap but
still invented specifics from training data ("repot every 2-3 years"). The
message now steers the LLM directly — no invented specifics, offer general
principles, and list the plants that ARE available so it can suggest
alternatives. Paired with a matching system-prompt instruction in agent.py.)*

---

#### Implementation Notes

*Fill this in after implementing and running the app.*

**Test: does `"devil's ivy"` return the pothos entry?**
```
yes — matched via the aliases tier, returns {"found": True, "plant": {...Pothos...}}
```

**Test: does `"SNAKE PLANT"` return the snake plant entry?**
```
yes — lowercased to "snake plant", matched via the display-name tier
(the direct key tier misses it because the db key is "snake_plant" with an underscore)
```

**One edge case you discovered while implementing:**
```
Typographic (curly) apostrophes: phone keyboards auto-insert ’ instead of ',
so "devil’s ivy" failed the alias match against "devil's ivy" in plants.json.
Fixed by replacing ’ with ' during input normalization. Also observed that
"zz plant" (space) misses the direct key "zz_plant" but is caught by the
display-name tier — the multi-tier search order covers the slug/space mismatch.
```

---

## Function 2: `get_seasonal_conditions()`

### Input / Output Contract

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `season` | `str \| None` | One of `"spring"`, `"summer"`, `"fall"`, `"winter"`, or `None` to auto-detect |

**Output:** `dict`

The full season dict from `_season_data`, plus one additional field:

| Added field | Type | Value |
|-------------|------|-------|
| `"detected_season"` | `bool` | `True` if auto-detected from the month; `False` if season was passed as an argument |

---

### Design Decisions

*This function is pre-implemented — read through these fields and the code before working on `lookup_plant`.*

---

#### Auto-detection logic

When `season` is `None`, get the current calendar month with `datetime.now().month`
and look it up in the `_MONTH_TO_SEASON` dict, which maps month numbers to season strings.

```python
current_month = datetime.now().month
season_key = _MONTH_TO_SEASON[current_month]
```

---

#### Season validation

If the caller passes an invalid season string (e.g., `"monsoon"`), the function
falls back to auto-detection — same as if `None` were passed. The `VALID_SEASONS`
set acts as the gate:

```python
VALID_SEASONS = {"spring", "summer", "fall", "winter"}
if season and season.lower() in VALID_SEASONS:
    ...  # use provided season
else:
    ...  # auto-detect
```

---

#### Return structure

The full season dict from `_season_data`, plus a `detected_season` boolean. Example for spring:

```python
{
    "name": "Spring",
    "watering": "Increase watering frequency as plants break dormancy ...",
    "fertilizing": "Resume feeding with a balanced fertilizer ...",
    "light": "Days are lengthening — move plants closer to windows ...",
    "pests": "Watch for spider mites and aphids as temperatures rise ...",
    "detected_season": True   # True = auto-detected; False = caller specified
}
```

---

#### Implementation Notes

*Fill this in after testing.*

**Test: does calling with `season=None` return the correct season for the current month?**
```
Current month: June
Expected season: summer
Returned season: Summer (with "detected_season": True)
```

**Test: does calling with `season="winter"` return winter data regardless of the current month?**
```
yes — returns the Winter dict with "detected_season": False even though it's June
```
