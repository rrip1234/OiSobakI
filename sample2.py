#!/usr/bin/env python3
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import NamedTuple

MAX_TURN = 200          # maximum turn (days)
START_GOLD = 500        # initial gold
START_WARRIORS = 3      # initial warriors
MOVE_COST = 10          # move cost
TRAIN_COST = 120        # train cost
WORK_INCOME = 15        # income per warrior
UPKEEP_PER_WARRIOR = 2  # upkeep per warrior
HQ_MAX_LEVEL = 5        # HQ max level
BASE_MAX_LEVEL = 3      # base max level
HQ_HEAL_COST = 1000     # HQ fix cost
BASE_HEAL_COST = 500    # base fix cost


class HqLevelEntry(NamedTuple):
    upgrade_cost: int
    warrior_hp: int
    hp: int
    turret: int
    train_cap: int
    work_cap: int


class BaseLevelEntry(NamedTuple):
    cost: int
    hp: int
    turret: int
    work_cap: int


HQ_LEVELS: tuple[HqLevelEntry, ...] = (
    HqLevelEntry(0,     0, 0,  0, 0, 0),
    HqLevelEntry(0,     4, 10, 1, 1, 1),
    HqLevelEntry(600,   5, 15, 2, 1, 2),
    HqLevelEntry(1200,  6, 20, 2, 2, 3),
    HqLevelEntry(2400,  7, 25, 3, 2, 4),
    HqLevelEntry(3600,  8, 30, 3, 3, 5),
)
BASE_LEVELS: tuple[BaseLevelEntry, ...] = (
    BaseLevelEntry(0,    0,  0, 0),
    BaseLevelEntry(300,  6, 1, 1),
    BaseLevelEntry(600,  12, 1, 2),
    BaseLevelEntry(1000, 18, 2, 3),
)


class Side(Enum):
    LEFT = "A"
    RIGHT = "B"

    @property
    def opposite(self) -> "Side":
        return Side.RIGHT if self is Side.LEFT else Side.LEFT

    @classmethod
    def from_word(cls, w: str) -> "Side":
        return cls.LEFT if w == "LEFT" else cls.RIGHT

    @classmethod
    def from_char(cls, c: str) -> "Side":
        return cls.LEFT if c == "A" else cls.RIGHT


class BType(Enum):
    HQ = "HQ"
    BASE = "BASE"


class WState(Enum):
    STATIONARY = 0
    MOVING = 1


@dataclass(frozen=True)
class WarriorId:
    side: Side
    num: int

    def __str__(self) -> str:
        return f"{self.side.value}{self.num}"

    @classmethod
    def parse(cls, tok: str) -> "WarriorId":
        assert tok and tok[0] in ("A", "B")
        return cls(Side.from_char(tok[0]), int(tok[1:]))


@dataclass
class Warrior:
    id: WarriorId
    region: int
    hp: int
    state: WState = WState.STATIONARY
    target: int = 0


@dataclass
class Building:
    region: int
    side: Side
    type: BType
    level: int = 1
    hp: int = 10

    def current_hp(self) -> int:
        return HQ_LEVELS[self.level].hp if self.type is BType.HQ else BASE_LEVELS[self.level].hp

    def work_cap(self) -> int:
        return HQ_LEVELS[self.level].work_cap if self.type is BType.HQ else BASE_LEVELS[self.level].work_cap

    def apply_upgrade(self) -> None:
        self.level += 1
        self.hp = self.current_hp()

    def upgrade_cost(self) -> int:
        if self.type is BType.HQ:
            return HQ_LEVELS[self.level + 1].upgrade_cost
        else:
            return BASE_LEVELS[self.level + 1].cost


@dataclass
class GameMap:
    N: int = 0
    K: int = 0
    x: list[int] = field(default_factory=list)
    y: list[int] = field(default_factory=list)
    strongholds: list[int] = field(default_factory=list)
    adj: list[list[int]] = field(default_factory=list)
    my_side: Side = Side.LEFT
    my_hq: int = 0
    opp_hq: int = 0

    def hq_of(self, s: Side) -> int:
        return 0 if s is Side.LEFT else self.N - 1


