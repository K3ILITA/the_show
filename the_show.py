# the_show.py
import random
import time

# ----------------------- Config & Labels -----------------------

POS_LABELS = {
    "1": "Pitcher", "2": "Catcher", "3": "First Base", "4": "Second Base",
    "5": "Third Base", "6": "Shortstop", "7": "Left Field", "8": "Center Field", "9": "Right Field"
}

# Strikeout symbols
K_SWING = "K"      # swinging
K_LOOK  = "ꓘ"      # looking (backwards K)

# Popular current MLB hitters by primary position (7/8/9 = LF/CF/RF)
# Each item: (Name, Bats) where Bats in {"L","R","S"}
MLB_POSITION_POOL = {
    "2": [("Adley Rutschman","S"), ("Will Smith","R"), ("J.T. Realmuto","R"), ("Cal Raleigh","S")],
    "3": [("Freddie Freeman","L"), ("Vladimir Guerrero Jr.","R"), ("Matt Olson","L"), ("Pete Alonso","R")],
    "4": [("Jose Altuve","R"), ("Ketel Marte","S"), ("Marcus Semien","R"), ("Ozzie Albies","S")],
    "5": [("Jose Ramirez","S"), ("Rafael Devers","L"), ("Manny Machado","R"), ("Austin Riley","R")],
    "6": [("Francisco Lindor","S"), ("Corey Seager","L"), ("Trea Turner","R"), ("Bobby Witt Jr.","R")],
    "7": [("Yordan Alvarez","L"), ("Randy Arozarena","R"), ("Kyle Schwarber","L"), ("Steven Kwan","L")],
    "8": [("Julio Rodriguez","R"), ("Mike Trout","R"), ("Luis Robert Jr.","R"), ("Corbin Carroll","L")],
    "9": [("Aaron Judge","R"), ("Ronald Acuna Jr.","R"), ("Kyle Tucker","L"), ("Mookie Betts","R")],
}

# Extra depth to reduce repeats
BENCH_POSITION_POOL = {
    "2": [("Sean Murphy","R"), ("Gabriel Moreno","R")],
    "3": [("Christian Walker","R"), ("Yandy Diaz","R")],
    "4": [("Nico Hoerner","R"), ("Andres Gimenez","L")],
    "5": [("Alex Bregman","R"), ("Matt Chapman","R")],
    "6": [("Xander Bogaerts","R"), ("Dansby Swanson","R")],
    "7": [("Ian Happ","S"), ("Bryan Reynolds","S")],
    "8": [("Jarren Duran","L"), ("Cedric Mullins","L")],
    "9": [("Teoscar Hernandez","R"), ("Seiya Suzuki","R")],
}

# Pitchers with role and handedness
# role in {"starter","reliever","closer"}, throws in {"L","R"}
PITCHERS = [
    ("Gerrit Cole","R","starter"), ("Tarik Skubal","L","starter"),
    ("Corbin Burnes","R","starter"), ("Zack Wheeler","R","starter"),
    ("Max Fried","L","starter"),
    ("Yennier Cano","R","reliever"), ("Pete Fairbanks","R","reliever"),
    ("Josh Hader","L","reliever"), ("Ryan Helsley","R","reliever"),
    ("Devin Williams","R","reliever"),
    ("Emmanuel Clase","R","closer"), ("Edwin Diaz","R","closer"),
    ("Camilo Doval","R","closer"), ("Jordan Romano","R","closer"),
    ("Josh Hader","L","closer"),
]

# Neutral full-name fallbacks (no single-surname confusion)
FALLBACK_NAMES = [
    "Alex Romero", "Diego Morales", "Evan Castillo", "Marco Alvarez", "Noah Delgado",
    "Leo Fernandez", "Owen Herrera", "Elias Navarro", "Victor Santos", "Julian Cabrera",
    "Mateo Villanueva", "Adrian Solis", "Hugo Contreras", "Nico Rivas", "Bruno Salazar",
]

# Optional overrides for stars (0–100 scale). Missing names get positional heuristics.
PLAYER_OVERRIDES = {
    "Julio Rodriguez": {"spd": 85, "obp": 75, "pow": 80},
    "Mike Trout": {"spd": 70, "obp": 80, "pow": 90},
    "Ronald Acuna Jr.": {"spd": 95, "obp": 80, "pow": 85},
    "Aaron Judge": {"spd": 55, "obp": 85, "pow": 99},
    "Yordan Alvarez": {"spd": 40, "obp": 80, "pow": 98},
    "Freddie Freeman": {"spd": 45, "obp": 92, "pow": 75},
    "Jose Ramirez": {"spd": 70, "obp": 80, "pow": 80},
    "Corey Seager": {"spd": 50, "obp": 85, "pow": 85},
    "Francisco Lindor": {"spd": 75, "obp": 78, "pow": 70},
    "Adley Rutschman": {"spd": 40, "obp": 85, "pow": 70},
    "Kyle Tucker": {"spd": 70, "obp": 80, "pow": 85},
    "Ketel Marte": {"spd": 70, "obp": 78, "pow": 70},
}

