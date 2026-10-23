# fakecoin: fitzyracing1/space-money (mainnet)

Chain 1 · deployments file: `deployments/mainnet.json` · **9 lit, 2 dark**

| Contract | Address |
|---|---|
| SpaceToken | `0x0af05969C412Dc1E07be5fC5A4e141214aAe846e` |
| TariffOracle | `0x05D05690425C79a9367c3Ac626F67D148e53Bc6a` |
| Reserve | `0x9D8E61007980d6Cb0ec0E8E4D3adA1F12D791A8D` |
| TariffRouter | `0x0A156a7652f809D6F07a0fCB2D85a8F88b038ABd` |

| Check | Status | Finding |
|---|---|---|
| tests | **lit** | Tests touch a fork or real deployed addresses |
| deployed | **lit** | SpaceToken 0x0af05969C412Dc1E07be5fC5A4e141214aAe846e: code matches repo |
| deployed | **lit** | TariffOracle 0x05D05690425C79a9367c3Ac626F67D148e53Bc6a: code matches repo |
| deployed | **lit** | Reserve 0x9D8E61007980d6Cb0ec0E8E4D3adA1F12D791A8D: code matches repo |
| deployed | **lit** | TariffRouter 0x0A156a7652f809D6F07a0fCB2D85a8F88b038ABd: code matches repo |
| verified | **lit** | SpaceToken verified on Sourcify |
| verified | **lit** | TariffOracle verified on Sourcify |
| verified | **lit** | Reserve verified on Sourcify |
| verified | **lit** | TariffRouter verified on Sourcify |
| verified | **skip** | Etherscan check skipped (no ETHERSCAN_API_KEY) |
| reserve | **dark** | Reserve 0x9D8E61007980d6Cb0ec0E8E4D3adA1F12D791A8D: reserve is empty |
| liquidity | **dark** | SpaceToken has no Uniswap liquidity vs WETH/USDC while docs use market language |
| admin | **info** | SpaceToken: single admin |
| admin | **info** | TariffOracle: single admin |
| admin | **info** | Reserve: single admin |
| admin | **info** | TariffRouter: single admin |
| supply | **info** | SpaceToken supply reported; no supply claim in docs |

## 1. Tests hit a fork / real addresses
- **lit**: Tests touch a fork or real deployed addresses
  - 6 test files scanned
  - 0 mock/local-chain references
  - test/TariffFeed.t.sol:117: vm.createSelectFork(rpc);
  - deployed address referenced: test/TariffFeed.t.sol:112: 0x05D05690425C79a9367c3Ac626F67D148e53Bc6a

## 2. Claimed deployments have matching code
- **lit**: SpaceToken 0x0af05969C412Dc1E07be5fC5A4e141214aAe846e: code matches repo
  - eth_getCode: 5676 bytes
  - runtime bytecode matches repo build (5676 B, 0 immutable ranges masked) (artifact out/SpaceToken.sol/SpaceToken.json)
- **lit**: TariffOracle 0x05D05690425C79a9367c3Ac626F67D148e53Bc6a: code matches repo
  - eth_getCode: 5884 bytes
  - runtime bytecode matches repo build (5884 B, 0 immutable ranges masked) (artifact out/TariffOracle.sol/TariffOracle.json)
- **lit**: Reserve 0x9D8E61007980d6Cb0ec0E8E4D3adA1F12D791A8D: code matches repo
  - eth_getCode: 3302 bytes
  - runtime bytecode matches repo build (3302 B, 3 immutable ranges masked) (artifact out/Reserve.sol/Reserve.json)
- **lit**: TariffRouter 0x0A156a7652f809D6F07a0fCB2D85a8F88b038ABd: code matches repo
  - eth_getCode: 6520 bytes
  - runtime bytecode matches repo build (6520 B, 5 immutable ranges masked) (artifact out/TariffRouter.sol/TariffRouter.json)

## 3. Verified on Sourcify
- **lit**: SpaceToken verified on Sourcify
  - sourcify match=match runtime=match creation=match
  - https://repo.sourcify.dev/1/0x0af05969C412Dc1E07be5fC5A4e141214aAe846e
- **lit**: TariffOracle verified on Sourcify
  - sourcify match=match runtime=match creation=match
  - https://repo.sourcify.dev/1/0x05D05690425C79a9367c3Ac626F67D148e53Bc6a
- **lit**: Reserve verified on Sourcify
  - sourcify match=match runtime=match creation=match
  - https://repo.sourcify.dev/1/0x9D8E61007980d6Cb0ec0E8E4D3adA1F12D791A8D
- **lit**: TariffRouter verified on Sourcify
  - sourcify match=match runtime=match creation=match
  - https://repo.sourcify.dev/1/0x0A156a7652f809D6F07a0fCB2D85a8F88b038ABd
- **skip**: Etherscan check skipped (no ETHERSCAN_API_KEY)

## 4. Reserve / backing holds assets
- **dark**: Reserve 0x9D8E61007980d6Cb0ec0E8E4D3adA1F12D791A8D: reserve is empty
  - ETH balance: 0
  - SpaceToken balance: 0
  - WETH balance: 0
  - USDC balance: 0

## 5. Market liquidity
- **dark**: SpaceToken has no Uniswap liquidity vs WETH/USDC while docs use market language
  - UniV2 getPair(SpaceToken,WETH) = 0x0
  - UniV3 getPool(SpaceToken,WETH, 100/500/3000/10000) = 0x0 for all fee tiers
  - UniV2 getPair(SpaceToken,USDC) = 0x0
  - UniV3 getPool(SpaceToken,USDC, 100/500/3000/10000) = 0x0 for all fee tiers
  - market language in docs: price

## 6. Admin / mint / upgrade power (info)
- **info**: SpaceToken: single admin
  - 0x20ffd7c153b68002ef052614a5600e240e7e2474 has DEFAULT_ADMIN_ROLE
  - 0x20ffd7c153b68002ef052614a5600e240e7e2474 has MINTER_ROLE
  - no cap() function: mint is unlimited
  - 0x20ffd7c153b68002ef052614a5600e240e7e2474 is contract (61 B)
- **info**: TariffOracle: single admin
  - 0x20ffd7c153b68002ef052614a5600e240e7e2474 has DEFAULT_ADMIN_ROLE
  - 0x20ffd7c153b68002ef052614a5600e240e7e2474 has UPDATER_ROLE
  - 0x20ffd7c153b68002ef052614a5600e240e7e2474 is contract (61 B)
- **info**: Reserve: single admin
  - 0x20ffd7c153b68002ef052614a5600e240e7e2474 has DEFAULT_ADMIN_ROLE
  - 0x20ffd7c153b68002ef052614a5600e240e7e2474 has WITHDRAWER_ROLE
  - 0x20ffd7c153b68002ef052614a5600e240e7e2474 is contract (61 B)
- **info**: TariffRouter: single admin
  - 0x20ffd7c153b68002ef052614a5600e240e7e2474 has DEFAULT_ADMIN_ROLE
  - 0x20ffd7c153b68002ef052614a5600e240e7e2474 has CONFIG_ROLE
  - 0x20ffd7c153b68002ef052614a5600e240e7e2474 is contract (61 B)

## 7. Total supply vs claims
- **info**: SpaceToken supply reported; no supply claim in docs
  - totalSupply() = 1,000,000 (1000000000000000000000000 raw, 18 decimals)

_lit = the claim holds on-chain; dark = it does not. Read-only RPC: no transaction was sent._
