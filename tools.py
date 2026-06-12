import json
import os
from datetime import datetime
from config import DATA_PATH

# Plant database and seasonal data are loaded once at module load.
# This mirrors how a real service would cache its data source in memory.
with open(os.path.join(DATA_PATH, "plants.json"), encoding="utf-8") as f:
    _plant_db = json.load(f)

with open(os.path.join(DATA_PATH, "seasons.json"), encoding="utf-8") as f:
    _season_data = json.load(f)

# Maps calendar months to seasons for auto-detection.
_MONTH_TO_SEASON = {
    12: "winter", 1: "winter", 2: "winter",
    3: "spring", 4: "spring", 5: "spring",
    6: "summer", 7: "summer", 8: "summer",
    9: "fall",  10: "fall",  11: "fall",
}


def lookup_plant(plant_name: str) -> dict:
    """
    Search the plant database for a plant by name and return its care information.

    Matching is case-insensitive and whitespace-trimmed. Search order (per
    specs/tool-functions-spec.md): direct key → display name → scientific
    name → aliases.

    Return format when found:
      {"found": True, "plant": <the full plant dict>}

    Return format when not found:
      {"found": False, "name": <normalized input>, "message": <helpful string>}
    """
    # Curly apostrophes (auto-inserted by phone keyboards) would miss aliases
    # like "devil's ivy", which use straight apostrophes in plants.json.
    normalized = plant_name.strip().lower().replace("’", "'")

    # 1. Direct key match — O(1) dict access, fastest path
    if normalized in _plant_db:
        return {"found": True, "plant": _plant_db[normalized]}

    # 2. Display name match
    for plant in _plant_db.values():
        if plant["display_name"].lower() == normalized:
            return {"found": True, "plant": plant}

    # 3. Scientific name match
    for plant in _plant_db.values():
        if plant["scientific_name"].lower() == normalized:
            return {"found": True, "plant": plant}

    # 4. Alias match — broadest net, so it goes last
    for plant in _plant_db.values():
        if normalized in [alias.lower() for alias in plant["aliases"]]:
            return {"found": True, "plant": plant}

    available = ", ".join(sorted(p["display_name"] for p in _plant_db.values()))
    return {
        "found": False,
        "name": normalized,
        "message": (
            f"No plant matching '{normalized}' found in the database. "
            "Do not invent specific care data (watering schedules, exact "
            "temperatures, fertilizing intervals) for this plant. Acknowledge "
            "the gap, offer general care principles for its broader plant type "
            "if the user's description makes that clear, and suggest a detailed "
            "source for specifics. If helpful, mention similar plants that ARE "
            f"in the database: {available}."
        ),
    }


def get_plant_list() -> dict:
    """
    Return the name and difficulty level of every plant in the database.

    Optional challenge tool: lets the agent answer catalog-style questions
    ("what plants do you know about?", "what's a good beginner plant?") that
    lookup_plant can't, since it only searches by a specific name.
    """
    plants = sorted(
        (
            {"name": p["display_name"], "difficulty": p["difficulty"]}
            for p in _plant_db.values()
        ),
        key=lambda p: p["name"],
    )
    return {"count": len(plants), "plants": plants}


def get_seasonal_conditions(season: str | None = None) -> dict:
    """
    Return current seasonal care context for houseplants.

    If season is provided and valid, returns that season's data.
    If season is None (or invalid), auto-detects from the current calendar month.

    Pre-implemented — read through this and the spec before working on lookup_plant().
    """
    VALID_SEASONS = {"spring", "summer", "fall", "winter"}

    if season and season.lower() in VALID_SEASONS:
        # Caller specified a valid season — use it directly
        season_key = season.lower()
        detected = False
    else:
        # Auto-detect from the current month using the _MONTH_TO_SEASON mapping
        current_month = datetime.now().month
        season_key = _MONTH_TO_SEASON[current_month]
        detected = True

    # Copy the season dict so we don't mutate the cached data
    result = dict(_season_data[season_key])
    result["detected_season"] = detected
    return result