# ----------------------- Input & Small Helpers -----------------------

def prompt_position():
    pos_map = {
        "1": "1", "p": "1", "pitcher": "1",
        "2": "2", "c": "2", "catcher": "2",
        "3": "3", "1b": "3", "first base": "3",
        "4": "4", "2b": "4", "second base": "4",
        "5": "5", "3b": "5", "third base": "5",
        "6": "6", "ss": "6", "shortstop": "6",
        "7": "7", "lf": "7", "left field": "7",
        "8": "8", "cf": "8", "center field": "8",
        "9": "9", "rf": "9", "right field": "9",
    }
    while True:
        raw = input("Your position? (1-9 or RF/SS/3B): ").strip().lower()
        if raw in pos_map:
            return pos_map[raw]
        print("Pick 1–9 or a name like RF, CF, SS, 3B.")

def choose_team_name(prompt_label):
    base = input(f"What is {prompt_label} team name? ").strip()
    if not base:
        base = "Goats" if "your" in prompt_label.lower() else "Opponents"
    already_has_the = base.lower().startswith("the ")
    add_the = input(f"Include 'the' in '{base}' when displayed? (y/n): ").strip().lower()
    if add_the.startswith("y"):
        return base if already_has_the else f"the {base}"
    return base[4:] if already_has_the else base

def show_bases(bases):
    def slot(x): return "_" if x is None else "X"
    print(f"Bases: 1st[{slot(bases[0])}]  2nd[{slot(bases[1])}]  3rd[{slot(bases[2])}]")

def reset_count(state):
    state["balls"] = 0
    state["strikes"] = 0
    state["fouls"] = 0

def count_string(state):
    return f"{state['balls']}-{state['strikes']}"

# ----------------------- Walk-up & Announcing -----------------------

def announce_batter(lineup, idx, batter_sides, current_pitcher, show_on_deck=False, user_name=None, user_side_for_ab=None):
    spot = idx + 1
    name = lineup[idx]
    bats = batter_sides.get(name, "R")
    p_name, p_throws = current_pitcher

    # Display side: if this is the user and they are switch, show chosen side for this AB
    display_bats = user_side_for_ab if (name == user_name and bats == "S" and user_side_for_ab) else bats

    vs_platoon = ("advantage" if (display_bats == "L" and p_throws == "R") or (display_bats == "R" and p_throws == "L") or bats == "S"
                  else "even")
    slot_lines = {
        1: ["Table-setter ready. 🏃", "Top of the card. 🎯", "Catalyst up.⚡"],
        2: ["Move the line. 🔗", "Contact guy in. 🧩", "Table extender. ➕"],
        3: ["Heart of the order. ❤️", "Thunder before cleanup. ⛈️", "Middle bat up. 🎯"],
        4: ["Cleanup time. 🧹", "Power chair is occupied. 💥", "Big swing spot. 🚀"],
        5: ["Protection bat. 🛡️", "Run producer. 🧮", "Damage zone continues. 🔨"],
        6: ["RBIs live here. 📦", "Keep it rolling. ▶️", "Traffic manager. 🚦"],
        7: ["Bottom heat. 🔥", "Depth bat stepping in. 🧰", "Grind time. 🪓"],
        8: ["Turn it over. 🔄", "Two-hole’s on deck soon. 👀", "Keep the chain moving. ⛓️"],
        9: ["Second leadoff feel. 2️⃣", "Flip the lineup. 🔁", "Sneaky speed here. 🐍"]
    }
    platoon_lines = {
        "advantage": ["Likes this matchup.", "Platoon edge here.", "Comfortable split."],
        "even": ["Straight-up battle.", "Neutral split.", "No edge either way."]
    }
    line = random.choice(slot_lines.get(spot, ["Locked in."])) + " " + random.choice(platoon_lines[vs_platoon])

    print(f"\nNow up: {spot}. {name} (Bats {display_bats}). {line}")
    print(f"Pitching: {p_name} (Throws {p_throws})")
    if bats == "S" and name == user_name:
        print("Switch hitter: auto side chosen vs pitcher. Press 'h' to flip this AB.")

    if show_on_deck:
        on_deck_idx = (idx + 1) % 9
        in_hole_idx = (idx + 2) % 9
        print(f"On deck: {lineup[on_deck_idx]} | In the hole: {lineup[in_hole_idx]}")

# ----------------------- Rosters & Lineups -----------------------

