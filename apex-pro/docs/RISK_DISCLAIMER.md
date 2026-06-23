# Risk Disclaimer & Responsible Use

**Read this before enabling live trading.**

## Financial risk
- Trading cryptocurrencies and derivatives is **extremely risky**. You can lose
  **all** of your capital. Leverage multiplies both gains and losses and can
  liquidate a position in seconds.
- Past backtest or paper performance **does not** predict future results.
- This software has **no profit guarantee**. It is a research/education tool and
  a framework. Bugs, exchange outages, network latency, oracle failures and
  black-swan events can and will cause losses.
- Only trade with money you can afford to lose entirely.

## Your responsibility
By enabling `APEX_LIVE_TRADING_ENABLED=true` you accept full responsibility for
all orders the agent places and all resulting outcomes. The authors and
contributors accept **no liability**.

## Legal & ethical scope
APEX is built for **legitimate** market participation only:
- ✅ Market making, arbitrage (incl. backrun/cross-venue), trend/mean-reversion,
  yield optimisation, liquidations, sentiment analysis, on-chain analytics.
- ❌ **Not implemented and not supported:** sandwich attacks / victim
  front-running, orchestrating or amplifying pump-and-dumps, wash trading,
  spoofing/layering, or any market manipulation. The pump-and-dump detector
  exists to *avoid* such schemes, not to run them. Market manipulation is
  **illegal** in most jurisdictions.
- You are responsible for compliance with the laws and regulations applicable
  to you (securities, derivatives, tax, AML/KYC, and exchange terms of service).

## Operational safety (strongly recommended)
- Keep `APEX_MODE=paper` until you've completed the [TESTING.md](TESTING.md)
  checklist.
- Use **trade-only** API keys with withdrawals **disabled** and IP allow-listed.
- For DeFi, use a **dedicated hot wallet** with a small balance — never your
  main wallet. Private keys belong in a secrets manager, never in plaintext.
- Keep position/leverage caps conservative. `degen` mode is genuinely dangerous;
  it requires 2FA + an explicit typed confirmation for a reason.
- Keep `/pause` reachable at all times.
