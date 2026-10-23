"""Offline tests: a FakeChain stands in for JSON-RPC + Sourcify. No network."""
import os, unittest
from fakecoin import cli, checks as C
from fakecoin.keccak import keccak256, selector
from fakecoin.chain import pad, DEX

FX = os.path.join(os.path.dirname(__file__), "fixtures")
WETH, USDC, F2, F3 = DEX[1]
def w(i): return "0x" + hex(i)[2:].rjust(64, "0")

class FakeChain:
    chain_id = 1
    def __init__(self, codes, balances=None, calls=None, sourcify=None):
        self.codes, self.balances, self.calls, self.src = {k.lower(): v for k, v in codes.items()}, balances or {}, calls or {}, sourcify or {}
    def code(self, a): return self.codes.get(a.lower(), "0x")
    def balance(self, a): return self.balances.get(a.lower(), 0)
    def storage(self, a, s): return w(0)
    def sourcify(self, a): return self.src.get(a.lower())
    def call_sig(self, to, sig, *args):
        if to.lower() not in self.codes: return "0x"
        return self.calls.get((to.lower(), sig) + args, self.calls.get((to.lower(), sig), None))

TOK = "0x1111111111111111111111111111111111111111"; LIT = "0x4444444444444444444444444444444444444444"
ADM = "0x00000000000000000000000000000000000000ad"; MINTER = keccak256(b"MINTER_ROLE").hex()

class TestKeccak(unittest.TestCase):
    def test_vectors(self):
        self.assertEqual(keccak256(b"").hex(), "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470")
        self.assertEqual(selector("transfer(address,uint256)"), "a9059cbb")

class TestDark(unittest.TestCase):
    def setUp(self):
        self.chain = FakeChain({TOK: "0x6080", "0x2222222222222222222222222222222222222222": "0x6080"}, calls={
            (TOK, "totalSupply()"): w(5 * 10**24), (TOK, "decimals()"): w(18),
            (TOK, "hasRole(bytes32,address)", "00" * 32, pad(ADM)): w(1),
            (TOK, "hasRole(bytes32,address)", MINTER, pad(ADM)): w(1)})
        self.rep = cli.run(os.path.join(FX, "darkcoin"), chain=self.chain)
        self.by = lambda c: [f for f in self.rep["findings"] if f["check"] == c]
    def test_tests_dark(self): self.assertEqual(self.by("tests")[0]["status"], "dark")
    def test_ghost_no_code(self):
        self.assertTrue(any(f["status"] == "dark" and "Ghost" in f["title"] for f in self.by("deployed")))
    def test_unverified(self): self.assertTrue(all(f["status"] == "dark" for f in self.by("verified")[:-1]))
    def test_reserve_empty(self): self.assertEqual(self.by("reserve")[0]["status"], "dark")
    def test_no_liquidity(self): self.assertEqual(self.by("liquidity")[0]["status"], "dark")
    def test_admin_info(self):
        a = self.by("admin")[0]; self.assertEqual(a["status"], "info")
        self.assertIn("no cap() function: mint is unlimited", a["evidence"]); self.assertIn(f"{ADM} is EOA", a["evidence"])
    def test_supply_mismatch(self): self.assertEqual(self.by("supply")[0]["status"], "dark")
    def test_markdown_words(self):
        md = cli.markdown(self.rep).lower()
        self.assertIn("dark", md); self.assertNotIn("green", md); self.assertNotIn("red", md.replace("reserve", "").replace("ered", ""))

class TestLit(unittest.TestCase):
    def test_all_lit(self):
        res = "0x5555555555555555555555555555555555555555"; pool = "0x" + "77" * 20
        ch = FakeChain({LIT: "0x6080", res: "0x6080"}, balances={res: 10**18}, calls={
            (LIT, "totalSupply()"): w(10**24), (LIT, "decimals()"): w(18),
            (F2, "getPair(address,address)", pad(LIT), pad(WETH)): "0x" + pad(pool),
            (LIT, "balanceOf(address)", pad(pool)): w(10**20)},
            sourcify={LIT: {"match": "exact_match"}, res: {"match": "match"}})
        ch.codes[F2.lower()] = "0x60"; ch.codes[F3.lower()] = "0x60"
        rep = cli.run(os.path.join(FX, "litcoin"), chain=ch)
        self.assertEqual(rep["dark"], 0, [f for f in rep["findings"] if f["status"] == "dark"])

class TestBytecode(unittest.TestCase):
    def test_immutables_masked(self):
        ok, _ = C.compare_bytecode("6080aaaa00", [{"start": 2, "length": 2}], "0x6080bbbb00"); self.assertTrue(ok)
        ok, _ = C.compare_bytecode("6080aaaa00", [], "0x6080bbbb00"); self.assertFalse(ok)

if __name__ == "__main__": unittest.main()