def allocate_two_teams(user_name, user_pos_num, batter_sides):
    """
    Build home and opponent defenses with variety.
    """
    home = {str(i): None for i in range(1, 10)}
    opp  = {str(i): None for i in range(1, 10)}

    def pick_two_from(pos):
        pool = MLB_POSITION_POOL.get(pos, []) + BENCH_POSITION_POOL.get(pos, [])
        pool = [p for p in pool]
        random.shuffle(pool)
        seen = set()
        picks = []
        for name, bats in pool:
            if name not in seen:
                picks.append((name, bats)); seen.add(name)
            if len(picks) == 2:
                break
        while len(picks) < 2:
            fallback = next((n for n in FALLBACK_NAMES if n not in seen and n != user_name), f"Bench{pos}")
            picks.append((fallback, "R")); seen.add(fallback)
        return picks[0], picks[1]

    for pos in ["2","3","4","5","6","7","8","9"]:
        if pos == user_pos_num:
            home[pos] = user_name
            batter_sides[user_name] = batter_sides.get(user_name, "R")
            (opp_name, opp_bats), _ = pick_two_from(pos)
            opp[pos] = opp_name
            batter_sides[opp_name] = opp_bats
        else:
            (h_name, h_bats), (o_name, o_bats) = pick_two_from(pos)
            home[pos] = h_name; batter_sides[h_name] = h_bats
            opp[pos]  = o_name; batter_sides[o_name] = o_bats

    home["1"] = "Home Pitcher"
    opp["1"]  = "Opp Pitcher"
    batter_sides.setdefault("Home Pitcher", "R")
    batter_sides.setdefault("Opp Pitcher", "R")
    return home, opp

def choose_staff():
    starters = [(n,t) for (n,t,r) in PITCHERS if r == "starter"]
    relievers = [(n,t) for (n,t,r) in PITCHERS if r == "reliever"]
    closers   = [(n,t) for (n,t,r) in PITCHERS if r == "closer"]
    starter   = random.choice(starters)
    reliever  = random.choice(relievers)
    closer    = random.choice(closers)
    starter_len = random.choice([3,4])  # starter goes 3–4 innings
    return {"starter": starter, "reliever": reliever, "closer": closer, "starter_len": starter_len}

def current_pitcher_for_inning(staff, inning):
    if inning <= staff["starter_len"]:
        return staff["starter"]
    elif inning <= 8:
        return staff["reliever"]
    else:
        return staff["closer"]

def infer_pos_for_name(defense, name):
    for pos, n in defense.items():
        if n == name:
            return pos
    return None

def heuristic_ratings(name, pos, bats):
    # Baseline
    base = {"spd": 50, "obp": 55, "pow": 50}
    if pos in ("8","6","4"):  # CF, SS, 2B tend faster/defense-first
        base["spd"] += 20; base["obp"] += 5
    if pos in ("3","5","7","9"):  # 1B, 3B, LF, RF tend to slug
        base["pow"] += 20; base["obp"] += 5
    if pos == "2":  # catchers: OB/contact
        base["obp"] += 5
    return base

def get_player_scores(defense, name, bats):
    pos = infer_pos_for_name(defense, name)
    ovr = PLAYER_OVERRIDES.get(name)
    if ovr:
        return ovr["spd"], ovr["obp"], ovr["pow"]
    h = heuristic_ratings(name, pos, bats)
    return h["spd"], h["obp"], h["pow"]

def build_batting_order_realistic(defense, user_name, user_spot, batter_sides):
    # Collect non-pitcher hitters
    hitters = [n for p,n in defense.items() if p != "1" and n is not None]
    # De-dup and pad
    seen = set(); uniq = []
    for n in hitters:
        if n not in seen:
            uniq.append(n); seen.add(n)
    while len(uniq) < 9:
        extra = next((x for x in FALLBACK_NAMES if x not in seen), f"Player{len(uniq)}")
        uniq.append(extra); batter_sides.setdefault(extra, "R"); seen.add(extra)

    # Score everyone
    scored = []
    for n in uniq:
        spd, obp, powr = get_player_scores(defense, n, batter_sides.get(n, "R"))
        overall = round(0.35*obp + 0.35*powr + 0.30*spd, 2)
        scored.append({"name": n, "spd": spd, "obp": obp, "pow": powr, "overall": overall})

    # Helpers to pick and remove
    def pick_max(key):
        i = max(range(len(scored)), key=lambda k: scored[k][key])
        return scored.pop(i)

    def pick_max_comb(keys, weights):
        i = max(range(len(scored)), key=lambda k: sum(scored[k][kk]*ww for kk,ww in zip(keys,weights)))
        return scored.pop(i)

    # Fill lineup roles
    leadoff = pick_max_comb(["spd","obp"], [0.6, 0.4])           # 1
    two     = pick_max("obp")                                   # 2
    three   = pick_max("overall")                               # 3
    four    = pick_max("pow")                                   # 4
    five    = pick_max_comb(["pow","obp"], [0.6, 0.4])          # 5
    six     = pick_max("overall")                               # 6
    seven   = pick_max("obp")                                   # 7
    eight   = pick_max("overall")                               # 8
    nine    = scored.pop(max(range(len(scored)), key=lambda k: -scored[k]["overall"]))  # weakest

    lineup = [leadoff["name"], two["name"], three["name"], four["name"],
              five["name"], six["name"], seven["name"], eight["name"], nine["name"]]

    # Put user in chosen spot
    if user_name in lineup:
        lineup.remove(user_name)
    user_spot = max(1, min(9, user_spot))
    lineup.insert(user_spot - 1, user_name)
    return lineup[:9]

# ----------------------- Pitch Model -----------------------

PITCH_TYPES = {
    "fastball":  {"strike_p": 0.63, "contact_weights": [30, 35, 35], "foul_on_strike_p": 0.18},
    "slider":    {"strike_p": 0.56, "contact_weights": [45, 35, 20], "foul_on_strike_p": 0.22},
    "curve":     {"strike_p": 0.50, "contact_weights": [40, 40, 20], "foul_on_strike_p": 0.24},
    "changeup":  {"strike_p": 0.58, "contact_weights": [35, 45, 20], "foul_on_strike_p": 0.20},
    "sinker":    {"strike_p": 0.60, "contact_weights": [25, 55, 20], "foul_on_strike_p": 0.18},
}

def count_adjusted_strike_p(base_p, balls, strikes):
    adj = 0.0
    if balls >= 3: adj += 0.08
    elif balls == 2: adj += 0.04
    if strikes == 2 and balls <= 1: adj -= 0.05
    return max(0.10, min(0.90, base_p + adj))

def platoon_modifier(hitter_side, pitcher_side):
    if hitter_side == "S": return 0.03
    if (hitter_side == "L" and pitcher_side == "R") or (hitter_side == "R" and pitcher_side == "L"):
        return 0.04
    return 0.0

# ----------------------- Baserunning -----------------------

def advance_bases(bases, batter_name, bases_to_advance):
    """
    Advance existing runners by bases_to_advance and place batter accordingly.
    Returns number of runs scored.
    """
    scored = 0
    new_bases = [None, None, None]

    # Move current runners (3rd->home, 2nd->3rd, 1st->2nd)
    if bases[2] is not None:
        if bases_to_advance >= 1: scored += 1
        else: new_bases[2] = bases[2]

    if bases[1] is not None:
        if bases_to_advance >= 2: scored += 1
        elif bases_to_advance == 1: new_bases[2] = bases[1]
        else: new_bases[1] = bases[1]

    if bases[0] is not None:
        if bases_to_advance >= 3: scored += 1
        elif bases_to_advance == 2: new_bases[2] = bases[0] if new_bases[2] is None else new_bases[2]
        elif bases_to_advance == 1: new_bases[1] = bases[0]
        else: new_bases[0] = bases[0]

    # Place batter
    if bases_to_advance >= 4: scored += 1
    elif bases_to_advance == 3: new_bases[2] = batter_name
    elif bases_to_advance == 2:
        if new_bases[1] is None: new_bases[1] = batter_name
    elif bases_to_advance == 1:
        if new_bases[0] is None: new_bases[0] = batter_name

    bases[0], bases[1], bases[2] = new_bases
    return scored

def force_advance_on_walk(bases, batter_name):
    """
    Force only what is required on a walk.
    Returns runs scored.
    """
    runs = 0
    b1, b2, b3 = bases
    if b1 and b2 and b3:
        runs += 1          # runner on 3rd scores
        bases[2] = b2      # 2nd -> 3rd
        bases[1] = b1      # 1st -> 2nd
        bases[0] = batter_name
    elif b1 and b2 and not b3:
        bases[2] = b2
        bases[1] = b1
        bases[0] = batter_name
    elif b1 and not b2:
        bases[1] = b1
        bases[0] = batter_name
    else:
        bases[0] = batter_name
    return runs

def double_play_643(bases):
    """
    Apply a classic 6-4-3 double play.
    Removes runner from 1B and the batter.
    Scores one only if bases were loaded.
    """
    runs = 0
    on1, on2, on3 = bases
    if not on1:
        return 0
    if on3 and on2 and on1:
        runs += 1
    if on2:
        bases[2] = on2
    bases[1] = None
    bases[0] = None
    return runs

# ----------------------- Defense Sim (3 outs exactly) -----------------------

def defensive_play_notation_exact(user_pos_num):
    """
    Build a concise, position-only summary that equals three outs.
    Events and their out values:
      - 'K' or 'ꓘ' = 1
      - 'F{pos}' = 1
      - '6-3'/'5-3'/'4-3'/'1-3' = 1
      - 'CS 2-6' or 'CS 2-4' = 1
      - '6-4-3 DP'/'5-4-3 DP'/'4-6-3 DP'/'3-6-3 DP' = 2
    """
    outs_left = 3
    plays = []
    while outs_left > 0:
        # If 2 or 3 outs remain, we may choose a DP
        can_dp = outs_left >= 2 and random.random() < 0.25
        if can_dp:
            dp = random.choice(["6-4-3 DP", "5-4-3 DP", "4-6-3 DP", "3-6-3 DP"])
            plays.append(dp)
            outs_left -= 2
            continue

        # Single-out options
        single = random.choice(["K", "ꓘ", f"F{user_pos_num}", random.choice(["6-3","5-3","4-3","1-3"]), random.choice(["CS 2-6","CS 2-4"])])
        plays.append(single)
        outs_left -= 1

    return ", ".join(plays)

