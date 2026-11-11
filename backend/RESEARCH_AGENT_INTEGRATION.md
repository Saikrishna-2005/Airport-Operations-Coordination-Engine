# Research Agent integration

## What changed
- The standalone Research Agent package is installed under `app/research_agent/`.
- Its internal imports use `app.research_agent.*` to avoid colliding with the main backend's `app` package.
- `POST /api/research/execute` exposes direct Research Agent execution.
- The existing airport LangGraph workflow now runs the Research Agent after operational rule evaluation and before the Planning Agent.
- Research evidence is passed into the Planning Agent as `operational_information.research_result`.

## Run
From the `backend` directory, install the backend requirements and start the existing application:

```bash
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Direct API test
`POST http://127.0.0.1:8000/api/research/execute`

```json
{
  "airport_code": "DEL",
  "disruption_description": "Weather disruption due to fog and low visibility",
  "affected_flights": ["AIC123"],
  "research_requirements": [
    "current weather conditions, wind and visibility",
    "flight aircraft state and status"
  ],
  "data_mode": "synthetic"
}
```

## Configuration
Copy the variables in `.env.research-agent.example` into `backend/.env` as needed. Keep `DATA_MODE=synthetic` for a no-credential smoke test. Set `GOOGLE_API_KEY` only if Gemini synthesis is desired. OpenSky live mode requires its client credentials. Never commit `.env`.

## Safety
Research output is advisory evidence only. It does not issue ATC clearances, approve takeoff/landing, allocate runway slots, or control aircraft. Existing rule-engine and human-approval behaviour remains authoritative.

## Validation
The integration was statically compiled with Python. Live provider execution and full integration tests require installing dependencies and running the backend in the project's own environment.
