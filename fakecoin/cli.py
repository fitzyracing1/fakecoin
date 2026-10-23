import argparse, json, os, re, subprocess, sys, tempfile
from . import checks as C
from .chain import Chain

ORDER = ["tests", "deployed", "verified", "reserve", "liquidity", "admin", "supply"]
NAMES = {"tests": "1. Tests hit a fork / real addresses", "deployed": "2. Claimed deployments have matching code",
         "verified": "3. Verified on Sourcify", "reserve": "4. Reserve / backing holds assets",
         "liquidity": "5. Market liquidity", "admin": "6. Admin / mint / upgrade power (info)", "supply": "7. Total supply vs claims"}

def resolve_repo(r):
    if not r: return None
    if os.path.isdir(r): return os.path.abspath(r)
    if re.match(r"^[\w.-]+/[\w.-]+$", r): r = f"https://github.com/{r}"
    d = tempfile.mkdtemp(prefix="fakecoin-")
    subprocess.run(["git", "clone", "--depth", "1", "-q", r, d], check=True)
    return d

def run(repo=None, addresses=None, chain=None, chain_id=1, reserves=(), admins=()):
    chain = chain or Chain(chain_id)
    claimed, meta, src = C.load_deployments(repo, chain.chain_id) if repo else ({}, {}, None)
    for spec in addresses or []:
        n, _, a = spec.rpartition("=")
        claimed[n or a[:10]] = a
    admins = list(admins) + [meta.get(k) for k in ("admin", "owner", "treasury", "oracleUpdater", "deployer") if isinstance(meta.get(k), str)]
    admins = list(dict.fromkeys(a.lower() for a in admins if a))
    readme = C.readme_text(repo) if repo else ""
    tokens = C._tokens(chain, claimed)
    f = []
    f += C.check_tests(repo, claimed) if repo else [C.Finding("tests", "skip", "No repo given", [])]
    f += C.check_deployments(chain, repo, claimed)
    f += C.check_verified(chain, claimed)
    f += C.check_reserve(chain, claimed, reserves, tokens)
    f += C.check_liquidity(chain, readme, tokens)
    f += C.check_admin(chain, claimed, admins)
    f += C.check_supply(readme, tokens)
    return {"chainId": chain.chain_id, "deployments_file": src, "contracts": claimed,
            "findings": [x.to_dict() for x in f], "dark": sum(x.status == "dark" for x in f),
            "lit": sum(x.status == "lit" for x in f)}

def markdown(rep, title="fakecoin report"):
    L = [f"# {title}", "", f"Chain {rep['chainId']} · deployments file: `{rep['deployments_file']}` · **{rep['lit']} lit, {rep['dark']} dark**", "",
         "| Contract | Address |", "|---|---|"] + [f"| {n} | `{a}` |" for n, a in rep["contracts"].items()] + [""]
    L += ["| Check | Status | Finding |", "|---|---|---|"]
    for x in rep["findings"]: L.append(f"| {x['check']} | **{x['status']}** | {x['title']} |")
    for k in ORDER:
        L += ["", f"## {NAMES[k]}"]
        for x in [x for x in rep["findings"] if x["check"] == k]:
            L.append(f"- **{x['status']}**: {x['title']}")
            L += [f"  - {e}" for e in x["evidence"]]
    L += ["", "_lit = the claim holds on-chain; dark = it does not. Read-only RPC: no transaction was sent._", ""]
    return "\n".join(L)

def main(argv=None):
    p = argparse.ArgumentParser("fakecoin", description="Detect token repos whose CI is lit but which are dark on-chain.")
    p.add_argument("repo", nargs="?", help="local path, owner/name, or git URL")
    p.add_argument("-a", "--address", action="append", default=[], help="[Name=]0xADDR (repeatable)")
    p.add_argument("--chain", type=int, default=1, help="chain id (default 1)")
    p.add_argument("--rpc", help="JSON-RPC URL (default publicnode)")
    p.add_argument("--reserve", action="append", default=[], help="extra claimed reserve address")
    p.add_argument("--admin", action="append", default=[], help="claimed admin address")
    p.add_argument("--md", help="write markdown report here"); p.add_argument("--json", help="write JSON here")
    p.add_argument("--title", default=None)
    a = p.parse_args(argv)
    repo = resolve_repo(a.repo)
    rep = run(repo, a.address, Chain(a.chain, a.rpc), a.chain, a.reserve, a.admin)
    md = markdown(rep, a.title or f"fakecoin: {a.repo or 'addresses'}")
    if a.md: open(a.md, "w").write(md)
    if a.json: open(a.json, "w").write(json.dumps(rep, indent=2))
    if not a.md: print(md)
    return 1 if rep["dark"] else 0

if __name__ == "__main__": sys.exit(main())