@dataclass
class GameState:
    gold: int = START_GOLD
    my_countdown: int = 5
    opp_countdown: int = 5
    warriors: list[Warrior] = field(default_factory=list)
    buildings: list[Building] = field(default_factory=list)

    def find_building(self, region: int) -> Building | None:
        return next((b for b in self.buildings if b.region == region), None)

    def find_warrior(self, wid: WarriorId) -> Warrior | None:
        return next((w for w in self.warriors if w.id == wid), None)


@dataclass
class Actions:
    train_n: int = 0
    moves: list[tuple[WarriorId, int]] = field(default_factory=list)
    upgrades: list[int] = field(default_factory=list)


def make_base(region: int, s: Side) -> Building:
    return Building(region, s, BType.BASE, 1, BASE_LEVELS[1].hp)


def readln() -> str:
    line = sys.stdin.readline()
    if not line:
        sys.exit(0)
    return line.rstrip("\n")


def read_tokens() -> list[str]:
    return readln().split()


def parse_init() -> tuple[GameMap, GameState]:
    M = GameMap()

    t = read_tokens()
    assert len(t) >= 2 and t[0] == "READY"
    M.my_side = Side.from_word(t[1])

    t = read_tokens()
    M.N, M.K = int(t[0]), int(t[1])

    M.x = [int(v) for v in read_tokens()]  # x_0 x_1 ... x_{N-1}
    M.y = [int(v) for v in read_tokens()]  # y_0 y_1 ... y_{N-1}

    M.strongholds = sorted(int(v) for v in read_tokens())  # K strongholds

    M.adj = [[] for _ in range(M.N)]
    for r in range(M.N):
        t = read_tokens()  # deg n_1 n_2 ...
        deg = int(t[0])
        M.adj[r] = sorted(int(v) for v in t[1:1 + deg])

    M.my_hq = M.hq_of(M.my_side)
    M.opp_hq = M.hq_of(M.my_side.opposite)

    S = GameState()
    opp = M.my_side.opposite
    for sfx in range(1, START_WARRIORS + 1):
        S.warriors.append(Warrior(WarriorId(M.my_side, sfx), M.my_hq, HQ_LEVELS[1].warrior_hp))
        S.warriors.append(Warrior(WarriorId(opp, sfx), M.opp_hq, HQ_LEVELS[1].warrior_hp))
    S.buildings.append(
        Building(0, Side.LEFT, BType.HQ, 1, HQ_LEVELS[1].hp)
    )
    S.buildings.append(
        Building(M.N - 1, Side.RIGHT, BType.HQ, 1, HQ_LEVELS[1].hp)
    )

    print("OK", flush=True)
    return M, S


def read_turn_start() -> int | None:
    line = readln()
    if line == "FINISH":
        return None
    t = line.split()
    assert t and t[0] == "START"
    return int(t[2])