def simulate_opponent_half_inning(user_pos_num):
    opp_runs = random.choices([0, 1, 2, 3], weights=[45, 30, 18, 7], k=1)[0]
    desc = defensive_play_notation_exact(user_pos_num)
    return opp_runs, desc

# ----------------------- At-Bat Loop -----------------------

def play_ended(outs_added, batter_idx, reset_fn, outs, lineup, bases):
    outs += outs_added
    reset_fn()
    batter_idx = (batter_idx + 1) % 9
    return outs, batter_idx, outs < 3

def play_half_inning(lineup, batter_idx, user_name, base_user_side, current_pitcher, batter_sides, team_label, show_on_deck):
    bases = [None, None, None]
    hits = 0
    runs = 0
    outs = 0
    state = {"balls": 0, "strikes": 0, "fouls": 0}

    # determine starting side for user if switch
    _, pitcher_side = current_pitcher
    def default_side_for_switch(p_side):
        return "L" if p_side == "R" else "R"

    # per-AB user side (only matters when the user is up)
    user_side_for_ab = base_user_side
    if base_user_side == "S":
        user_side_for_ab = default_side_for_switch(pitcher_side)

    def reset(): reset_count(state)

    # announce first batter
    announce_batter(lineup, batter_idx, batter_sides, current_pitcher, show_on_deck, user_name=user_name, user_side_for_ab=user_side_for_ab)
    show_bases(bases)

    while outs < 3:
        batter_name = lineup[batter_idx]

        # Use effective side: for user AB, use selected side; for others use listed bats
        effective_side = batter_sides.get(batter_name, "R")
        if batter_name == user_name and base_user_side == "S":
            effective_side = user_side_for_ab

        # Pitch comes in
        pitch_type = random.choices(
            population=["fastball", "slider", "curve", "changeup", "sinker"],
            weights=[30, 25, 15, 15, 15],
            k=1
        )[0]
        base_p = PITCH_TYPES[pitch_type]["strike_p"]
        strike_p = count_adjusted_strike_p(base_p, state["balls"], state["strikes"])
        strike_p = max(0.10, min(0.90, base_p + platoon_modifier(effective_side, pitcher_side)))
        pitch_result = "strike" if random.random() < strike_p else "ball"

        choice = input(f"⚾ {pitch_type.title()} — [s/t/q]{' (h=flip side)' if (batter_name==user_name and base_user_side=='S') else ''}: ").strip().lower()
        # Optional side flip for switch-hitting user
        if choice == "h" and batter_name == user_name and base_user_side == "S":
            user_side_for_ab = "L" if user_side_for_ab == "R" else "R"
            print(f"Switched hitting side for this AB → {user_side_for_ab}.")
            continue

        if choice in ("s", "swing"):
            pass  # proceed to swing branch
        elif choice in ("t", "take"):
            choice = "take"
        elif choice in ("q", "quit"):
            print("Practice over early. Head back to the clubhouse.")
            return runs, hits, batter_idx, True
        else:
            print("Type s (swing), t (take), or q (quit).")
            continue

        if choice == "take":
            if pitch_result == "ball":
                state["balls"] += 1
                print(f"Ball {state['balls']} 🔔  Count: {count_string(state)}")
                if state["balls"] == 4:
                    print("Walk. Take your base. 🧱")
                    scored = force_advance_on_walk(bases, batter_name)
                    runs += scored
                    if scored:
                        print(f"Runs: +{scored}  |  {team_label} this half: {runs}")
                    show_bases(bases)
                    outs, batter_idx, ann = play_ended(0, batter_idx, reset, outs, lineup, bases)
                    if ann:
                        # new AB: re-evaluate default side vs current pitcher
                        user_side_for_ab = base_user_side
                        if base_user_side == "S":
                            user_side_for_ab = default_side_for_switch(pitcher_side)
                        announce_batter(lineup, batter_idx, batter_sides, current_pitcher, show_on_deck, user_name=user_name, user_side_for_ab=user_side_for_ab)
                        show_bases(bases)
            else:
                state["strikes"] += 1
                print(f"Strike {state['strikes']} 🎯  Count: {count_string(state)}")
                if state["strikes"] == 3:
                    print(f"Strikeout looking {K_LOOK}.")
                    outs, batter_idx, ann = play_ended(1, batter_idx, reset, outs, lineup, bases)
                    print(f"Outs: {outs}")
                    if ann:
                        user_side_for_ab = base_user_side
                        if base_user_side == "S":
                            user_side_for_ab = default_side_for_switch(pitcher_side)
                        announce_batter(lineup, batter_idx, batter_sides, current_pitcher, show_on_deck, user_name=user_name, user_side_for_ab=user_side_for_ab)
                        show_bases(bases)
            continue

        # swing branch
        foul_on_strike_p = PITCH_TYPES[pitch_type]["foul_on_strike_p"]
        foul = (pitch_result == "strike" and random.random() < foul_on_strike_p)

        if foul:
            state["fouls"] += 1
            if state["strikes"] < 2:
                state["strikes"] += 1
                print(f"Foul ball. Strike {state['strikes']} ⚠️  Fouls: {state['fouls']}  Count: {count_string(state)}")
            else:
                print(f"Foul ball. Still two strikes. ⚠️  Fouls: {state['fouls']}  Count: {count_string(state)}")
            continue

        base_threshold = 6
        if pitch_type in ("slider", "curve"): base_threshold += 1
        if pitch_type == "sinker": base_threshold += 1
        if platoon_modifier(effective_side, pitcher_side) > 0: base_threshold -= 1

        swing_roll = random.randint(1, 10)
        if pitch_result == "strike" and swing_roll >= base_threshold:
            weights = PITCH_TYPES[pitch_type]["contact_weights"]
            contact = random.choices(["fly", "ground", "line"], weights=weights, k=1)[0]

            if contact == "fly":
                if random.random() < 0.55:
                    print("Fly out. 🪁")
                    outs, batter_idx, ann = play_ended(1, batter_idx, reset, outs, lineup, bases)
                    if ann:
                        user_side_for_ab = base_user_side
                        if base_user_side == "S":
                            user_side_for_ab = default_side_for_switch(pitcher_side)
                        announce_batter(lineup, batter_idx, batter_sides, current_pitcher, show_on_deck, user_name=user_name, user_side_for_ab=user_side_for_ab)
                        show_bases(bases)
                    continue
                hit_type = random.choices(["single", "double", "triple"], weights=[35, 50, 15], k=1)[0]

            elif contact == "ground":
                turn_two = random.random() < 0.10 and bases[0] and outs <= 1  # DP requires runner on 1st
                if turn_two:
                    print("Ground ball. 6-4-3 double play. 🧱🧱")
                    dp_runs = double_play_643(bases)
                    runs += dp_runs
                    outs, batter_idx, ann = play_ended(2, batter_idx, reset, outs, lineup, bases)
                    if ann:
                        user_side_for_ab = base_user_side
                        if base_user_side == "S":
                            user_side_for_ab = default_side_for_switch(pitcher_side)
                        announce_batter(lineup, batter_idx, batter_sides, current_pitcher, show_on_deck, user_name=user_name, user_side_for_ab=user_side_for_ab)
                        show_bases(bases)
                    continue
                if random.random() < 0.35:
                    scored = advance_bases(bases, batter_name, 1)
                    hits += 1
                    print("Ground-ball single through the infield. 🟩")
                    runs += scored
                    if scored:
                        print(f"Runs: +{scored}  |  {team_label} this half: {runs}")
                    show_bases(bases)
                    outs, batter_idx, ann = play_ended(0, batter_idx, reset, outs, lineup, bases)
                    if ann:
                        user_side_for_ab = base_user_side
                        if base_user_side == "S":
                            user_side_for_ab = default_side_for_switch(pitcher_side)
                        announce_batter(lineup, batter_idx, batter_sides, current_pitcher, show_on_deck, user_name=user_name, user_side_for_ab=user_side_for_ab)
                        show_bases(bases)
                    continue
                print("Ground out. 🧤")
                outs, batter_idx, ann = play_ended(1, batter_idx, reset, outs, lineup, bases)
                if ann:
                    user_side_for_ab = base_user_side
                    if base_user_side == "S":
                        user_side_for_ab = default_side_for_switch(pitcher_side)
                    announce_batter(lineup, batter_idx, batter_sides, current_pitcher, show_on_deck, user_name=user_name, user_side_for_ab=user_side_for_ab)
                    show_bases(bases)
                continue

            else:  # line
                if random.random() < 0.20:
                    print("Lineout. 📐")
                    outs, batter_idx, ann = play_ended(1, batter_idx, reset, outs, lineup, bases)
                    if ann:
                        user_side_for_ab = base_user_side
                        if base_user_side == "S":
                            user_side_for_ab = default_side_for_switch(pitcher_side)
                        announce_batter(lineup, batter_idx, batter_sides, current_pitcher, show_on_deck, user_name=user_name, user_side_for_ab=user_side_for_ab)
                        show_bases(bases)
                    continue
                hit_type = random.choices(["single", "double", "triple"], weights=[45, 40, 15], k=1)[0]

            # Extra-base or HR chance
            if random.random() < 0.07:
                hit_type = "homer"

            if hit_type == "single":
                scored = advance_bases(bases, batter_name, 1); hits += 1; print("Single. 🎯")
            elif hit_type == "double":
                scored = advance_bases(bases, batter_name, 2); hits += 1; print("Double. 🎯🎯")
            elif hit_type == "triple":
                scored = advance_bases(bases, batter_name, 3); hits += 1; print("Triple! 🎯🎯🎯")
            else:
                scored = advance_bases(bases, batter_name, 4); hits += 1; print("Home run! 💥")

            runs += scored
            if scored:
                print(f"Runs: +{scored}  |  {team_label} this half: {runs}")
            show_bases(bases)
            outs, batter_idx, ann = play_ended(0, batter_idx, reset, outs, lineup, bases)
            if ann:
                user_side_for_ab = base_user_side
                if base_user_side == "S":
                    user_side_for_ab = default_side_for_switch(pitcher_side)
                announce_batter(lineup, batter_idx, batter_sides, current_pitcher, show_on_deck, user_name=user_name, user_side_for_ab=user_side_for_ab)
                show_bases(bases)
        else:
            state["strikes"] += 1
            print(f"Swinging strike {state['strikes']} ❌  Count: {count_string(state)}")
            if state["strikes"] == 3:
                print(f"Strikeout swinging {K_SWING}.")
                outs, batter_idx, ann = play_ended(1, batter_idx, reset, outs, lineup, bases)
                print(f"Outs: {outs}")
                if ann:
                    user_side_for_ab = base_user_side
                    if base_user_side == "S":
                        user_side_for_ab = default_side_for_switch(pitcher_side)
                    announce_batter(lineup, batter_idx, batter_sides, current_pitcher, show_on_deck, user_name=user_name, user_side_for_ab=user_side_for_ab)
                    show_bases(bases)

    print(f"\nEnd of half-inning for {team_label}. Runs: {runs}, Hits: {hits}, Outs: {outs}")
    return runs, hits, batter_idx, False

