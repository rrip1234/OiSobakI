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


# ===========================================================================
# ============================  전략 (STRATEGY)  ============================
# ===========================================================================
#
# 튜닝 파라미터
# ---------------------------------------------------------------------------
GOLD_RESERVE = 100          # 항상 남겨둘 최소 골드 (파산 방지 버퍼)
REPAIR_HP_RATIO = 0.4      # 최대 체력 대비 이 비율 미만이면 최우선 수리
ATTACK_SAFETY_MARGIN = 1   # "내 손실 + 이만큼" 보다 적을 손해 상대는 이득이어야 공격
CONTEST_MARGIN = 3  # 이 거리 차이 이내면 "적과 경쟁 중인 위험 거점"으로 간주해 호위 병력 동반

def _building_turret(b: Building) -> int:
    return HQ_LEVELS[b.level].turret if b.type is BType.HQ else BASE_LEVELS[b.level].turret

def simulate_battle(
    my_hps: list[int],
    enemy_hps: list[int],
    my_turret: int,
    enemy_turret: int,
    my_building_hp: int | None,
    enemy_building_hp: int | None,
) -> tuple[list[int], list[int], int | None, int | None]:
    """규칙서 3절(전투)의 낮 전투 단계를 그대로 재현한다.

    - my_hps / enemy_hps: 해당 구역에 있는 전사들의 체력 리스트
      (번호 오름차순으로 정렬해서 넘겨야 동점 처리(번호가 빠른 쪽 우선)가 정확함).
    - my_turret / enemy_turret: 그 구역에 내/상대 건물이 있을 때의 포탑 공격력
      (건물이 없으면 0).
    - my_building_hp / enemy_building_hp: 그 구역 내/상대 건물의 현재 체력
      (건물이 없으면 None).

    반환값은 전투 직후 상태이며, 체력이 0 이하인 전사는 아직 제거하지 않는다
    (규칙: "전투가 끝날 때까지 퇴각하지 않으므로 a, b 산정에 포함됨").
    호출부에서 전투 종료 후 hp<=0 인 전사를 걸러내면 된다.
    """
    my_hps = my_hps[:]
    enemy_hps = enemy_hps[:]

    # 포탑 공격과 전사 공격은 둘 다 "상대편 중 살아있는 최소 체력 전사,
    # 없으면 건물"을 때리는 동일한 규칙을 따르므로 하나의 총 공격 횟수로
    # 합쳐서 처리해도 결과가 동일하다 (매 공격이 독립적으로 그 순간의
    # 최소 체력 대상을 찾기 때문).
    attacks_on_enemy = len(my_hps) + my_turret
    attacks_on_me = len(enemy_hps) + enemy_turret

    def apply_attacks(n: int, target_hps: list[int], target_building_hp: int | None) -> int | None:
        for _ in range(n):
            alive = [i for i, hp in enumerate(target_hps) if hp > 0]
            if alive:
                idx = min(alive, key=lambda i: (target_hps[i], i))
                target_hps[idx] -= 1
            elif target_building_hp is not None and target_building_hp > 0:
                target_building_hp -= 1
        return target_building_hp

    enemy_building_hp = apply_attacks(attacks_on_enemy, enemy_hps, enemy_building_hp)
    my_building_hp = apply_attacks(attacks_on_me, my_hps, my_building_hp)

    return my_hps, enemy_hps, my_building_hp, enemy_building_hp

def _nearest_enemy_arrival(P: Paths, M: GameMap, enemy_warriors: list[Warrior], region: int) -> float:
    """해당 구역에 적이 도달할 수 있는 가장 빠른 거리를 추정한다.
    (기존 적 전사들의 현재 위치 + 적 본부에서 새로 훈련되어 올 가능성까지 고려)"""
    best = P.dist[M.opp_hq][region]
    for w in enemy_warriors:
        d = P.dist[w.region][region]
        if d < best:
            best = d
    return best

HOME_GARRISON_MIN = 1      # 본부에는 최소 이 인원을 남겨 소득 공백/무방비 상태를 막는다


