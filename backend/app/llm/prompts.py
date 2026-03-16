"""System prompt construction for the FinAlly AI trading assistant."""


SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant in a simulated trading workstation.
You help users analyze their portfolio, suggest trades, and execute orders.

You MUST respond with valid JSON matching this exact schema:
{
  "message": "your conversational response",
  "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}],
  "watchlist_changes": [{"ticker": "PYPL", "action": "add"}]
}

Rules:
- "message" is required and contains your conversational response
- "trades" is optional, include only when executing trades
- "watchlist_changes" is optional, include only when modifying the watchlist
- valid "side" values: "buy" or "sell"
- valid "action" values: "add" or "remove"
- Be concise and data-driven
- When the user asks to buy or sell, execute the trade
- When the user asks to add or remove a ticker from the watchlist, do it
- Analyze portfolio composition, risk concentration, and P&L when asked
- All money is simulated -- zero real-world risk"""


def build_system_prompt(portfolio_context: str) -> str:
    """Build the full system prompt with portfolio context."""
    return f"{SYSTEM_PROMPT}\n\nCurrent Portfolio State:\n{portfolio_context}"


def format_portfolio_context(
    cash_balance: float,
    positions: list[dict],
    watchlist: list[dict],
    total_value: float,
) -> str:
    """Format portfolio data into a context string for the LLM."""
    lines = [
        f"Cash: ${cash_balance:,.2f}",
        f"Total Portfolio Value: ${total_value:,.2f}",
    ]

    if positions:
        lines.append("\nPositions:")
        for p in positions:
            unrealized = (p["current_price"] - p["avg_cost"]) * p["quantity"]
            pct = ((p["current_price"] / p["avg_cost"]) - 1) * 100 if p["avg_cost"] > 0 else 0
            lines.append(
                f"  {p['ticker']}: {p['quantity']} shares @ ${p['avg_cost']:.2f} avg, "
                f"now ${p['current_price']:.2f} (P&L: ${unrealized:,.2f}, {pct:+.1f}%)"
            )
    else:
        lines.append("\nNo open positions.")

    if watchlist:
        lines.append("\nWatchlist:")
        for w in watchlist:
            price_str = f" @ ${w['price']:.2f}" if w.get("price") else ""
            lines.append(f"  {w['ticker']}{price_str}")

    return "\n".join(lines)
