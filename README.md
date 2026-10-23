# fakecoin

Sibling of [fakegreen](https://github.com/fitzyracing1/fakegreen), for crypto projects. fakegreen catches faked lit CI in AI-written PRs. fakecoin catches coin and token repos that **pass** (lit CI, confident README) but are **dark on-chain**.

Python 3.9+, standard library only. It uses public JSON-RPC (publicnode) and the Sourcify API. You don't need API keys. It only makes read calls (`eth_call`, `eth_getCode`, `eth_getBalance`, `eth_getStorageAt`) and never sends a transaction.

```bash
pip install git+https://github.com/fitzyracing1/fakecoin
fakecoin ./my-token-repo --md report.md --json report.json      # repo path, owner/name or git URL
fakecoin -a SpaceToken=0x0af0...846e -a Reserve=0x9D8E...1A8D --chain 1
```

Exit code 1 if any check is **dark**.

## Checks

| # | Check | lit | dark |
|---|---|---|---|
| 1 | Tests | a test forks (`createSelectFork`, `forking:`, `--fork-url`) or references a deployed address | tests only use mocks or a local chain |
| 2 | Deployments | every address in `deployments/*.json` (or `-a`) has code, and the runtime bytecode matches `out/`/`artifacts/` (immutables masked, CBOR stripped) | no code, or the bytecode differs |
| 3 | Verification | Sourcify `match`/`exact_match` | not verified (Etherscan only runs if `ETHERSCAN_API_KEY` is set, otherwise skip) |
| 4 | Reserve | the claimed reserve/treasury/vault holds ETH, the token itself, WETH or USDC | balance is zero |
| 5 | Liquidity | Uniswap v2 `getPair` / v3 `getPool` (4 fee tiers) vs WETH and USDC returns a pool that holds tokens | no pool, and the docs use price/market language |
| 6 | Admin power | **info**: `owner()`, AccessControl roles, EIP-1967 proxy slots, mint cap, and whether the holder is an EOA or a contract | n/a |
| 7 | Supply | `totalSupply()` matches the "total/max supply" stated in the docs | mismatch, or zero supply |

## Reports
- [reports/space-money.md](reports/space-money.md): fitzyracing1/space-money on mainnet.

## Tests
`python -m unittest discover -s tests` runs offline against fixtures and a fake chain.

MIT © 2026 Joshua Almeida
