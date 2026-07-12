"""
Dashboard — Panel web con Plotly para monitorear el bot en vivo.
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, List, Any

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def generate_dashboard(
    metrics: Dict[str, Any],
    trades: List[Dict[str, Any]],
    df_prices: Optional[Dict[str, Any]] = None,  # symbol → {time, close, bb?}
    output_path: str = "data/dashboard.html",
) -> str:
    """
    Genera un dashboard HTML completo con Plotly.

    Args:
        metrics: Dict de métricas (del RiskManager)
        trades: Lista de trades
        df_prices: Dict con datos de precio por símbolo
        output_path: Ruta del HTML generado

    Returns:
        Ruta absoluta del archivo generado
    """
    if not PLOTLY_AVAILABLE:
        print("⚠️  plotly not installed. Skipping dashboard.")
        return ""

    # ─── Crear figures ───
    figs = []

    # 1. Equity curve
    if trades:
        equity_fig = _build_equity_curve(trades, metrics)
        figs.append(equity_fig)

    # 2. Price chart con señales
    if df_prices:
        for symbol, df in df_prices.items():
            price_fig = _build_price_chart(df, symbol, trades)
            figs.append(price_fig)

    # 3. Trade stats
    stats_fig = _build_stats_panel(metrics)
    figs.append(stats_fig)

    # 4. Win/Loss distribution
    if trades:
        dist_fig = _build_pnl_distribution(trades)
        figs.append(dist_fig)

    # ─── Ensamblar HTML ───
    html_parts = [
        "<!DOCTYPE html><html><head>",
        "<meta charset='UTF-8'>",
        f"<title>PolypastaBot Dashboard — {datetime.now():%d/%m %H:%M}</title>",
        "<script src='https://cdn.plot.ly/plotly-2.32.0.min.js'></script>",
        "<style>",
        "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;",
        "background:#0f172a;color:#e2e8f0;margin:0;padding:20px}",
        "h1{color:#38bdf8}",
        ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(500px,1fr));gap:20px}",
        ".card{background:#1e293b;border-radius:12px;padding:16px;box-shadow:0 4px 6px rgba(0,0,0,.3)}",
        ".metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:20px}",
        ".metric{background:#1e293b;border-radius:8px;padding:12px;text-align:center}",
        ".metric .label{color:#94a3b8;font-size:12px;text-transform:uppercase}",
        ".metric .value{font-size:24px;font-weight:700;margin-top:4px}",
        ".positive{color:#22c55e} .negative{color:#ef4444}",
        "</style></head><body>",
        f"<h1>🤖 PolypastaBot Dashboard</h1>",
        f"<p>Última actualización: {datetime.now():%d/%m/%Y %H:%M:%S}</p>",
    ]

    # ─── Métricas rápidas ───
    html_parts.append("<div class='metrics'>")
    quick_metrics = [
        ("Balance", f"${metrics.get('current_balance', 0):.2f}", ""),
        ("P&L", f"{metrics.get('total_pnl', 0):+.2f}",
         "positive" if metrics.get('total_pnl', 0) >= 0 else "negative"),
        ("Win Rate", f"{metrics.get('win_rate', 0):.0%}", ""),
        ("Trades", str(metrics.get('total_trades', 0)), ""),
        ("Drawdown", f"{metrics.get('current_drawdown', 0):.1%}",
         "negative" if metrics.get('current_drawdown', 0) > 0.05 else ""),
        ("Posiciones", str(metrics.get('open_positions', 0)), ""),
    ]
    for label, value, cls in quick_metrics:
        html_parts.append(
            f"<div class='metric'><div class='label'>{label}</div>"
            f"<div class='value {cls}'>{value}</div></div>"
        )
    html_parts.append("</div>")

    # ─── Plotly figures ───
    html_parts.append("<div class='grid'>")
    for fig in figs:
        html_parts.append("<div class='card'>")
        html_parts.append(fig.to_html(full_html=False, include_plotlyjs=False))
        html_parts.append("</div>")
    html_parts.append("</div>")

    html_parts.append("</body></html>")

    # ─── Guardar ───
    html = "\n".join(html_parts)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)

    print(f"📊 Dashboard generated: {output_path}")
    return output_path


# ─── Helper builders ───

def _build_equity_curve(trades: List[Dict], metrics: Dict) -> go.Figure:
    """Curva de equity acumulada"""
    cumulative = []
    bal = metrics.get("initial_balance", 0)
    cumulative.append({"time": "start", "balance": bal})
    for t in trades:
        bal += float(t.get("profit", 0))
        cumulative.append({
            "time": t.get("timestamp", ""),
            "balance": bal,
        })

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[c["time"] for c in cumulative],
        y=[c["balance"] for c in cumulative],
        mode="lines",
        name="Equity",
        line=dict(color="#38bdf8", width=2),
        fill="tozeroy",
        fillcolor="rgba(56,189,248,0.1)",
    ))
    fig.update_layout(
        title="Equity Curve",
        xaxis_title="Time",
        yaxis_title="Balance ($)",
        template="plotly_dark",
        height=400,
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig


def _build_price_chart(df, symbol: str, trades: List[Dict]) -> go.Figure:
    """Chart de precio con señales de trade"""
    fig = go.Figure()

    # Candlestick o línea
    if all(c in df.columns for c in ["open", "high", "low", "close"]):
        fig.add_trace(go.Candlestick(
            x=df.index if hasattr(df, 'index') else df.get("time", []),
            open=df["open"], high=df["high"],
            low=df["low"], close=df["close"],
            name=symbol,
        ))
    else:
        fig.add_trace(go.Scatter(
            x=df.index if hasattr(df, 'index') else df.get("time", []),
            y=df["close"],
            mode="lines",
            name=symbol,
            line=dict(color="#38bdf8"),
        ))

    # Bollinger Bands si existen
    for band, color in [("bb_upper", "rgba(34,197,94,0.3)"),
                          ("bb_middle", "rgba(34,197,94,0.5)"),
                          ("bb_lower", "rgba(34,197,94,0.3)")]:
        if band in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index if hasattr(df, 'index') else df.get("time", []),
                y=df[band],
                mode="lines",
                name=band,
                line=dict(color=color, width=1),
            ))

    # Señales de trade
    buy_signals = [t for t in trades if t.get("action") == "buy" and symbol in t.get("symbol", "")]
    sell_signals = [t for t in trades if t.get("action") == "sell" and symbol in t.get("symbol", "")]

    if buy_signals:
        fig.add_trace(go.Scatter(
            x=[t.get("timestamp") for t in buy_signals],
            y=[float(t.get("entry_price", 0)) for t in buy_signals],
            mode="markers",
            marker=dict(color="#22c55e", size=10, symbol="triangle-up"),
            name="Buy",
        ))
    if sell_signals:
        fig.add_trace(go.Scatter(
            x=[t.get("timestamp") for t in sell_signals],
            y=[float(t.get("entry_price", 0)) for t in sell_signals],
            mode="markers",
            marker=dict(color="#ef4444", size=10, symbol="triangle-down"),
            name="Sell",
        ))

    fig.update_layout(
        title=f"{symbol} — Price & Signals",
        template="plotly_dark",
        height=400,
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig


def _build_stats_panel(metrics: Dict) -> go.Figure:
    """Panel de métricas numéricas"""
    keys = [
        ("Win Rate", metrics.get("win_rate", 0), 1),
        ("Drawdown", metrics.get("current_drawdown", 0), 1),
        ("Daily P&L", metrics.get("daily_pnl", 0), None),
        ("Weekly P&L", metrics.get("weekly_pnl", 0), None),
        ("Total Trades", metrics.get("total_trades", 0), None),
        ("Open Pos", metrics.get("open_positions", 0), None),
    ]
    labels, values, max_vals = zip(*keys) if keys else ([], [], [])

    fig = go.Figure(data=[
        go.Table(
            header=dict(values=["Metric", "Value"], fill_color="#334155",
                        font=dict(color="#e2e8f0")),
            cells=dict(
                values=[list(labels), [f"{v:.1%}" if isinstance(v, float) and v < 1 else str(v) for v in values]],
                fill_color="#1e293b",
                font=dict(color="#e2e8f0"),
                align=["left", "center"],
                height=30,
            )
        )
    ])
    fig.update_layout(
        title="Statistics",
        template="plotly_dark",
        height=300,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig


def _build_pnl_distribution(trades: List[Dict]) -> go.Figure:
    """Distribución de P&L por trade"""
    pnls = [float(t.get("profit", 0)) for t in trades if t.get("profit") is not None]
    if not pnls:
        return go.Figure()

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=pnls,
        nbinsx=20,
        marker_color="#38bdf8",
        name="P&L Distribution",
    ))
    fig.add_vline(x=0, line_dash="dash", line_color="#ef4444")
    fig.update_layout(
        title="Trade P&L Distribution",
        xaxis_title="Profit ($)",
        yaxis_title="Trades",
        template="plotly_dark",
        height=300,
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig