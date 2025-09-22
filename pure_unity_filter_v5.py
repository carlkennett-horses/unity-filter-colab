from typing import List, Dict, Any
import pandas as pd

# --- Core Filter Class ---
class PureUnityFilterCorrected:
    def __init__(self):
        # Trainer scores
        self.trainer_scores = {
            "aidan o'brien": 4.0, "a p o'brien": 4.0, "joseph patrick o'brien": 3.8,
            "donnacha o'brien": 3.5, "dermot weld": 3.2, "jessica harrington": 2.8,
            "william haggas": 3.5, "john gosden": 3.5, "j & t gosden": 3.5,
            "charlie appleby": 3.2, "sir michael stoute": 3.0, "roger varian": 2.6,
            "andrew balding": 2.4, "ralph beckett": 2.2,
            "tim easterby": 2.8, "richard fahey": 2.6, "david o'meara": 2.2,
            "michael dods": 2.0, "kevin ryan": 1.8, "john quinn": 1.6,
        }
        # Jockey scores
        self.jockey_scores = {
            "ryan moore": 3.0, "william buick": 2.8, "frankie dettori": 2.8,
            "james doyle": 2.4, "tom marquand": 2.4, "oisin murphy": 2.6,
            "jim crowley": 2.2, "silvestre de sousa": 2.2, "rossa ryan": 2.0,
            "daniel tudhope": 2.4, "colin keane": 2.4, "seamie heffernan": 2.8,
            "wayne lordan": 2.2,
        }

    # --- Helpers ---
    @staticmethod
    def parse_form_corrected(form_str: str) -> List[int]:
        if not form_str:
            return []
        positions: List[int] = []
        for ch in form_str:
            if ch.isdigit():
                pos = int(ch)
                positions.append(10 if pos == 0 else pos)
            elif ch.upper() in "FURPD":
                positions.append(15)
        return positions

    def calculate_corrected_rel(self, form: List[int], or_rating: int, age: int) -> float:
        if not form:
            return 1.0
        weights = [1.0, 1.2, 1.5, 1.8, 2.2, 2.8, 3.2, 3.5]
        recent = form[-8:]
        score = 0.0
        for i, pos in enumerate(recent):
            if i >= len(weights): break
            w = weights[i]
            if pos == 1: points = 8.0 * w
            elif pos == 2: points = 5.5 * w
            elif pos == 3: points = 4.0 * w
            elif pos <= 6: points = 2.0 * w
            elif pos <= 10: points = 0.5 * w
            else: points = 0.0
            score += points

        extended = form[-12:]
        wins = sum(1 for p in extended if p == 1)
        places = sum(1 for p in extended if p <= 3)
        frames = sum(1 for p in extended if p <= 6)
        consistency = (wins*3 + places*2 + frames) / len(extended) if extended else 0.0

        momentum = 0.0
        if len(form) >= 6:
            early = form[-6:-3]; recent3 = form[-3:]
            if early and recent3:
                imp = (sum(early)/len(early)) - (sum(recent3)/len(recent3))
                if   imp >= 3: momentum = 2.0
                elif imp >= 1.5: momentum = 1.0
                elif imp >= 0.5: momentum = 0.5
                elif imp <= -3: momentum = -2.0
                elif imp <= -1.5: momentum = -1.0
                elif imp <= -0.5: momentum = -0.5

        base_rel = min(4.0, max(1.0, (score / 25.0) + consistency + momentum))
        if age == 3: base_rel *= 1.15
        elif age == 4: base_rel *= 1.10
        elif age >= 8: base_rel *= 0.90
        if or_rating >= 85: base_rel *= 0.95
        elif or_rating <= 55: base_rel *= 1.05
        return round(min(4.0, max(1.0, base_rel)), 2)

    @staticmethod
    def calculate_pure_map(stall: int, field_size: int, distance: int, track: str) -> float:
        if stall <= field_size * 0.3: draw_score = 0.8
        elif stall >= field_size * 0.7: draw_score = -0.6
        else: draw_score = 0.1
        if field_size >= 14: draw_score *= 1.3
        elif field_size <= 8: draw_score *= 0.7
        return round(draw_score, 1)

    def calculate_pure_csi(self, trainer: str, jockey: str, form: List[int]) -> float:
        trainer_key = trainer.lower()
        jockey_key = jockey.lower()
        csi = 0.0
        for t, s in self.trainer_scores.items():
            if t in trainer_key:
                csi += s; break
        for j, s in self.jockey_scores.items():
            if j in jockey_key:
                csi += s; break
        return round(min(csi, 10.0), 1)

    @staticmethod
    def calculate_pure_tpi(or_rating: int, cd_markers: str, age: int, class_level: str) -> int:
        tpi = 0
        if   or_rating >= 100: tpi += 5
        elif or_rating >= 90:  tpi += 4
        elif or_rating >= 80:  tpi += 3
        elif or_rating >= 70:  tpi += 2
        elif or_rating >= 60:  tpi += 1

        if cd_markers:
            c = cd_markers.upper()
            if "CD" in c: tpi += 3
            elif c.count("C") + c.count("D") >= 2: tpi += 2
            elif ("C" in c) or ("D" in c): tpi += 1

        if 4 <= age <= 6: tpi += 1
        cl = class_level.lower()
        if "group" in cl: tpi += 2
        elif "listed" in cl: tpi += 1
        return min(tpi, 12)