def decide(S: GameState, M: GameMap, P: Paths, turn: int) -> Actions:
    """Write your strategy here."""
    a = Actions()
    my, opp = M.my_side, M.my_side.opposite
    gold = S.gold

    my_warriors = [w for w in S.warriors if w.id.side is my]
    enemy_warriors = [w for w in S.warriors if w.id.side is opp]

    my_at: dict[int, list[Warrior]] = {}
    enemy_at: dict[int, list[Warrior]] = {}
    for w in my_warriors:
        my_at.setdefault(w.region, []).append(w)
    for w in enemy_warriors:
        enemy_at.setdefault(w.region, []).append(w)

    my_buildings = {b.region: b for b in S.buildings if b.side is my}
    enemy_buildings = {b.region: b for b in S.buildings if b.side is opp}

    def sorted_hps(region: int, side: Side) -> list[int]:
        ws = sorted(
            (w for w in S.warriors if w.id.side is side and w.region == region),
            key=lambda w: w.id.num,
        )
        return [w.hp for w in ws]

    committed_regions: set[int] = set()
    reserved_movers: set[WarriorId] = set()

    # -----------------------------------------------------------------
    # 1) 건설 단계: 수리 > 빈 거점 선점 > 본부 업그레이드 > 기지 업그레이드
    # -----------------------------------------------------------------
    hq = my_buildings.get(M.my_hq)

    build_queue: list[tuple[int, int, int]] = []

    for region, b in my_buildings.items():
        if not my_at.get(region) or enemy_at.get(region):
            continue
        max_hp = b.current_hp()
        max_level = HQ_MAX_LEVEL if b.type is BType.HQ else BASE_MAX_LEVEL
        if b.hp < max_hp * REPAIR_HP_RATIO:
            cost = (HQ_HEAL_COST if b.type is BType.HQ else BASE_HEAL_COST) \
                if b.level >= max_level else b.upgrade_cost()
            build_queue.append((0, region, cost))
        elif b.type is BType.HQ and b.level < HQ_MAX_LEVEL:
            build_queue.append((2, region, b.upgrade_cost()))
        elif b.type is BType.BASE and b.level < BASE_MAX_LEVEL:
            build_queue.append((3, region, b.upgrade_cost()))

    for region in M.strongholds:
        if region in my_buildings or region in enemy_buildings:
            continue
        if my_at.get(region) and not enemy_at.get(region):
            build_queue.append((1, region, BASE_LEVELS[1].cost))

    build_queue.sort(key=lambda t: t[0])
    for _, region, cost in build_queue:
        if region in committed_regions:
            continue
        if gold - cost >= GOLD_RESERVE:
            a.upgrades.append(region)
            gold -= cost
            committed_regions.add(region)

    # -----------------------------------------------------------------
    # 2) 이동 단계
    # -----------------------------------------------------------------
    idle = [w for w in my_warriors if w.state is WState.STATIONARY]

    # 본부 최소 수비/노동 인원은 파견 후보에서 제외한다.
    # (이게 없으면 초반에 전원이 빠져나가 그동안 수입이 0이 된다.)
    hq_idle = [w for w in idle if w.region == M.my_hq]
    protected = {w.id for w in hq_idle[:HOME_GARRISON_MIN]}
    idle = [w for w in idle if w.id not in protected]

    # 2a. 적에게 밀리는 내 건물 구역에 인접 전사 급파
    for region, b in my_buildings.items():
        attackers = enemy_at.get(region, [])
        if not attackers:
            continue
        my_hps = sorted_hps(region, my)
        en_hps = sorted_hps(region, opp)
        en_b = enemy_buildings.get(region)
        _, en_after, _, _ = simulate_battle(
            my_hps, en_hps, _building_turret(b),
            _building_turret(en_b) if en_b else 0,
            b.hp, None,
        )
        enemy_survivors = sum(1 for hp in en_after if hp > 0)
        if enemy_survivors >= len(en_hps):
            candidates = [
                w for w in idle
                if w.id not in reserved_movers and region in M.adj[w.region]
            ]
            candidates.sort(key=lambda w: -w.hp)
            if candidates:
                w = candidates[0]
                a.moves.append((w.id, region))
                reserved_movers.add(w.id)

    idle = [w for w in idle if w.id not in reserved_movers]

    # 2b. 비어있는 거점 선점 -- 이번엔 "지금 골드로 감당 가능한 만큼만" 새로
    #     착수한다. 그렇지 않으면 여러 명을 동시에 내보냈다가 한 명이 도착해
    #     건설하는 순간 나머지가 지을 돈이 없어지는 문제가 생긴다.
    unclaimed = [
        r for r in M.strongholds
        if r not in my_buildings and r not in enemy_buildings and not enemy_at.get(r)
    ]
    en_route_targets = {w.target for w in my_warriors if w.state is WState.MOVING}
    unclaimed = [r for r in unclaimed if r not in en_route_targets]

    pairs: list[tuple[float, Warrior, int]] = []
    for r in unclaimed:
        for w in idle:
            d = P.dist[w.region][r]
            if d < math.inf:
                pairs.append((d, w, r))
    pairs.sort(key=lambda t: t[0])

    # 지금 골드로 새로 착수 가능한 거점 개수 상한
    # (이미 이동 중인 미착공 거점 수는 이미 자금이 배정된 것으로 보고 차감)
    max_new_bases = max(0, (gold - GOLD_RESERVE) // BASE_LEVELS[1].cost)
    budget_left = max(0, max_new_bases - len(en_route_targets))

    assigned_count: dict[int, int] = {}
    new_regions_claimed = 0
    for d, w, r in pairs:
        if w.id in reserved_movers:
            continue
        if r not in assigned_count and new_regions_claimed >= budget_left:
            continue  # 예산 상한 도달 -- 이 거점은 자금이 회복된 뒤에 노린다
        enemy_eta = _nearest_enemy_arrival(P, M, enemy_warriors, r)
        needed = 2 if enemy_eta <= d + CONTEST_MARGIN else 1
        if assigned_count.get(r, 0) >= needed:
            continue
        if next_step(P, w.region, r) == -1:
            continue
        a.moves.append((w.id, r))
        reserved_movers.add(w.id)
        if r not in assigned_count:
            new_regions_claimed += 1
        assigned_count[r] = assigned_count.get(r, 0) + 1

    idle = [w for w in idle if w.id not in reserved_movers]

    # 2c. 기회주의적 공격 (인접한 적 건물에 한해)
    for region, b in list(enemy_buildings.items()):
        attackers_here = [
            w for w in idle
            if w.id not in reserved_movers and region in M.adj[w.region]
        ]
        if not attackers_here:
            continue
        my_hps = sorted([w.hp for w in attackers_here], reverse=True)
        en_hps = sorted_hps(region, opp)
        my_after, en_after, _, b_after = simulate_battle(
            my_hps, en_hps, 0, _building_turret(b), None, b.hp,
        )
        my_losses = sum(1 for hp in my_after if hp <= 0)
        en_losses = len(en_hps) - sum(1 for hp in en_after if hp > 0)
        building_damage = b.hp - (b_after if b_after is not None else b.hp)

        worth_it = building_damage > 0 or en_losses >= my_losses + ATTACK_SAFETY_MARGIN
        if worth_it:
            for w in attackers_here:
                a.moves.append((w.id, region))
                reserved_movers.add(w.id)

    idle = [w for w in idle if w.id not in reserved_movers]

    # -----------------------------------------------------------------
    # 3) 훈련 단계
    #    -- 도착 예정인 거점의 건설비를 먼저 예약해두고 남는 돈으로만 훈련
    # -----------------------------------------------------------------
    all_pending_targets = en_route_targets | assigned_count.keys()
    pending_build_cost = sum(
        BASE_LEVELS[1].cost
        for r in all_pending_targets
        if r not in my_buildings and r not in enemy_buildings
    )

    if hq is not None:
        cap = HQ_LEVELS[hq.level].train_cap
        affordable = max(0, (gold - GOLD_RESERVE - pending_build_cost) // TRAIN_COST)
        a.train_n = min(cap, affordable)

    return a

def main() -> None:
    M, S = parse_init()
    P = calculate_paths(M)

    while (turn := read_turn_start()) is not None:
        a = decide(S, M, P, turn)
        emit(a)
        read_turn_result(S, M, a)


if __name__ == "__main__":
    main()