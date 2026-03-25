# Situational AI

**A health coach that only activates when you need it — and doesn't leave you alone until you hit your goal.**

Set a threshold (e.g., body weight > 170 lbs). Cross it, and an AI coach wakes up and starts messaging you with real, actionable coaching. It won't stop until you're back on track.

## Zero Server Costs

This runs **100% on your machine** using **your own API key**. No servers, no subscriptions, no middleman. You bring your own AI credits (Anthropic or OpenAI) and everything stays local.

## How It Works

1. **Set a threshold** — "If my weight goes above 170 lbs, activate the coach"
2. **Log your data** — Import from Apple Health or log manually
3. **Cross the line** — The AI coach wakes up and starts coaching you
4. **Get nagged** — The coach checks in on a schedule, gives actionable advice, and won't leave you alone
5. **Hit your goal** — The coach celebrates and goes back to sleep

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/monad-droid/situational-ai.git
cd situational-ai
pip install -e .

# 2. Set up your API key (you only need ONE)
cp .env.example .env
# Edit .env and add your Anthropic or OpenAI key

# 3. Log your weight
situational-ai log body_mass 172 --unit lb

# 4. The coach activates immediately if you're over threshold!
# Or start the daemon to monitor continuously:
situational-ai start
```

## Commands

| Command | Description |
|---------|-------------|
| `situational-ai start` | Start the coach daemon (monitors + nags on schedule) |
| `situational-ai log <metric> <value>` | Log a health metric manually |
| `situational-ai import-health <file>` | Import Apple Health XML export |
| `situational-ai status` | Show all thresholds and their current state |
| `situational-ai chat` | Chat with an active coach interactively |
| `situational-ai history <metric>` | Show recent history for a metric |
| `situational-ai add-threshold` | Add a new threshold |

## Apple Health Import

Export your data from the Apple Health app:
1. Open Health app on iPhone
2. Tap your profile picture
3. Tap "Export All Health Data"
4. Transfer the `export.xml` file to your machine
5. Run: `situational-ai import-health /path/to/export.xml`

Supported metrics: body weight, heart rate, steps, blood pressure, body fat %, calories, blood glucose.

## Configuration

**Thresholds** are stored in `data/config.json`. You can edit directly or use the CLI:

```bash
# Add a threshold: activate coach if weight goes above 170 lb, goal is 165 lb
situational-ai add-threshold \
  --id weight_upper \
  --metric body_mass \
  --direction above \
  --value 170 \
  --goal 165 \
  --unit lb
```

**Environment variables** (in `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Your Anthropic API key |
| `OPENAI_API_KEY` | — | Your OpenAI API key |
| `CHECK_INTERVAL_MINUTES` | 60 | How often the daemon checks thresholds |
| `COACH_INTENSITY` | 7 | How aggressive the coach is (1-10) |

## Coach Intensity Scale

| Level | Style |
|-------|-------|
| 1-2 | Gentle, encouraging |
| 3-4 | Friendly but firm |
| 5-6 | Direct, no-nonsense |
| 7-8 | Relentless, drill sergeant energy |
| 9-10 | Maximum accountability — will not let you breathe |

## Architecture

```
Your Machine (zero server costs)
├── CLI Interface (click + rich)
├── Health Data Layer
│   ├── Apple Health XML parser
│   ├── Manual entry
│   └── SQLite storage (local)
├── Threshold Engine
│   ├── Evaluates metrics vs thresholds
│   └── Tracks activation state
├── AI Coach
│   ├── Uses YOUR Anthropic/OpenAI key
│   ├── Context-aware (knows your data + trends)
│   └── Persistent conversation history
└── Notification System
    ├── Terminal (rich panels)
    ├── System notifications (macOS/Linux)
    └── Sound alerts
```

## Why Local?

- **Your data stays on your machine** — health data never leaves your computer
- **Your API key, your costs** — pay only for the AI calls you make
- **No accounts, no servers** — clone, configure, run
- **Full control** — customize thresholds, coach persona, intensity, everything

## License

MIT