# ----------------------- Emoji Recap Animation -----------------------

def watch_game_recap(my_team, opp_team, my_line, opp_line, final_home, final_away, speed=0.6):
    """
    Plays a simple emoji animation of the inning-by-inning scoring.
    - ⚾ repeated for runs in that half-inning
    - live score updates after each half
    """
    hl = my_line + [0]*(9 - len(my_line))
    al = opp_line + [0]*(9 - len(opp_line))

    home_score = 0
    away_score = 0

    print("\n🎬 Watch the game recap")
    time.sleep(0.6)

    for inning in range(1, 10):
        runs_top = al[inning-1]
        top_icons = "⚾" * runs_top if runs_top else "·"
        away_score += runs_top
        print("\033c", end="")
        print(f"Recap — Inning {inning}")
        print(f"Top {inning}: {opp_team} {top_icons}")
        print(f"Score: {opp_team} {away_score} — {my_team} {home_score}")
        time.sleep(speed)

        runs_bot = hl[inning-1]
        bot_icons = "⚾" * runs_bot if runs_bot else "·"
        home_score += runs_bot
        print("\033c", end="")
        print(f"Recap — Inning {inning}")
        print(f"Top {inning}: {opp_team} {top_icons}")
        print(f"Bottom {inning}: {my_team} {bot_icons}")
        print(f"Score: {opp_team} {away_score} — {my_team} {home_score}")
        time.sleep(speed)

    print("\033c", end="")
    trophy = "🎉🏆" if home_score > away_score else "👏🧢" if away_score > home_score else "🤝"
    verdict = (
        f"{my_team} win! {trophy}" if home_score > away_score else
        f"{opp_team} win! {trophy}" if away_score > home_score else
        f"Tie game. {trophy}"
    )
    print("🏁 Final")
    print(f"{opp_team} {away_score} — {my_team} {home_score}")
    print(verdict)
    time.sleep(1.0)

