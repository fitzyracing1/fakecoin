"""The seven checks. Each returns a list of Finding. Status is one of lit / dark / info / skip."""
import json, os, re, glob
from dataclasses import dataclass, field, asdict
from .keccak import keccak256
from .chain import pad, word_int, word_addr, EIP1967_IMPL, EIP1967_ADMIN, DEX

ADDR_RE = re.compile(r"0x[0-9a-fA-F]{40}\b")
ZERO32 = "0x" + "0" * 64
DEFAULT_ADMIN_ROLE = "00" * 32
ROLE_NAMES = ["MINTER_ROLE", "PAUSER_ROLE", "UPGRADER_ROLE", "CONFIG_ROLE", "WITHDRAWER_ROLE", "UPDATER_ROLE", "BURNER_ROLE"]

@dataclass
class Finding:
    check: str
    status: str
    title: str
    evidence: list = field(default_factory=list)
    def to_dict(self): return asdict(self)

# ---------- repo helpers ----------
def _read(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as f: return f.read()
    except OSError: return ""

def test_files(repo):
    pats = ["test/**/*.sol", "test/**/*.t.sol", "test/**/*.js", "test/**/*.ts", "tests/**/*.ts", "tests/**/*.js",
            "e2e/**/*.ts", "e2e/**/*.js", "e2e/**/*.sol"]
    out = set()
    for p in pats: out.update(glob.glob(os.path.join(repo, p), recursive=True))
    return sorted(f for f in out if "/lib/" not in f.replace(repo, "") and "node_modules" not in f)

def load_deployments(repo, chain_id):
    """Return (contracts{name:addr}, meta dict, source path) for the deployments file matching chain_id."""
    best = None
    for p in sorted(glob.glob(os.path.join(repo, "deployments", "**", "*.json"), recursive=True)):
        try: d = json.loads(_read(p))
        except ValueError: continue
        if not isinstance(d, dict): continue
        cid = d.get("chainId") or d.get("chain_id")
        name = os.path.basename(p).lower()
        if cid == chain_id or (cid is None and chain_id == 1 and "mainnet" in name):
            contracts = d.get("contracts") if isinstance(d.get("contracts"), dict) else \
                {k: v for k, v in d.items() if isinstance(v, str) and ADDR_RE.fullmatch(v)}
            contracts = {k: (v["address"] if isinstance(v, dict) else v) for k, v in contracts.items()}
            best = (contracts, d, os.path.relpath(p, repo))
    return best or ({}, {}, None)

def readme_text(repo):
    return "\n".join(_read(p) for p in glob.glob(os.path.join(repo, "*.md")))

def artifact_runtime(repo, name):
    for p in glob.glob(os.path.join(repo, "out", "**", f"{name}.json"), recursive=True) + \
             glob.glob(os.path.join(repo, "artifacts", "**", f"{name}.json"), recursive=True):
        try: d = json.loads(_read(p))
        except ValueError: continue
        db = d.get("deployedBytecode")
        if isinstance(db, dict):
            refs = [r for v in (db.get("immutableReferences") or {}).values() for r in v]
            return db.get("object"), refs, os.path.relpath(p, repo)
        if isinstance(db, str): return db, [], os.path.relpath(p, repo)
    return None, [], None

def strip_cbor(hexcode):
    b = bytes.fromhex(hexcode)
    if len(b) > 2:
        n = int.from_bytes(b[-2:], "big")
        if 0 < n < len(b) - 2 and b[-n-2] in (0xa1, 0xa2, 0xa3): return b[:-n-2]
    return b

def compare_bytecode(local_hex, refs, onchain_hex):
    lo = bytes.fromhex(local_hex.replace("0x", "")); on = bytes.fromhex(onchain_hex.replace("0x", ""))
    if len(lo) != len(on):
        lo, on = strip_cbor(lo.hex()), strip_cbor(on.hex())
        if len(lo) != len(on): return False, f"length differs (repo {len(lo)} B vs chain {len(on)} B)"
    lo, on = bytearray(lo), bytearray(on)
    for r in refs:
        s, n = r["start"], r["length"]
        lo[s:s+n] = b"\0" * n; on[s:s+n] = b"\0" * n
    lo2, on2 = strip_cbor(lo.hex()), strip_cbor(on.hex())
    if lo2 == on2: return True, f"runtime bytecode matches repo build ({len(on)} B, {len(refs)} immutable ranges masked)"
    diff = sum(1 for a, b in zip(lo2, on2) if a != b)
    return False, f"runtime bytecode differs from repo build in {diff} bytes"

# ---------- check 1 ----------
FORK_RE = re.compile(r"createSelectFork|createFork|vm\.rpcUrl|forking\s*:|--fork-url|fork_url|hardhat_reset|eth_rpc_url", re.I)
MOCK_RE = re.compile(r"\bMock[A-Z]\w*|new\s+\w*Mock\w*|anvil|ganache|hardhat\s+node|localhost:8545|127\.0\.0\.1:8545", re.I)

def check_tests(repo, claimed):
    files = test_files(repo)
    if not files: return [Finding("tests", "dark", "No tests found", ["no files under test/, tests/, e2e/"])]
    fork_hits, mock_hits, real_hits = [], [], []
    claimed_l = {a.lower() for a in claimed.values()}
    for f in files:
        rel, txt = os.path.relpath(f, repo), _read(f)
        for i, line in enumerate(txt.splitlines(), 1):
            if FORK_RE.search(line): fork_hits.append(f"{rel}:{i}: {line.strip()[:120]}")
            if MOCK_RE.search(line): mock_hits.append(f"{rel}:{i}")
            for a in ADDR_RE.findall(line):
                if a.lower() in claimed_l: real_hits.append(f"{rel}:{i}: {a}")
    cfg = _read(os.path.join(repo, "foundry.toml")) + _read(os.path.join(repo, "hardhat.config.js")) + _read(os.path.join(repo, "hardhat.config.ts"))
    if re.search(r"rpc_endpoints|forking", cfg): fork_hits.append("config declares rpc_endpoints/forking")
    ev = [f"{len(files)} test files scanned", f"{len(mock_hits)} mock/local-chain references"]
    if fork_hits or real_hits:
        return [Finding("tests", "lit", "Tests touch a fork or real deployed addresses",
                        ev + fork_hits[:8] + [f"deployed address referenced: {h}" for h in real_hits[:8]])]
    return [Finding("tests", "dark", "Tests only hit mocks/local chain: no fork, no deployed addresses", ev)]

# ---------- check 2 & 3 ----------
def check_deployments(chain, repo, claimed):
    out = []
    if not claimed: return [Finding("deployed", "skip", "No claimed deployed addresses", [])]
    for name, a in claimed.items():
        code = chain.code(a)
        if not code or code == "0x":
            out.append(Finding("deployed", "dark", f"{name} {a}: no code on-chain", ["eth_getCode returned 0x"])); continue
        ev = [f"eth_getCode: {(len(code)-2)//2} bytes"]
        local, refs, src = artifact_runtime(repo, name) if repo else (None, [], None)
        if local and len(local) > 4:
            ok, why = compare_bytecode(local, refs, code)
            ev.append(f"{why} (artifact {src})")
            out.append(Finding("deployed", "lit" if ok else "dark", f"{name} {a}: {'code matches repo' if ok else 'code does not match repo build'}", ev))
        else:
            ev.append("no local build artifact to compare (run forge build / hardhat compile)")
            out.append(Finding("deployed", "lit", f"{name} {a}: code present", ev))
    return out

def check_verified(chain, claimed):
    out = []
    key = os.environ.get("ETHERSCAN_API_KEY")
    for name, a in claimed.items():
        s = chain.sourcify(a)
        m = (s or {}).get("match") or (s or {}).get("runtimeMatch")
        if m in ("match", "exact_match", "perfect", "partial"):
            ev = [f"sourcify match={s.get('match')} runtime={s.get('runtimeMatch')} creation={s.get('creationMatch')}",
                  f"https://repo.sourcify.dev/{chain.chain_id}/{a}"]
            out.append(Finding("verified", "lit", f"{name} verified on Sourcify", ev))
        else:
            out.append(Finding("verified", "dark", f"{name} not verified on Sourcify", [f"sourcify v2 lookup: {s!r}"[:200]]))
    out.append(Finding("verified", "skip" if not key else "info",
                       "Etherscan check skipped (no ETHERSCAN_API_KEY)" if not key else "Etherscan key present; Sourcify result is authoritative here", []))
    return out

# ---------- check 4 ----------
def _tokens(chain, claimed):
    toks = {}
    for n, a in claimed.items():
        ts = word_int(chain.call_sig(a, "totalSupply()"))
        dec = word_int(chain.call_sig(a, "decimals()"))
        if ts is not None and dec is not None and dec <= 36: toks[n] = (a, ts, dec)
    return toks

def fmt(v, d): return f"{v / 10**d:,.6f}".rstrip("0").rstrip(".")

def check_reserve(chain, claimed, extra_reserves, tokens):
    targets = {n: a for n, a in claimed.items() if "reserve" in n.lower() or "treasury" in n.lower() or "vault" in n.lower()}
    for a in extra_reserves: targets[f"reserve {a[:10]}"] = a
    if not targets: return [Finding("reserve", "skip", "No reserve/backing address claimed", [])]
    out = []
    weth, usdc = (DEX.get(chain.chain_id) or (None, None, None, None))[:2]
    for n, a in targets.items():
        ev, total = [], 0
        eth = chain.balance(a); total += eth; ev.append(f"ETH balance: {fmt(eth, 18)}")
        for tn, (ta, _, dec) in list(tokens.items()) + ([("WETH", (weth, 0, 18)), ("USDC", (usdc, 0, 6))] if weth else []):
            b = word_int(chain.call_sig(ta, "balanceOf(address)", pad(a))) or 0
            total += b; ev.append(f"{tn} balance: {fmt(b, dec)}")
        out.append(Finding("reserve", "dark" if total == 0 else "lit",
                           f"{n} {a}: {'reserve is empty' if total == 0 else 'holds assets'}", ev))
    return out

# ---------- check 5 ----------
MARKET_RE = re.compile(r"\b(price|priced|market cap|liquidity|uniswap|trading|tradable|listed|swap|dex|peg|pegged|worth)\b", re.I)

def check_liquidity(chain, readme, tokens):
    if not tokens: return [Finding("liquidity", "skip", "No ERC-20 token among claimed contracts", [])]
    d = DEX.get(chain.chain_id)
    if not d: return [Finding("liquidity", "skip", f"No Uniswap factory table for chain {chain.chain_id}", [])]
    weth, usdc, f2, f3 = d
    claims = [m.group(0) for m in MARKET_RE.finditer(readme)]
    out = []
    for n, (a, _, dec) in tokens.items():
        ev, liquid = [], False
        for qn, q in (("WETH", weth), ("USDC", usdc)):
            p = word_addr(chain.call_sig(f2, "getPair(address,address)", pad(a), pad(q)))
            if p and int(p, 16):
                bal = word_int(chain.call_sig(a, "balanceOf(address)", pad(p))) or 0
                liquid |= bal > 0; ev.append(f"UniV2 {qn} pair {p}: holds {fmt(bal, dec)} {n}")
            else: ev.append(f"UniV2 getPair({n},{qn}) = 0x0")
            for fee in (100, 500, 3000, 10000):
                p = word_addr(chain.call_sig(f3, "getPool(address,address,uint24)", pad(a), pad(q), hex(fee)[2:].rjust(64, "0")))
                if p and int(p, 16):
                    bal = word_int(chain.call_sig(a, "balanceOf(address)", pad(p))) or 0
                    liquid |= bal > 0; ev.append(f"UniV3 {qn} {fee} pool {p}: holds {fmt(bal, dec)} {n}")
            if not any(f"UniV3 {qn}" in e for e in ev): ev.append(f"UniV3 getPool({n},{qn}, 100/500/3000/10000) = 0x0 for all fee tiers")
        if liquid: st, t = "lit", f"{n} has on-chain Uniswap liquidity"
        elif claims: st, t = "dark", f"{n} has no Uniswap liquidity vs WETH/USDC while docs use market language"
        else: st, t = "info", f"{n} has no Uniswap liquidity (no market claims found)"
        if claims: ev.append("market language in docs: " + ", ".join(sorted(set(c.lower() for c in claims))[:12]))
        out.append(Finding("liquidity", st, t, ev))
    return out

# ---------- check 6 ----------
def _role(name): return keccak256(name.encode()).hex()

def check_admin(chain, claimed, admins):
    out = []
    admins = [a for a in admins if a]
    for n, a in claimed.items():
        ev = []
        impl = chain.storage(a, EIP1967_IMPL); padm = chain.storage(a, EIP1967_ADMIN)
        if impl and int(impl, 16): ev.append(f"EIP-1967 proxy: implementation 0x{impl[-40:]}")
        if padm and int(padm, 16): ev.append(f"EIP-1967 proxy admin 0x{padm[-40:]}")
        own = word_addr(chain.call_sig(a, "owner()"))
        if own and int(own, 16): ev.append(f"owner() = {own}")
        holders = set([own] if own and int(own, 16) else [])
        for adm in admins:
            for rn, rh in [("DEFAULT_ADMIN_ROLE", DEFAULT_ADMIN_ROLE)] + [(r, _role(r)) for r in ROLE_NAMES]:
                r = word_int(chain.call_sig(a, "hasRole(bytes32,address)", rh, pad(adm)))
                if r == 1: ev.append(f"{adm} has {rn}"); holders.add(adm.lower())
        cap = word_int(chain.call_sig(a, "cap()"))
        if any("MINTER_ROLE" in e for e in ev): ev.append(f"mint cap: {cap}" if cap else "no cap() function: mint is unlimited")
        if not ev: continue
        for h in holders:
            c = chain.code(h)
            kind = "EOA" if c in (None, "0x") else ("EIP-7702 delegated EOA" if c.startswith("0xef0100") else f"contract ({(len(c)-2)//2} B)")
            ev.append(f"{h} is {kind}")
        single = len(holders) == 1
        out.append(Finding("admin", "info", f"{n}: {'single admin' if single else f'{len(holders)} privileged accounts'}", ev))
    return out or [Finding("admin", "info", "No owner/role/proxy admin detected", [])]

# ---------- check 7 ----------
SUPPLY_RE = re.compile(r"(?:total|max|fixed|initial)\s+supply[^0-9\n]{0,40}([0-9][0-9,_.]*)\s*(billion|million|thousand|[bmk])?\b", re.I)
MULT = {"billion": 1e9, "b": 1e9, "million": 1e6, "m": 1e6, "thousand": 1e3, "k": 1e3}

def check_supply(readme, tokens):
    if not tokens: return [Finding("supply", "skip", "No ERC-20 token among claimed contracts", [])]
    claims = []
    for m in SUPPLY_RE.finditer(readme):
        try: v = float(m.group(1).replace(",", "").replace("_", "").rstrip(".")) * MULT.get((m.group(2) or "").lower(), 1)
        except ValueError: continue
        claims.append((v, m.group(0).strip()))
    out = []
    for n, (a, ts, dec) in tokens.items():
        actual = ts / 10**dec
        ev = [f"totalSupply() = {fmt(ts, dec)} ({ts} raw, {dec} decimals)"]
        if not claims:
            out.append(Finding("supply", "dark" if ts == 0 else "info", f"{n} supply {'is zero' if ts == 0 else 'reported'}; no supply claim in docs", ev)); continue
        bad = [c for c in claims if abs(c[0] - actual) > max(1e-9, 0.01 * c[0])]
        ev += [f"claim: “{c[1]}” -> {c[0]:,.0f}" for c in claims]
        out.append(Finding("supply", "dark" if len(bad) == len(claims) else "lit",
                           f"{n} supply {'does not match any doc claim' if len(bad) == len(claims) else 'matches doc claim'}", ev))
    return out
