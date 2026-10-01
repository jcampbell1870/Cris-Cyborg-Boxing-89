# Cris Cyborg Boxing - Python 3

The Python 3 rewrite of the game: the boxing engine, the online lobby with
one-vs-one tables and eight-max sit-and-go tournaments (GG Poker style), and
the Arcade1870 (ARC / A1870) reward payout system.

The payout system and the treasury vault are **identical to
[Crypto Hockey](https://www.cryptohockey.org)**: a flat **10 ARC per completed
game**, issued as an EIP-712 signed claim against the *same* shared, pre-funded
`Arcade1870RewardVault` contract. Do not deploy a second vault for this game.

| Setting | Value |
| --- | --- |
| Reward token | Arcade1870 (`A1870` / ARC) `0x8eddD4edea39c5B5f77662453600F53A202EE47C` |
| Reward vault (shared treasury) | `0x1e4f6e4a382adbdb662733a19ae773d3ab8f497d` |
| Chain | Ethereum Mainnet (chain id `1`) |
| Payout | `10` ARC per completed game |
| Token decimals | `18` |
| Claim TTL | `600` seconds (60 second floor) |

## Layout

```
python/
  criscyborg/
    config.py      Arcade1870 + server configuration (Crypto Hockey values)
    models.py      Player, Match, Tournament, Reward
    wallet.py      MetaMask address / personal_sign verification
    auth.py        Sign-in challenges and JWT session tokens
    rewards.py     EIP-712 Arcade1870RewardVault claim issuer
    online.py      Lobby: heads-up tables + 8-max sit-and-go brackets
    game/          Boxing engine (port of the Unreal C++ gameplay) and AI
    server/app.py  FastAPI REST + WebSocket server
    client/        pygame client, terminal client, HTTP client
  tests/           pytest suite
```

## Install and run

```sh
cd python
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# Reward signer key - never commit this, load it from a secrets manager.
export REWARD_SIGNER_PRIVATE_KEY=0x...
export JWT_SECRET=$(python -c "import secrets;print(secrets.token_urlsafe(48))")

uvicorn criscyborg.server.app:app --reload
```

The web server requirements intentionally exclude `pygame`. To install the
optional desktop renderer, run `pip install -r requirements-client.txt`.

## Deploy the web service on Render

Create a Python web service with **Root Directory** set to `python`, then use:

| Setting | Value |
| --- | --- |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn criscyborg.server.app:app --host 0.0.0.0 --port $PORT` |

The web-service requirements exclude `pygame`, so Render does not need SDL2 to
build the API service.

Offline practice bout (no server required):

```sh
python -m criscyborg.client.pygame_client --difficulty Expert
python -m criscyborg.client.pygame_client --resolution 3840x2160 --fullscreen
python -m criscyborg.client.terminal practice --difficulty Hard
```

The Pygame renderer scales its 2D graphics for high-resolution displays. The
GitHub Pages site also offers standalone Windows and Chromebook Linux builds;
the latter runs in the 64-bit Chromebook Linux development environment.

Controls: `A`/`D` move, `J` jab, `K` hook, `L` special, `Space` dodge, `Esc` quit.
Bouts are three 120 second rounds; a knockout ends the fight immediately,
otherwise the decision goes to points and then to remaining health.

## Online play

Players sign in with their wallet: `POST /api/auth/challenge` returns a nonce
message, the wallet signs it with `personal_sign`, and `POST /api/auth/login`
returns a JWT session token, sent in the `Authorization` header (bearer
scheme) on every later call.

### One vs one

| Endpoint | Purpose |
| --- | --- |
| `POST /api/matches` | Open a heads-up table with one seat free |
| `POST /api/matches/quick` | Take the first open seat, or open a table |
| `POST /api/matches/{id}/join` | Sit down at a specific open table |
| `POST /api/matches/{id}/result` | Report the winner (seated players only) |
| `WS /ws/match/{id}?token=...` | Realtime input/state relay between seats |

### Eight-person tournaments

| Endpoint | Purpose |
| --- | --- |
| `POST /api/tournaments` | Register a new 8-max sit-and-go (host takes seat 1) |
| `POST /api/tournaments/{id}/register` | Take a seat |
| `POST /api/tournaments/{id}/unregister` | Leave before the tournament starts |
| `GET /api/tournaments/{id}` | Bracket, seats and champion |
| `GET /api/lobby` | Open tables and running sit-and-gos |

The sit-and-go auto-starts the moment the eighth seat is filled: entrants are
shuffled, seated into four quarter-finals, and winners advance through a
semi-final and a final until one champion remains.
On completion, the champion is awarded an in-game Championship Belt for that
tournament. The belt appears on the champion's player profile
(`GET /api/players/me`) and in the tournament and lobby responses as
`championshipBelt`; it is separate from the per-bout ARC claims. Like the
current lobby and tournament records, belts are held in server memory and do
not survive a server restart.

## Reward flow

1. A seated player reports the result of a completed bout.
2. The server signs `Claim(address recipient, uint256 amount, uint256 nonce,
   uint256 deadline)` for the winner against the shared vault - it never
   transfers ARC and never holds custody of funds. The amount is always
   resolved server-side, and each game can only ever be rewarded once.
3. The winner submits `claim(amount, nonce, deadline, signature)` to
   [`Arcade1870RewardVault`](../contracts/Arcade1870RewardVault.sol) from their
   own wallet, paying their own gas, and receives ARC directly.
4. The client calls `POST /api/rewards/{id}/complete` with the transaction hash
   so the payout is recorded.

`GET /api/rewards/config` and `GET /health/reward-issuer` expose the vault,
token and chain the server is configured for.

## Tests

```sh
cd python
python -m pytest
```
