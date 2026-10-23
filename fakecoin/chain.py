import json, urllib.request
from .keccak import selector

DEFAULT_RPC = {1: "https://ethereum-rpc.publicnode.com", 11155111: "https://ethereum-sepolia-rpc.publicnode.com",
               8453: "https://base-rpc.publicnode.com"}
EIP1967_IMPL = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
EIP1967_ADMIN = "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"
# chain -> (WETH, USDC, UniV2 factory, UniV3 factory)
DEX = {1: ("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
           "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f", "0x1F98431c8aD98523631AE4a59f267346ea31F984")}

def _post(url, payload, timeout=20):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"content-type": "application/json", "user-agent": "fakecoin"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def _get(url, timeout=20):
    req = urllib.request.Request(url, headers={"user-agent": "fakecoin"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b"null")
        except Exception: return e.code, None

def pad(addr): return addr.lower().replace("0x", "").rjust(64, "0")

class Chain:
    """Read-only JSON-RPC client. Only eth_call/eth_getCode/eth_getBalance/eth_getStorageAt: never sends a transaction."""
    def __init__(self, chain_id=1, rpc=None):
        self.chain_id = chain_id
        self.rpc = rpc or DEFAULT_RPC.get(chain_id)
        self._id = 0
    def _rpc(self, method, params):
        self._id += 1
        r = _post(self.rpc, {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params})
        if "error" in r: raise RuntimeError(f"{method}: {r['error']}")
        return r["result"]
    def code(self, a): return self._rpc("eth_getCode", [a, "latest"])
    def balance(self, a): return int(self._rpc("eth_getBalance", [a, "latest"]), 16)
    def storage(self, a, slot): return self._rpc("eth_getStorageAt", [a, slot, "latest"])
    def call(self, to, data):
        try: return self._rpc("eth_call", [{"to": to, "data": data}, "latest"])
        except RuntimeError: return None
    def call_sig(self, to, sig, *args):
        return self.call(to, "0x" + selector(sig) + "".join(args))
    def sourcify(self, a):
        st, body = _get(f"https://sourcify.dev/server/v2/contract/{self.chain_id}/{a}")
        return body if st == 200 else None

def word_int(h):
    if not h or h == "0x": return None
    return int(h[2:66] or "0", 16)
def word_addr(h):
    if not h or len(h) < 66: return None
    return "0x" + h[-40:]
