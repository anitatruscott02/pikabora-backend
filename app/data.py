import json
from pathlib import Path
BASE=Path(__file__).resolve().parent.parent / "data"
FOODS=json.loads((BASE/"foods.json").read_text())
MEALS=json.loads((BASE/"meals.json").read_text())
ALIASES=json.loads((BASE/"aliases.json").read_text())
COUNTRY_NAME={"KE":"Kenya","NG":"Nigeria","SN":"Senegal"}
