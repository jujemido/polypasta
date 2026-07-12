# 🧠 PolypastaBot

**Sistema multi-agente de trading algorítmico.**  
5 agentes con personalidades distintas, capital independiente, cartera protegida y validación por IA.

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

| # | Agente | Capital | Timeframe | Símbolos | Estrategia | Win rate obj. |
|:-:|--------|:-------:|:---------:|:--------:|-----------|:------------:|
| 1 | 🤵 **Conservador** | 25% | 1h | 48 (IBEX, DAX, SAP, TEF...) | SMA crossover + confirmación 2 velas + RSI 40-70 | 70% |
| 2 | 🏃 **Agresivo** | 35% | 15m | 69 (US100, NVDA, BTC, GME...) | RSI extremo + Bollinger 2σ + momentum | 50% |
| 3 | 🧐 **Pesimista** | 20% | 1h | 46 (XAU, EURUSD, VIX, SQQQ...) | Stress test + margen seguridad + VIX < 25 | 65% |
| 4 | 🐢 **Largo Plazo** | 20% | 1d | 66 (AAPL, JPM, SPY, LLY...) | MACD mensual + SMA200 + RSI semanal < 60 | 80% |
| 5 | 💰 **Tesorero** | — | — | — | 20% de cada beneficio → hucha protegida | — |

---

## 🔒 Pipeline de validaciones (antes de comprar/vender)

Cada trade pasa por **6 filtros** antes de ejecutarse:

```
1. GENERAR SEÑAL → Cada agente aplica su estrategia
                        │
2. FILTRO DE HORARIO → ¿El mercado está abierto?
                        │
3. FILTRO DE RIESGO → ¿Podemos operar?
                        │
4. FILTRO DE COOLDOWN → ¿No operamos el mismo símbolo muy seguido?
                        │
5. AI VALIDATOR → ¿La IA lo aprueba? (opcional)
                        │
6. EJECUCIÓN → Solo si pasa TODO
```

### 1️⃣ GENERAR SEÑAL — Estrategia por agente

Cada agente obtiene velas de Yahoo Finance (con rate limiting de 0.35s entre llamadas), calcula indicadores y decide:

| Agente | Condiciones de entrada (ejemplo) |
|--------|--------------------------------|
| **🤵 Conservador** | `SMA(20) cruza por encima de SMA(50)` + `RSI(14) entre 40-70` + `volumen > 1.3× media` + **2 velas de confirmación** |
| **🏃 Agresivo** | `RSI(14) < 25 (sobreventa) o > 75 (sobrecompra)` + `precio toca banda Bollinger 2σ` + `momentum > 0.15%` + `volumen > 1.2× media` |
| **🧐 Pesimista** | `RSI(14) entre 40-60 (zona segura)` + `volumen < 0.8× media (sin pánico)` + `VIX < 25 (sin crisis)` + `fuerza tendencia > 0.2` |
| **🐢 Largo Plazo** | `MACD(12,26,9) mensual > línea de señal` + `precio > SMA(200)` + `RSI semanal(14) < 60 (sin sobrecompra)` |

Si el agente no encuentra señal → **SALTA**, no pasa al siguiente filtro.

### 2️⃣ FILTRO DE HORARIO — ¿Mercado abierto?

```python
from src.utils.time_utils import is_market_open

is_open, reason = is_market_open("IBEX35")
# → (True, "Mercado europeo abierto")         # Entre 8:00-17:00 CET
# → (False, "Mercado USA cerrado 14:30-21:00 CET")
# → (True, "24/7")                             # Crypto
# → (False, "Fin de semana")
```

Si el mercado está cerrado → **SALTA**, no se analiza hasta la próxima vela.  
Cobertura horaria: USA equities, USA sectores, Europa equities, Asia, Forex, Commodities, Crypto, Bonos.

### 3️⃣ FILTRO DE RIESGO — RiskManager

```python
agent.risk.can_trade()
```

Comprueba:

| Condición | Qué hace si se activa |
|-----------|----------------------|
| **Drawdown máximo** superado (ej: agresivo 25%) | 🔴 Para el agente 24h |
| **Pérdida diaria** > 10% del capital | 🔴 No tradea hasta mañana |
| **Máximo de posiciones abiertas** alcanzado (ej: agresivo 3) | 🔴 Espera a que se cierre alguna |
| **Kelly Criterion** | 💰 Calcula tamaño óptimo de posición según historial |

Si `can_trade()` devuelve False → **SALTA**.

### 4️⃣ FILTRO DE COOLDOWN — Evitar sobretrading

Mínimo **1 hora** entre trades del mismo símbolo por el mismo agente.  
Evita que el agresivo compre/venda US100 cada 15 minutos en un mercado lateral.

### 5️⃣ AI VALIDATOR — DeepSeek revisa la señal (opcional)

