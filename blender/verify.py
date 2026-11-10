"""Check room stops and circulation against the exported collision envelopes."""
import json
import math
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "assets" / "walkthrough"
RADIUS = .19  # Match the first-person camera in walkthrough.js.


def walkable(data, x, d):
    for dx, dd in ((0, 0), (RADIUS, 0), (-RADIUS, 0), (0, RADIUS), (0, -RADIUS)):
        if not any(a <= x + dx <= b and c <= d + dd <= e for a, c, b, e in data["floors"]):
            return False
    for solid in data["solids"]:
        a, c, b, e = solid["rect"]
        if math.hypot(max(a - x, 0, x - b), max(c - d, 0, d - e)) < RADIUS:
            return False
    return True


def verify(unit):
    data = json.loads((WEB / f"{unit}.json").read_text())
    for name, (x, d, _), _ in data["views"]:
        assert walkable(data, x, d), f"{unit}: {name} camera intersects an obstruction"
    for route in data["routes"]:
        for (x, d), (end_x, end_d) in zip(route, route[1:]):
            steps = max(1, math.ceil(math.dist((x, d), (end_x, end_d)) / .025))
            for step in range(steps + 1):
                t = step / steps
                assert walkable(data, x + (end_x - x) * t, d + (end_d - d) * t), (
                    f"{unit}: obstruction on route from {(x, d)} to {(end_x, end_d)}"
                )
    if unit=="2br":
        for solid in data["solids"]:
            if solid["name"] in {"Breakfast island","Leather counter stool"}:
                assert solid["rect"][0]>=5.91, "2BR: breakfast seating enters the bathroom approach"
    by_name = {s["name"]: s["rect"] for s in data["solids"]}
    if unit == "3br":
        table = by_name["Dining table"]
        chairs = [s["rect"] for s in data["solids"] if s["name"] == "Six-seat dining chair"]
        assert len(chairs) == 6, "3BR: the dining table needs six chairs"
        assert sum((rect[0]+rect[2])/2 < table[0] for rect in chairs) == 3
        assert sum((rect[0]+rect[2])/2 > table[2] for rect in chairs) == 3
        chair_aisle = min(rect[0] for rect in chairs)-by_name["Kitchen worktop"][2]
        assert chair_aisle >= .95, f"3BR: dining chairs narrow the kitchen aisle to {chair_aisle:.2f} m"
        dining_to_lounge = by_name["Four-seat family sectional"][1]-table[3]
        assert dining_to_lounge >= .85, f"3BR: dining and sectional leave {dining_to_lounge:.2f} m between them"
    worktop = by_name["Kitchen worktop"]
    gap = (worktop[0] - by_name["Breakfast island"][2] if unit == "2br"
           else by_name["Dining table"][0] - worktop[2])
    assert gap >= (1.08 if unit == "2br" else 1.0), f"{unit}: kitchen aisle narrowed to {gap:.2f} m"
    assert round(gap, 2) == data["checks"][0]["metres"], f"{unit}: clearance label is stale"
    print(f"{unit.upper()} passed all room stops and walking routes, kitchen clearance {gap:.2f} m")


if __name__ == "__main__":
    for unit in ("2br", "3br"):
        verify(unit)
