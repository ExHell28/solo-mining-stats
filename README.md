# Parasite Pool for Home Assistant

HACS-compatible custom integration for the public [Parasite Pool](https://parasite.space/) API. It polls every 30 seconds and creates one device per configured Bitcoin address.

## Sensors

- Personal hashrate (TH/s)
- Personal best difficulty
- Total work (`account.total_diff`)
- Worker count
- Uptime (duration)
- Leaderboard rank (top 100 combined leaderboard only)
- Pool hashrate (PH/s)
- Pool best difficulty

Private, new, or unranked addresses may not have personal data exposed by the public API. In that case the personal sensors remain unavailable while the pool sensors continue to update.

## Install with HACS

1. Extract this repository ZIP, then make the extracted folder available from a GitHub repository (or use HACS's local/custom repository workflow).
2. In HACS, open **Integrations** → the three-dot menu → **Custom repositories**.
3. Add the repository URL and select **Integration** as its category.
4. Find **Parasite Pool**, install it, and restart Home Assistant.
5. Open **Settings** → **Devices & services** → **Add integration** → **Parasite Pool**, then enter your Bitcoin address.

For a manual installation, copy `custom_components/parasite` into your Home Assistant `config/custom_components/` directory and restart Home Assistant.

## API endpoints

The integration uses the public endpoints below:

- `GET /api/pool-stats`
- `GET /api/user/{bitcoin_address}`
- `GET /api/account/{bitcoin_address}`
- `GET /api/leaderboard?type=combined&limit=100`

No API token is needed.