Si está activo (`config/learning.yaml: ai_validator.enabled: true` y `OPENROUTER_API_KEY` configurada):

```
Agente genera señal → BUY US100 @ 19.820
        │
AI Validator llama a DeepSeek V4 vía OpenRouter
        │
DeepSeek evalúa: precio, RSI, volumen, tendencia, contexto de mercado
        │
Responde: APPROVE o BLOCK + motivo detallado
        │
┌───────┴───────┐
▼               ▼
APROBADO       BLOQUEADO
│               │
Ejecuta trade   Genera log con motivo del bloqueo
```

**Prompt del validador (resumido):**
> "Eres un validador de trades conservador. Si tienes dudas, BLOQUEA.  
> - Si el precio está en soporte/resistencia clave → aprueba  
> - Si hay evento macro pronto (CPI, FOMC) → bloquea  
> - Si la señal contradice la tendencia general → bloquea  
> - Si el volumen es anormalmente bajo → bloquea"

**Coste:** ~$0.001 por validación (DeepSeek V4 Flash via OpenRouter).

### 6️⃣ EJECUCIÓN — Solo si pasa TODO

Si la señal supera los 5 filtros anteriores:

1. **Ejecuta** el trade (simulado en sandbox, real con MT5)
2. **Tesorero** → Si hay ganancia, descuenta el 20% y lo guarda en la hucha protegida
3. **Summary Logger** → Registra el trade completo con todos los indicadores en `data/logs/training/`
4. **Dashboard** → Se actualiza en tiempo real
5. **State persistente** → Se guarda `data/state.json` con balances actualizados

### 🚦 Ejemplos reales del pipeline

**✅ Señal que SÍ se ejecuta:**
```
🏃 Agresivo analiza US100 a las 14:32
  ✅ Mercado USA abierto (14:30-21:00 CET)
  ✅ RSI(14) = 22 → SOBREVENTA
  ✅ Precio tocó banda inferior Bollinger
  ✅ Volumen 1.4× la media → confirma
  ✅ RiskManager: drawdown 8% < 25% límite
  ✅ RiskManager: solo 1 posición abierta de 3 máx
  ✅ AI Validator: "Señal válida, RSI confirma + soporte en 19.800"
  → 🟢 BUY US100 @ 19.820 | SL: 19.520 | TP: 20.220
```

**🚫 Señal que NO se ejecuta:**
```
🏃 Agresivo analiza BTCUSD a las 03:15
  ✅ Crypto: mercado 24/7
  ✅ RSI(14) = 18 → sobreventa
  ❌ VIX = 32 (alta volatilidad general)
  ❌ AI Validator: "VIX alto, mercado con pánico. BLOQUEO."
  → 🚫 BLOQUEADO por IA | Log generado con motivo
```

---

## ⚙️ Sistema de Logs — 5 tipos

Cada acción genera logs con distinto propósito:

### 1. 📊 `data/dashboard_data.json` — Dashboard en tiempo real
Métricas consolidadas, estado de agentes, últimas señales, resúmenes IA, histórico de equity.  
**Consumido por:** Frontend React (shadcn/ui) en `http://localhost:8050`.  
**Se reescribe** cada ciclo del orquestador.

### 2. 💾 `data/state.json` — Persistencia entre reinicios
Balances actuales, total de trades, trades ganados de cada agente.  
**Propósito:** Si el bot se para (cierras terminal, se va la luz), al reiniciar recupera los balances exactos.  
**Se restaura automáticamente** al arrancar el orquestador.

### 3. 📈 `data/logs/performance.json` — Métricas agregadas
Sharpe ratio, profit factor, drawdown máximo, win rate global, profit medio, desviación estándar.  
**Propósito:** Evaluación objetiva del rendimiento del sistema.

### 4. 🎓 `data/logs/training/analysis_YYYYMM.jsonl` — Training logs (formato JSONL)
Una línea por trade/análisis. Cada línea contiene:
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
Últimas 200 entradas del resumen de cada análisis.  
**Propósito:** Visualización en tiempo real en la pestaña 📋 Logs del dashboard.  
*Volátil — se pierde al parar el bot (se recupera del training logs si es necesario).*

---

## 🏖️ Modos de ejecución

### Sandbox (gratis, sin instalar nada, datos reales)
```bash
python run.py
# Yahoo Finance → datos reales del mercado
# Trades simulados, sin dinero real
# Dashboard en http://localhost:8050
```

### Backtest
```bash
python run.py --backtest
# Simula con datos históricos
```

### Real (HFM + MT5)
```bash
# 1. Configurar broker en config/broker.yaml
# 2. Tener MT5 abierto
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
python3 -c "from src.core.sandbox_broker import resolve_symbol; print(resolve_symbol('SAP'))"

# Ver training logs
head -5 data/logs/training/analysis_*.jsonl | python3 -m json.tool
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