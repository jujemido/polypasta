# 🧠 PolypastaBot

**Sistema multi-agente de trading algorítmico.**  
5 agentes con personalidades distintas, capital independiente y cartera protegida.

---

## 🏗️ Arquitectura

```
                    🧠 AgentOrchestrator
                    ┌──────────────────┐
                    │ Coordina ciclos  │
                    │ Consolida datos  │
                    │ State recovery   │
                    └────────┬─────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
   ┌──────────┐      ┌──────────┐      ┌──────────┐
   │ Agent 1  │      │ Agent 2  │      │ Agent N  │
   │ 25% cap  │      │ 35% cap  │      │ ...      │
   └────┬─────┘      └────┬─────┘      └──────────┘
        │                 │
        ▼                 ▼
   ┌─────────────────────────────┐
   │      Broker Interface       │
   │  ┌──────────┐ ┌──────────┐  │
   │  │ Sandbox  │ │   MT5    │  │  ← intercambiable
   │  │(Yahoo Fi)│ │ (HFM)    │  │
   │  └──────────┘ └──────────┘  │
   └─────────────────────────────┘
```

---

## 🤖 Los 5 Agentes

| # | Agente | Capital | Timeframe | Símbolos | Estrategia | Win rate |
|:-:|--------|:-------:|:---------:|:--------:|-----------|:--------:|
| 1 | 🤵 **Conservador** | 25% | 1h | 48 (IBEX, DAX, SAP, TEF...) | SMA crossover + confirmación | 70% |
| 2 | 🏃 **Agresivo** | 35% | 15m | 69 (US100, NVDA, BTC, GME...) | RSI extremo + Bollinger + momentum | 50% |
| 3 | 🧐 **Pesimista** | 20% | 1h | 46 (XAU, EURUSD, VIX, SQQQ...) | Stress test + margen seguridad | 65% |
| 4 | 🐢 **Largo Plazo** | 20% | 1d | 66 (AAPL, JPM, SPY, LLY...) | MACD mensual + SMA200 + tendencia | 80% |
| 5 | 💰 **Tesorero** | — | — | — | 20% de profits → hucha protegida | — |

---

## ⚙️ Sistema de Logs

Cada acción genera **5 tipos de logs** con distinto propósito:

### 1. 📊 `data/dashboard_data.json` — Dashboard en tiempo real
**Qué contiene:** Métricas consolidadas, estado de agentes, últimas señales, resúmenes IA, histórico de equity.  
**Quién lo consume:** El frontend React (shadcn/ui) en `http://localhost:8050`.  
**Frecuencia:** Se reescribe cada ciclo del orquestador.  
**Ejemplo:**
```json
{
  "last_updated": "2026-07-11T11:35:03",
  "total": { "balance_actual": 142.66, "treasury_balance": 8.46, "total_trades": 48 },
  "agents": [{ "agent_id": "aggressive", "balance_actual": 350.00, ... }],
  "agent_logs": [{ "timestamp": "...", "agent_name": "🏃 Agresivo", "conclusion": "BUY", ... }],
  "trade_summaries": [{ "period": "últimas 24h", "ai_analysis": "...", "win_rate": 67 }],
  "training_logs": [{ ... }]
}
```

### 2. 💾 `data/state.json` — Persistencia entre reinicios  
**Qué contiene:** Balances actuales, total de trades, trades ganados de cada agente.  
**Propósito:** Si el bot se para (cierras terminal, se va la luz), al reiniciar recupera los balances exactos.  
**Se restaura automáticamente** al arrancar el orquestador (`AgentOrchestrator.__init__`).

### 3. 📈 `data/logs/performance.json` — Métricas agregadas  
**Qué contiene:** Sharpe ratio, profit factor, drawdown máximo, win rate global, avg profit, std profit.  
**Propósito:** Evaluación objetiva del rendimiento del sistema. Útil para comparar entre configuraciones.

### 4. 🎓 `data/logs/training/analysis_YYYYMM.jsonl` — Training logs (formato JSONL)  
**Qué contiene:** Una línea por trade/análisis. Cada línea tiene:  
  - `agent_id`, `agent_name`, `symbol`, `price`  
  - `indicators_full`: RSI, volumen, y todos los indicadores en el momento del análisis  
  - `conclusion`: BUY / SELL / HOLD  
  - `confidence`: 0.0–1.0  
  - `action_taken`: executed / skipped / blocked_by_ai  
  - `ai_validation`: Resultado del AI Validator (si está activo)  
**Propósito:** Entrenamiento futuro del bot. Con estos datos se puede:  
  - Entrenar un modelo ML que prediga qué señales acertarán  
  - Analizar qué combinación de indicadores funciona mejor  
  - Detectar en qué condiciones el bot falla sistemáticamente  