# --- Overwritten: run_card_primary (Total-first ordering) ---
def run_card_primary(races: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    puf = PureUnityFilterCorrected()
    out: Dict[str, List[Dict[str, Any]]] = {}
    for i, race in enumerate(races, start=1):
        horses = race["horses"]
        fs = len(horses)
        scored = []
        for h in horses:
            form_list = puf.parse_form_corrected(h.get("form", ""))
            rel = puf.calculate_corrected_rel(form_list, h.get("or", 60), h.get("age", 5))
            m = puf.calculate_pure_map(h.get("stall", 1), fs, race["distance"], race.get("track", ""))
            c = puf.calculate_pure_csi(h.get("trainer", ""), h.get("jockey", ""), form_list)
            t = puf.calculate_pure_tpi(h.get("or", 60), h.get("cd", ""), h.get("age", 5), race["class"])
            primary = round(rel + m + c, 1)
            total = round(primary + t, 1)
            scored.append({
                "name": h["name"], "stall": h.get("stall"),
                "rel": rel, "map": m, "csi": c, "cd": h.get("cd", ""),
                "tpi": t, "primary": primary, "total": total
            })
        scored.sort(key=lambda x: (-x["total"], -x["primary"], -x["tpi"]))
        out[f"R{i}"] = scored[:2]
    return out

# --- Debug Printer: Single Race ---
def print_race_table(race: Dict[str, Any]):
    puf = PureUnityFilterCorrected()
    fs = len(race["horses"])
    scored = []
    for h in race["horses"]:
        form_list = puf.parse_form_corrected(h.get("form", ""))
        rel = puf.calculate_corrected_rel(form_list, h.get("or", 60), h.get("age", 5))
        m = puf.calculate_pure_map(h.get("stall", 1), fs, race["distance"], race.get("track", ""))
        c = puf.calculate_pure_csi(h.get("trainer", ""), h.get("jockey", ""), form_list)
        t = puf.calculate_pure_tpi(h.get("or", 60), h.get("cd", ""), h.get("age", 5), race["class"])
        primary = round(rel + m + c, 1)
        total = round(primary + t, 1)
        scored.append({
            "Horse": h["name"], "Stall": h.get("stall"),
            "REL": rel, "MAP": m, "CSI": c,
            "CD": h.get("cd", ""), "TPI": t,
            "Primary": primary, "Total": total
        })
    df = pd.DataFrame(scored)
    df = df.sort_values(by=["Total", "Primary", "TPI"], ascending=[False, False, False])
    print(df.to_string(index=False))
    return df

# --- Debug Printer: Full Card ---
def print_card_tables(races: List[Dict[str, Any]]):
    for i, race in enumerate(races, start=1):
        print(f"\n====================")
        print(f" Race {i} — {race.get('track','')} {race.get('class','')} {race.get('distance','')}f")
        print("====================")
        print_race_table(race)