# ----------------------- Main Game -----------------------

def main():
    print("⚾️  Welcome to The Show!")

    player_name = input("What's your name? ").strip() or "Player"
    my_team = choose_team_name("your")
    opp_team = choose_team_name("the opponent's")

    print(f"Hi {player_name}, you are playing for {my_team} (home).")
    hitter_side = input("Hit from (L/R/S): ").upper()
    if hitter_side not in ("L","R","S"):
        hitter_side = "R"
        print("Not L/R/S; defaulting to R.")

    user_pos_num = prompt_position()
    print(f"Defensively, you are {POS_LABELS[user_pos_num]} ({user_pos_num}).")

    while True:
        try:
            user_spot = int(input("Your lineup spot (1–9): "))
            if 1 <= user_spot <= 9: break
            print("Pick a number from 1 to 9.")
        except ValueError:
            print("Type a number, like 4.")

    show_on_deck = input("Show on-deck/in-the-hole lines? (y/n): ").strip().lower().startswith("y")

    # Batter handedness map
    batter_sides = {player_name: hitter_side}

    # Build defenses (varied pools)
    home_defense, opp_defense = allocate_two_teams(player_name, user_pos_num, batter_sides)

    # Opponent pitching staff and schedule
    opp_staff = choose_staff()

    # Build lineups from realistic role-fitting
    home_lineup = build_batting_order_realistic(home_defense, player_name, user_spot, batter_sides)
    _ = build_batting_order_realistic(opp_defense, "Opp Batter", 9, batter_sides)  # opponent lineup not used in PBP

    my_total_runs = 0
    my_total_hits = 0
    opp_total_runs = 0
    my_line = []
    opp_line = []
    batter_idx = (user_spot - 1)
    game_ended_early = False

    # Inning 1 — Opp batting (defense summary = exactly 3 outs)
    print(f"\n========== Inning 1 — {opp_team} batting ==========")
    opp_runs, opp_desc = simulate_opponent_half_inning(user_pos_num)
    opp_total_runs += opp_runs
    opp_line.append(opp_runs)
    print("Defense summary:", opp_desc)
    print(f"{opp_team} scored this half: {opp_runs}")

    # Inning 1 — Home batting
    inning = 1
    current_pitcher = current_pitcher_for_inning(opp_staff, inning)
    p_name, p_hand = current_pitcher
    print(f"\n========== Inning 1 — {my_team} batting (vs {p_name}, {p_hand}) ==========")
    runs, hits, batter_idx, ended = play_half_inning(
        lineup=home_lineup,
        batter_idx=batter_idx,
        user_name=player_name,
        base_user_side=hitter_side,
        current_pitcher=current_pitcher,
        batter_sides=batter_sides,
        team_label=my_team,
        show_on_deck=show_on_deck
    )
    if ended: game_ended_early = True
    my_total_runs += runs; my_total_hits += hits; my_line.append(runs)
    print("\n--- Inning Summary ---")
    print(f"{my_team}: {my_total_runs} | {opp_team}: {opp_total_runs}")
    print("----------------------")

    # Innings 2–9
    inning = 2
    while not game_ended_early and inning <= 9:
        print(f"\n========== Inning {inning} — {opp_team} batting ==========")
        opp_runs, opp_desc = simulate_opponent_half_inning(user_pos_num)
        opp_total_runs += opp_runs
        opp_line.append(opp_runs)
        print("Defense summary:", opp_desc)
        print(f"{opp_team} scored this half: {opp_runs}")

        current_pitcher = current_pitcher_for_inning(opp_staff, inning)
        p_name, p_hand = current_pitcher
        print(f"\n========== Inning {inning} — {my_team} batting (vs {p_name}, {p_hand}) ==========")
        runs, hits, batter_idx, ended = play_half_inning(
            lineup=home_lineup,
            batter_idx=batter_idx,
            user_name=player_name,
            base_user_side=hitter_side,
            current_pitcher=current_pitcher,
            batter_sides=batter_sides,
            team_label=my_team,
            show_on_deck=show_on_deck
        )
        if ended:
            game_ended_early = True
            break
        my_total_runs += runs; my_total_hits += hits; my_line.append(runs)

        print("\n--- Inning Summary ---")
        print(f"{my_team}: {my_total_runs} | {opp_team}: {opp_total_runs}")
        print("----------------------")
        inning += 1

    if not game_ended_early:
        # Scoreboard
        def pad_line(arr): return arr + [0]*(9 - len(arr))
        my_display  = pad_line(my_line)
        opp_display = pad_line(opp_line)

        header   = "Inning:   " + " ".join(str(i) for i in range(1, 10)) + "   R   H"
        left_nm  = f"{my_team[:10]}".ljust(10)
        right_nm = f"{opp_team[:10]}".ljust(10)
        my_row   = f"{left_nm}:  {' '.join(map(str, my_display)).ljust(20)}  {my_total_runs:>2}  {my_total_hits:>2}"
        opp_row  = f"{right_nm}:  {' '.join(map(str, opp_display)).ljust(20)}  {opp_total_runs:>2}   -"

        print("\n========== Final ==========")
        print(header)
        print(my_row)
        print(opp_row)
        print(f"\n{my_team} {my_total_runs} vs {opp_team} {opp_total_runs}")
        if my_total_runs > opp_total_runs:   print("You win. 🎉")
        elif my_total_runs < opp_total_runs: print("You lose. 🧢")
        else:                                 print("Tie game. 🤝")

        # Optional recap animation
        want_recap = input("\nWatch the emoji recap? (y/n): ").strip().lower()
        if want_recap.startswith("y"):
            watch_game_recap(my_team, opp_team, my_line, opp_line, my_total_runs, opp_total_runs)

if __name__ == "__main__":
    main()
