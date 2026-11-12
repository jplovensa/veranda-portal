"""Check room stops and circulation against the exported collision envelopes."""
import json
import math
import struct
from itertools import combinations
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
    for item in data.get("operable",[]):
        t=item["initial"]
        angle=item["angle"]*(1-t) if item["kind"]=="door" else item["angle"]*t
        px=item["pivot"][0]+item["travel"][0]*t
        pd=item["pivot"][1]+item["travel"][1]*t
        c,s=math.cos(angle),math.sin(angle)
        u,v=c*(x-px)-s*(d-pd),s*(x-px)+c*(d-pd)
        a,b,e,f=item["rect"]
        if math.hypot(max(a-u,0,u-e),max(b-v,0,v-f))<RADIUS:
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
    # These share a planned footprint at different heights or form one fixture.
    shared = [{"Kitchen worktop","Stove cabinet"},{"Dining table","Six-seat dining chair"},
              {"Breakfast island","Leather counter stool"},{"Coffee table","Nesting table"}]
    furniture=[s for s in data["solids"] if s["kind"]!="architecture"]
    for first,second in combinations(furniture,2):
        if {first["name"],second["name"]} in shared:
            continue
        a,b,c,d=first["rect"]
        e,f,g,h=second["rect"]
        assert min(c,g)-max(a,e)<=.005 or min(d,h)-max(b,f)<=.005, (
            f"{unit}: {first['name']} clashes with {second['name']}")
    for fitting in furniture:
        for wall in (s for s in data["solids"] if s["kind"]=="architecture"):
            a,b,c,d=fitting["rect"]
            e,f,g,h=wall["rect"]
            assert min(c,g)-max(a,e)<=.008 or min(d,h)-max(b,f)<=.008, (
                f"{unit}: {fitting['name']} enters {wall['name']}")
    binary=(WEB/f"{unit}.glb").read_bytes()
    length=struct.unpack_from("<I",binary,12)[0]
    gltf=json.loads(binary[20:20+length])
    names={node.get("name") for node in gltf["nodes"]}
    assert data["operable"]
    for item in data["operable"]:
        assert item["id"] in names, f"{unit}: {item['label']} is not exported as a moving part"
        assert item["rect"][0]<item["rect"][2] and item["rect"][1]<item["rect"][3]
    assert {item["kind"] for item in data["operable"]} >= {"door","cabinet","drawer"}

    if unit == "2br":
        small_wardrobe=next(s["rect"] for s in furniture if s["name"]=="Wardrobe" and s["rect"][1]<4.5)
        study=next(s["rect"] for s in furniture if s["name"]=="Desk")
        assert small_wardrobe[0]-study[2]>=.60, "2BR: study corner is too close to the wardrobe"
        assert sum(s["name"]=="Leather counter stool" for s in furniture)==1
        assert by_name["Breakfast island"][1]-3.06>=.899, "2BR: the breakfast bar narrows the kitchen approach"
    if unit == "3br":
        table = by_name["Dining table"]
        assert "Woven resort lounge chair" not in by_name, "3BR: lounge chairs are still present"
        assert "Work corner desk" in by_name and "Work corner chair" in by_name
        assert math.isclose(by_name["Kitchen worktop"][3], 8.10), "3BR: kitchen stops short of the service doorway"
        chairs = [s["rect"] for s in data["solids"] if s["name"] == "Six-seat dining chair"]
        assert len(chairs) == 6, "3BR: the dining table needs six chairs"
        assert sum((rect[0]+rect[2])/2 < table[0] for rect in chairs) == 3
        assert sum((rect[0]+rect[2])/2 > table[2] for rect in chairs) == 3
        chair_aisle = min(rect[0] for rect in chairs)-by_name["Kitchen worktop"][2]
        assert chair_aisle >= 1.067, f"3BR: dining chairs narrow the kitchen aisle to {chair_aisle:.2f} m"
        dining_to_lounge = by_name["Four-seat family sectional"][1]-table[3]
        assert dining_to_lounge >= .90, f"3BR: dining and sectional leave {dining_to_lounge:.2f} m between them"
    worktop = by_name["Kitchen worktop"]
    gap = (worktop[0] - by_name["Breakfast island"][2] if unit == "2br"
           else by_name["Dining table"][0] - worktop[2])
    assert gap >= (1.08 if unit == "2br" else 1.0), f"{unit}: kitchen aisle narrowed to {gap:.2f} m"
    assert round(gap, 2) == data["checks"][0]["metres"], f"{unit}: clearance label is stale"
    print(f"{unit.upper()} passed all room stops and walking routes, kitchen clearance {gap:.2f} m")


if __name__ == "__main__":
    for unit in ("2br", "3br"):
        verify(unit)
