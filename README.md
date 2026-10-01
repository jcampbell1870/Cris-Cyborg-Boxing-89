# Cris Cyborg Boxing 89

A 2D boxing game built with Unreal Engine 5.3 for **Windows PC (Win64)**,
featuring online matchmaking, tournaments, and play-to-earn rewards in
**Arcade1870 (ARC)** - the same ERC-20 token and non-custodial reward system
used by [Crypto Chess](https://www.cryptochess.org).

## Project layout

- `python/` - the **Python 3 rewrite** of the game: boxing engine, FastAPI
  online server, GG Poker style lobby (one-vs-one tables and eight-person
  sit-and-go tournaments), pygame/terminal clients and the Arcade1870 reward
  payout system. See [`python/README.md`](python/README.md).
- `UnrealEngine/` - the original Unreal Engine 5.3 game project (C++ gameplay
  code, Win64-only per `CrisCyborgBoxing.uproject`).
- `Backend/CrisCyborgBoxing.Backend/` - the ASP.NET Core backend: auth,
  matchmaking, tournaments, and Arcade1870 reward-claim issuance.
- `contracts/Arcade1870RewardVault.sol` - the shared vault contract that
  releases ARC for signed reward claims.
- `docs/` - the GitHub Pages site and downloadable Python desktop game ZIP
  (published from this folder - see below).
- `Packaging/WindowsStore/` - MSIX packaging scaffold for a Microsoft Store
  submission.

## Arcade1870 (ARC) reward system

Rewards are issued using the same non-custodial pattern as Crypto Chess and
Crypto Hockey - a flat **10 ARC per completed game**:

1. After a match win, tournament victory, or other reward event, the game
   calls `POST /api/rewards/claim` on the backend.
2. The backend signs an EIP-712 `Claim(address recipient, uint256 amount,
   uint256 nonce, uint256 deadline)` message using a dedicated reward-signer
   key and returns it to the game - it does **not** transfer ARC itself.
3. The game (or the player's connected wallet) submits
   `claim(amount, nonce, deadline, signature)` directly to the deployed
   [`Arcade1870RewardVault`](contracts/Arcade1870RewardVault.sol) contract,
   paying its own gas, and receives ARC straight into the player's wallet.
4. The game then calls `POST /api/rewards/{rewardId}/complete` with the
   resulting transaction hash so the backend can record it.

This vault contract is **chain- and consumer-agnostic**: the same deployed,
funded `Arcade1870RewardVault` address is shared as the treasury across
multiple Arcade1870 games (Crypto Chess and Cris Cyborg Boxing both point at
it). Do not deploy a second vault for this game - reuse the existing
address. See [`Backend/CrisCyborgBoxing.Backend/appsettings.json`](Backend/CrisCyborgBoxing.Backend/appsettings.json)
`BlockchainConfig` for where the token address, vault address, and reward
signer key are configured (the signer key must be stored in a secrets
manager in production, never committed to source control).

## Downloading the game

The [GitHub Pages site](docs/index.html) (published from the `docs/` folder,
see [`.github/workflows/pages.yml`](.github/workflows/pages.yml)) provides
standalone Windows 10/11 (64-bit) and Chromebook Linux (64-bit Intel/AMD)
downloads, as well as the Python source ZIP. The Chromebook build requires the
ChromeOS Linux development environment; it does not run in the browser. The
Pygame practice game supports custom 1440p and 4K resolutions. These are
standalone 2D builds, not packaged Unreal Engine games; the Unreal project
remains source-only, and packaged Unreal builds, if published, are listed on
the [Releases](../../releases) page.

## Microsoft Store version

See [`Packaging/WindowsStore/README.md`](Packaging/WindowsStore/README.md)
for step-by-step instructions to package the same Win64 build as an MSIX
package for Microsoft Store submission.

## Python development

```sh
cd python
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export REWARD_SIGNER_PRIVATE_KEY=0x...   # from a secrets manager, never committed
uvicorn criscyborg.server.app:app --reload
python -m criscyborg.client.pygame_client --difficulty Expert
python -m pytest
```

## Backend development

```sh
cd Backend/CrisCyborgBoxing.Backend
dotnet restore
dotnet build
dotnet run
```

Configure `BlockchainConfig` in `appsettings.Development.json` (or user
secrets) with a testnet RPC URL, the Arcade1870 token address, a testnet
deployment of `Arcade1870RewardVault`, and a dev reward-signer key before
testing the reward-claim flow end to end.
