from datetime import UTC, datetime


MOCK_CFO_SUMMARY = {
    "generated_at": datetime.now(UTC).isoformat(),
    "mode": "mock",
    "cash_position": {"amount": 4_250_000, "currency": "USD"},
    "open_receivables": {"amount": 1_175_000, "currency": "USD"},
    "monthly_revenue": {"amount": 2_980_000, "currency": "USD"},
    "kpis": [
        {
            "label": "Cash runway",
            "value": "14.2 months",
            "trend": "up",
            "narrative": "Mock operating cash trend improved against the prior period.",
        },
        {
            "label": "DSO",
            "value": 42,
            "trend": "down",
            "narrative": "Mock receivables collection velocity improved by 3 days.",
        },
        {
            "label": "Gross margin",
            "value": "61.4%",
            "trend": "flat",
            "narrative": "Mock margin stayed within the expected operating band.",
        },
    ],
}

MOCK_TEMPLATE_ROWS: dict[str, list[dict[str, str | float]]] = {
    "cash_position_summary": [
        {"account": "Operating Cash", "balance": 2_850_000, "currency": "USD"},
        {"account": "Money Market", "balance": 1_400_000, "currency": "USD"},
    ],
    "ar_aging_summary": [
        {"bucket": "Current", "amount": 720_000, "currency": "USD"},
        {"bucket": "1-30", "amount": 310_000, "currency": "USD"},
        {"bucket": "31-60", "amount": 110_000, "currency": "USD"},
        {"bucket": "60+", "amount": 35_000, "currency": "USD"},
    ],
    "monthly_revenue_trend": [
        {"period": "2026-01", "revenue": 2_620_000, "currency": "USD"},
        {"period": "2026-02", "revenue": 2_740_000, "currency": "USD"},
        {"period": "2026-03", "revenue": 2_910_000, "currency": "USD"},
        {"period": "2026-04", "revenue": 2_980_000, "currency": "USD"},
    ],
}
