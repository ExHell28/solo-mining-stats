# Solo Mining Stats for Home Assistant

A HACS-compatible custom integration for monitoring solo-mining statistics in Home Assistant. It currently supports public [Parasite Pool](https://parasite.space/) and standard CKPool endpoints.

The integration creates one device for each configured Bitcoin address and refreshes its data every 30 seconds.

## Features

- Personal hashrate in TH/s
- 24-hour average hashrate in TH/s
- Personal best difficulty
- Total contributed work
- Active worker count
- Uptime
- Combined leaderboard rank (when present in the public top 100)
- Pool hashrate in PH/s
- Pool best difficulty
- Friendly compact formatting for large difficulty and work values
- Parasite Pool and standard public CKPool endpoint support

## Installation

### HACS

1. In Home Assistant, open **HACS** → **Integrations**.
2. Open the three-dot menu → **Custom repositories**.
3. Add the following repository URL and select **Integration** as the category:

   ```text
   https://github.com/ExHell28/parasite-home-assistant
   ```

4. Find **Parasite Pool** in HACS and choose **Download**.
5. Restart Home Assistant.

### Manual

Copy the `custom_components/parasite` folder into your Home Assistant configuration directory:

```text
config/custom_components/parasite
```

Restart Home Assistant after copying the files.

## Configuration

1. Go to **Settings** → **Devices & services**.
2. Select **Add integration**.
3. Search for **Parasite Pool**.
4. Enter the Bitcoin address used by your Parasite Pool miners.

No API key is required.

### CKPool

Choose one of the following pool types during setup; only the Bitcoin address is required:

- **CKPool** — `solo.ckpool.org`
- **CKPool (EU)** — `eusolo.ckpool.org`

CKPool supplies its own `hashrate1d` value, which is shown as **Hashrate 24h**. Some CKPool installations do not expose a rank or total-work value; those sensors remain unavailable rather than showing incorrect data.

## Notes

- Personal statistics depend on what Parasite Pool exposes for the configured address.
- New, private, or unranked addresses can show unavailable personal values. Pool-wide sensors continue to update normally.
- Large values are displayed in a compact form (for example `63.30 T`); their original numeric values remain available as sensor attributes.

## Data source

This integration uses the public Parasite Pool API:

- `GET /api/pool-stats`
- `GET /api/user/{bitcoin_address}`
- `GET /api/account/{bitcoin_address}`
- `GET /api/leaderboard?type=combined&limit=100`

Parasite Pool is an independent project. This integration is community-maintained and is not affiliated with or endorsed by Parasite Pool.

## Contributing

Issues and pull requests are welcome. Please include the Home Assistant version, integration version, and relevant log output when reporting a problem.