### 5. 📋 `agent_logs` (en memoria) — Dashboard en vivo  
**Qué contiene:** Últimas 200 entradas del resumen de cada análisis.  
**Propósito:** Visualización en tiempo real en la pestaña 📋 Logs del dashboard.  
**Importante:** Al parar el bot se pierden (se recuperan del training logs si es necesario).

---

## 🤖 AI Validator

El **AI Validator** es un filtro opcional que revisa cada señal antes de ejecutarla:

```
1. Agente genera señal → BUY US100 @ 19.820
2. AI Validator llama a DeepSeek V4 vía OpenRouter
3. DeepSeek evalúa: precio, RSI, volumen, tendencia, contexto
4. Responde: APPROVE o BLOCK + motivo
5. Si APPROVE → trade ejecutado
6. Si BLOCK → trade saltado, log con motivo
```

**Activar:** `config/learning.yaml` → `ai_validator.enabled: true`  
**Requisito:** Variable de entorno `OPENROUTER_API_KEY` configurada  
**Coste:** ~$0.001 por validación (en DeepSeek V4 Flash)

---

## 🏖️ Modos de ejecución

### Sandbox (gratis, sin instalar nada)
```
python run.py
# Usa Yahoo Finance para datos reales
# Trades simulados, sin dinero real
# Dashboard en http://localhost:8050
```

### Backtest
```
python run.py --backtest
# Simula con datos históricos
```

### Real (HFM + MT5)
```
# 1. Configurar broker en config/broker.yaml
# 2. Asegurar MT5 abierto
# 3. Ejecutar
python run.py --mode live --interval 120
```

---

## 🚀 Dashboard

Frontend React con **shadcn/ui**, tipografía **Inter**, diseño **blanco y negro**, **a11y compliant**.

```
┌─────────────────┬──────────────┐
│  📊 Dashboard   │  📋 Logs     │  ← Tabs
└─────────────────┴──────────────┘

📊 Dashboard:
  • Resumen global (Balance, Trading, Tesorería, P&L)
  • 5 tarjetas de agente (click para ocultar/mostrar)
  • Tabla comparativa de agentes
  • Curva de capital (incluye línea de tesorería)
  • Posiciones abiertas + Últimos trades

📋 Logs:
  • Logs de actividad (paginación 20/page)
  • Tags con tooltips: COMPRA / VENTA / EJECUTADO / BLOQUEADO
  • Resúmenes IA generados automáticamente
  • Training logs completos
```

---

## 🔧 Comandos rápidos

```bash
# Arrancar bot sandbox
cd ~/Documents/Polypasta
source venv/bin/activate
python run.py

# Arrancar solo dashboard
python dashboard/dashboard_server.py  # → http://localhost:8050

# QA agent (simular 20+ ciclos)
python scripts/qa_agent.py

# Validar símbolos Yahoo Finance
python3 -c "
from src.core.sandbox_broker import resolve_symbol
print(resolve_symbol('SAP'))  # → SAP.DE
print(resolve_symbol('TEF'))  # → TEF.MC
"

# Ver estado persistente
cat data/state.json | python3 -m json.tool

# Ver training logs
head -5 data/logs/training/analysis_*.jsonl
```

---

## 📁 Estructura del proyecto

```
Polypasta/
├── config/              # YAML configuration
│   ├── agents.yaml      #   5 agentes (229 símbolos total)
│   ├── broker.yaml      #   sandbox / hfm
│   ├── strategy.yaml    #   parámetros estrategia
│   ├── risk.yaml        #   Kelly, SL/TP, drawdown
│   ├── learning.yaml    #   AI Validator + logs
│   └── paths.yaml       #   rutas
├── src/
│   ├── agents/          #   5 agentes + orquestador
│   ├── core/            #   engine + broker
│   ├── learning/        #   AI Validator + Summary Logger
│   ├── strategies/      #   lógica de trading
│   ├── risk/            #   gestión de riesgo
│   ├── notifier/        #   Telegram
│   ├── dashboard/       #   servidor web
│   └── utils/           #   config, time, file, backtest
├── dashboard/           # React + shadcn/ui (Vite)
├── data/
│   ├── dashboard_data.json  # frontend data
│   ├── state.json           # persistence
│   └── logs/
│       ├── performance.json # métricas agregadas
│       └── training/        # JSONL por agente
└── scripts/
    └── qa_agent.py      # test automatizado
```

---

## 🌐 Repositorio

https://github.com/jujemido/polypasta

Hecho con ❤️ por [@jujemido](https://github.com/jujemido)