def read_turn_result(S: GameState, M: GameMap, submitted: Actions) -> None:
    for region in submitted.upgrades:
        b = S.find_building(region)
        if b is None:
            S.gold -= BASE_LEVELS[1].cost
            S.buildings.append(make_base(region, M.my_side))
        else:
            max_level = HQ_MAX_LEVEL if b.type is BType.HQ else BASE_MAX_LEVEL
            if b.level >= max_level:
                cost = HQ_HEAL_COST if b.type is BType.HQ else BASE_HEAL_COST
                S.gold -= cost
                b.hp = b.current_hp()
            else:
                S.gold -= b.upgrade_cost()
                b.apply_upgrade()

    for wid, target in submitted.moves:
        b = S.find_building(target)
        cost = 0 if (b is not None and b.side is M.my_side) else MOVE_COST
        S.gold -= cost
        w = S.find_warrior(wid)
        if w is not None:
            w.state = WState.MOVING
            w.target = target

    S.gold -= TRAIN_COST * submitted.train_n

    line = readln()
    if line == "FINISH":
        sys.exit(0)
    t = line.split()
    assert t and t[0] == "TURN"

    t = read_tokens()
    S.my_countdown = int(t[2])
    S.opp_countdown = int(t[4])

    # UPGRADE
    t = read_tokens()  # "UPGRADE N"
    n = int(t[1])
    for _ in range(n):
        r = read_tokens()  # "<A|B> <region>"
        s = Side.from_char(r[0][0])
        region = int(r[1])
        b = S.find_building(region)
        if b is None:
            S.buildings.append(make_base(region, s))
        elif b.side is not M.my_side:
            max_level = HQ_MAX_LEVEL if b.type is BType.HQ else BASE_MAX_LEVEL
            if b.level >= max_level:
                b.hp = b.current_hp()
            else:
                b.apply_upgrade()

    # TRAIN
    t = read_tokens()  # "TRAIN N"
    n = int(t[1])
    if n > 0:
        ids = read_tokens()
        for i in range(n):
            wid = WarriorId.parse(ids[i])
            hq_region = M.hq_of(wid.side)
            hq_b = S.find_building(hq_region)
            hq_level = hq_b.level if hq_b is not None else 1
            S.warriors.append(Warrior(wid, hq_region, HQ_LEVELS[hq_level].warrior_hp))

    # MOVE
    t = read_tokens()  # "MOVE N"
    n = int(t[1])
    for _ in range(n):
        r = read_tokens()
        wid = WarriorId.parse(r[0])
        region = int(r[1])
        w = S.find_warrior(wid)
        if w is not None:
            w.region = region
            if (wid.side is M.my_side
                    and w.state is WState.MOVING
                    and w.region == w.target):
                w.state = WState.STATIONARY

    # DAMAGE
    t = read_tokens()  # "DAMAGE N"
    n = int(t[1])
    for _ in range(n):
        r = read_tokens()
        wid = WarriorId.parse(r[1])
        damage = int(r[2])
        w = S.find_warrior(wid)
        if w is not None:
            w.hp -= damage
    S.warriors = [w for w in S.warriors if w.hp > 0]

    # SIEGE
    t = read_tokens()  # "SIEGE N"
    n = int(t[1])
    for _ in range(n):
        r = read_tokens()
        region = int(r[1])
        dmg = int(r[2])
        b = S.find_building(region)
        if b is not None:
            b.hp -= dmg
    S.buildings = [b for b in S.buildings if b.hp > 0]

    readln()  # "END"

    income = 0
    for b in S.buildings:
        if b.side is not M.my_side:
            continue
        count = sum(
            1 for w in S.warriors
            if w.id.side is M.my_side and w.region == b.region
        )
        income += WORK_INCOME * min(count, b.work_cap())
    S.gold += income

    alive = sum(1 for w in S.warriors if w.id.side is M.my_side)
    S.gold = max(0, S.gold - UPKEEP_PER_WARRIOR * alive)


@dataclass
class Paths:
    dist: list[list[float]]
    nxt: list[list[int]]


def euclid_ceil(M: GameMap, u: int, v: int) -> float:
    return math.ceil(math.hypot(M.x[u] - M.x[v], M.y[u] - M.y[v]))


def calculate_paths(M: GameMap) -> Paths:
    INF = math.inf
    N = M.N
    dist = [[INF] * N for _ in range(N)]
    nxt = [[-1] * N for _ in range(N)]

    for i in range(N):
        dist[i][i] = 0.0
        nxt[i][i] = i
    for u in range(N):
        for v in M.adj[u]:
            w = euclid_ceil(M, u, v)
            if w < dist[u][v]:
                dist[u][v] = w

    # Floyd-Warshall
    for k in range(N):
        dk = dist[k]
        for u in range(N):
            du = dist[u]
            duk = du[k]
            if duk == INF:
                continue
            for v in range(N):
                cand = duk + dk[v]
                if cand < du[v]:
                    du[v] = cand

    for u in range(N):
        du = dist[u]
        for v in range(N):
            if u == v or du[v] == INF:
                continue
            best_score = INF
            for nb in M.adj[u]:
                if dist[nb][v] == INF:
                    continue
                score = euclid_ceil(M, u, nb) + dist[nb][v]
                if score < best_score:
                    best_score = score
                    nxt[u][v] = nb
    return Paths(dist, nxt)


def next_step(P: Paths, u: int, v: int) -> int:
    """Returns the next step on the path from u to v. Returns -1 if the path is not reachable."""
    return P.nxt[u][v]


def path(P: Paths, u: int, v: int) -> list[int]:
    """Returns the path from u to v as [u, ..., v]. Returns an empty list if the path is not reachable."""
    if P.nxt[u][v] == -1:
        return []
    out = [u]
    while u != v:
        u = P.nxt[u][v]
        out.append(u)
    return out


def emit(a: Actions) -> None:
    out: list[str] = ["COMMAND"]
    for wid, target in a.moves:
        out.append(f"MOVE {wid} {target}")
    for r in a.upgrades:
        out.append(f"UPGRADE {r}")
    if a.train_n > 0:
        out.append(f"TRAIN {a.train_n}")
    out.append("END")
    sys.stdout.write("\n".join(out) + "\n")
    sys.stdout.flush()


def decide(S: GameState, M: GameMap, P: Paths, turn: int) -> Actions:
    """Balanced Frontier strategy.

    Priority:
    0. Heal Hq.
    1. If a soldier can build a base now, build before training.
    2. Keep workers on HQ / bases so income continues.
    3. Preserve 300 gold when a base construction is imminent.
    4. If income cannot grow with current soldiers, train a small number of soldiers
       so expansion and future income become possible.
    5. Defend when enemy soldiers approach our buildings.
    """
    a = Actions()
    my = M.my_side
    enemy = my.opposite

    my_warriors = [w for w in S.warriors if w.id.side is my]
    enemy_warriors = [w for w in S.warriors if w.id.side is enemy]

    def building_at(region: int) -> Building | None:
        return S.find_building(region)

    def my_building(region: int) -> Building | None:
        b = building_at(region)
        return b if b is not None and b.side is my else None

    def enemy_building(region: int) -> Building | None:
        b = building_at(region)
        return b if b is not None and b.side is enemy else None

    def my_count(region: int) -> int:
        return sum(1 for w in my_warriors if w.region == region)

    def enemy_count(region: int) -> int:
        return sum(1 for w in enemy_warriors if w.region == region)

    def stationary_my(region: int) -> list[Warrior]:
        return [w for w in my_warriors if w.region == region and w.state is WState.STATIONARY]

    center = M.N // 2
    if my is Side.LEFT:
        stronghold_order = sorted(
            M.strongholds,
            key=lambda r: (0 if r <= center else 1, abs(r - center), P.dist[M.my_hq][r])
        )
    else:
        stronghold_order = sorted(
            M.strongholds,
            key=lambda r: (0 if r >= center else 1, abs(r - center), P.dist[M.my_hq][r])
        )

    my_bases = [b for b in S.buildings if b.side is my and b.type is BType.BASE]
    my_buildings = [b for b in S.buildings if b.side is my]
    reserved_gold = 0 if turn < 20 else (HQ_LEVELS[building_at(M.my_hq).level][0] if building_at(M.my_hq).level<=HQ_MAX_LEVEL else HQ_HEAL_COST)
    used_regions: set[int] = set()

    if S.gold-reserved_gold>=0 and building_at(M.my_hq).hp<=building_at(M.my_hq).current_hp()/2 and sum(1 for i in enemy_warriors if i.region==M.my_hq)==0:
        a.upgrades.append(M.my_hq)

    # 1) Build base immediately if possible. This is always before TRAIN.
    for r in stronghold_order:
        if building_at(r) is not None: 
            continue
        if my_count(r) <= 0 or enemy_count(r) > 0:
            continue
        if S.gold - reserved_gold >= BASE_LEVELS[1].cost:
            a.upgrades.append(r)
            used_regions.add(r)
            reserved_gold += BASE_LEVELS[1].cost

    # 2) Identify threat. Enemy close to my building => defense target.
    defense_targets: list[int] = []
    for b in my_buildings:
        close_enemy = [e for e in enemy_warriors if P.dist[e.region][b.region] <= 30]
        if close_enemy:
            defense_targets.append(b.region)

    # 3) Reserve workers on buildings.
    reserved_workers: set[WarriorId] = set()
    for b in my_buildings:
        st = stationary_my(b.region)
        st.sort(key=lambda w: w.id.num)
        if b.type is BType.HQ:
            keep = min(1, len(st))
        else:
            keep = min(b.work_cap(), len(st))
        for w in st[:keep]:
            reserved_workers.add(w.id)

    # If a base is being built now, keep at least one soldier there as the first worker.
    for r in a.upgrades:
        st = stationary_my(r)
        st.sort(key=lambda w: w.id.num)
        if st:
            reserved_workers.add(st[0].id)

    def nearest_unowned_stronghold(from_region: int) -> int | None:
        candidates = []
        for r in stronghold_order:
            if my_building(r) is not None:
                continue
            if enemy_building(r) is not None:
                continue
            candidates.append(r)
        if not candidates:
            return None
        return min(candidates, key=lambda r: (P.dist[from_region][r] + 0.20 * P.dist[r][center], P.dist[from_region][r]))

    # Someone is ready to build but cannot yet because of gold.
    waiting_to_build = any(
        w.region in M.strongholds and building_at(w.region) is None and enemy_count(w.region) == 0
        for w in my_warriors
    )

    # Someone is already moving toward an unowned stronghold.
    active_expander = any(
        w.id.side is my and w.state is WState.MOVING and w.target in M.strongholds and my_building(w.target) is None
        for w in my_warriors
    )

    # Count surplus stationary soldiers that can be sent away while workers remain.
    surplus_stationary = [
        w for w in my_warriors
        if w.state is WState.STATIONARY and w.id not in reserved_workers
    ]

    # Current and possible work slots. Empty work slots mean training can directly increase income.
    work_slots = sum(b.work_cap() for b in my_buildings)
    current_workers = 0
    for b in my_buildings:
        current_workers += min(my_count(b.region), b.work_cap())
    empty_work_slots = max(0, work_slots - current_workers)

    # 4) TRAIN decision.
    hq = my_building(M.my_hq)
    train_cap = HQ_LEVELS[hq.level].train_cap if hq is not None else 1
    alive_my = len(my_warriors)
    safety_buffer = max(30, 2 * alive_my + 2 * MOVE_COST)

    desired_early_bases = 3
    planned_bases = len(my_bases) + sum(1 for r in a.upgrades if r in M.strongholds)
    still_expanding = planned_bases < desired_early_bases

    # Strictly protect 300 gold only when construction is imminent or a builder is actively moving.
    # But if gold is already below 300 and no income/expansion can happen with current soldiers,
    # allow one TRAIN so we do not freeze forever.
    construction_imminent = waiting_to_build or active_expander
    income_can_grow_now = empty_work_slots > 0 or bool(surplus_stationary) or active_expander or waiting_to_build or bool(a.upgrades)
    economy_stalled = (not income_can_grow_now) and (S.gold < BASE_LEVELS[1].cost or len(my_bases) == 0)

    future_base_reserve = 0
    if construction_imminent or (still_expanding and S.gold >= BASE_LEVELS[1].cost):
        future_base_reserve = BASE_LEVELS[1].cost

    train_budget = S.gold - reserved_gold - future_base_reserve - safety_buffer

    # Case A: training fills building work slots, so it increases income soon.
    if train_budget >= TRAIN_COST and (empty_work_slots > 0 or (sum(1 for i in my_warriors if i.region == M.my_hq)<sum(1 for i in enemy_warriors if True))) :#building_at(i.region) is None))):
        a.train_n = min(train_cap, max(1, min(empty_work_slots, train_budget // TRAIN_COST)))

    # Case B: no soldier is available to expand/defend, so produce one even if we are below 300.
    elif a.train_n == 0 and S.gold - reserved_gold - safety_buffer >= TRAIN_COST:
        no_builder_available = (not surplus_stationary) and (not active_expander) and (not waiting_to_build)
        if economy_stalled or no_builder_available:
            a.train_n = 1

    # Case C: after economy is established, train normally but still do not block base construction.
    elif a.train_n == 0 and len(my_bases) >= 2 and train_budget >= TRAIN_COST:
        a.train_n = 1

    if a.train_n > 0:
        reserved_gold += a.train_n * TRAIN_COST

    # 5) Optional conservative upgrade after stable economy.
    if len(my_bases) >= 4 and S.gold - reserved_gold >= 900:
        front_bases = sorted(my_bases, key=lambda b: P.dist[b.region][M.opp_hq])
        for b in front_bases:
            if b.level >= BASE_MAX_LEVEL or b.region in used_regions:
                continue
            cost = b.upgrade_cost()
            if S.gold - reserved_gold - cost >= BASE_LEVELS[1].cost + TRAIN_COST:
                a.upgrades.append(b.region)
                used_regions.add(b.region)
                reserved_gold += cost
                break

    def target_for(w: Warrior) -> int:
        # Wait on an unbuilt stronghold until we can build there.
        if w.region in M.strongholds and building_at(w.region) is None and enemy_count(w.region) == 0:
            return w.region

        # Defend threatened buildings.
        if defense_targets:
            return min(defense_targets, key=lambda r: P.dist[w.region][r])

        # Expand until mid-late game.
        if turn < 135:
            t = nearest_unowned_stronghold(w.region)
            if t is not None:
                return t

        return M.opp_hq

    # 6) MOVE decision. Preserve building money only if a base is realistically coming soon.
    move_budget = S.gold - reserved_gold
    if construction_imminent and S.gold >= BASE_LEVELS[1].cost:
        move_budget -= BASE_LEVELS[1].cost
    move_budget = max(0, move_budget)

    # Opening: send two soldiers to first stronghold, keep one HQ worker.
    if turn == 1:
        first_target = nearest_unowned_stronghold(M.my_hq)
        if first_target is None:
            first_target = M.opp_hq
        sent = 0
        for w in sorted(my_warriors, key=lambda x: x.id.num):
            if w.state is WState.STATIONARY and w.region == M.my_hq and sent < 2:
                a.moves.append((w.id, first_target))
                sent += 1
        return a

    for w in sorted(my_warriors, key=lambda x: x.id.num):
        if w.state is not WState.STATIONARY:
            continue
        if w.id in reserved_workers:
            continue
        if w.region==M.my_hq and sum(1 for i in my_warriors if i.region==M.my_hq) < sum(1 for i in enemy_warriors if True): #building_at(i.region) is None):  
            continue
        dst = target_for(w)
        if dst == w.region:
            continue
        b = building_at(dst)
        cost = 0 if (b is not None and b.side is my) else MOVE_COST
        if move_budget >= cost:
            a.moves.append((w.id, dst))
            move_budget -= cost

    return a

def main() -> None:
    M, S = parse_init()
    P = calculate_paths(M)

    while True:
        turn = read_turn_start()
        if turn is None:
            break
        a = decide(S, M, P, turn)
        emit(a)
        read_turn_result(S, M, a)


if __name__ == "__main__":
    main()
