# Synthetic User Generation Platform — Frontend

A multi-page Streamlit app that lets users define a product, generate synthetic
personas, run surveys/interviews, view insights, and export a PDF report.

Currently running on **mock data** so you can build and test the full workflow
before your backend + Groq integration is ready.

## Setup

```bash
cd frontend
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

## Project structure

```
frontend/
├── app.py                          # Entry point, redirects to Home
├── pages/                          # One file per page (Streamlit auto-routes these)
│   ├── 0_Home.py
│   ├── 1_Experiment_Workspace.py
│   ├── 2_Persona_Gallery.py
│   ├── 3_Survey_Mode.py
│   ├── 4_Interview_Mode.py
│   ├── 5_Insights_Dashboard.py
│   └── 6_Report_Generator.py
├── components/                     # Reusable UI pieces
│   ├── persona_card.py
│   ├── chat_interface.py
│   ├── survey_grid.py
│   ├── visualizations.py
│   └── report_preview.py
├── services/                       # Business logic + API integration
│   ├── api_client.py               # <-- single switchboard for mock vs real backend
│   ├── mock_data.py                # Fake persona/survey/insight generators
│   ├── data_processor.py
│   └── export_service.py           # PDF generation (reportlab)
├── utils/
│   ├── state_manager.py            # session_state init + helpers
│   ├── validators.py
│   └── constants.py
├── styles/
│   ├── custom.css
│   └── theme.py
├── config.py                       # USE_MOCK_DATA toggle, backend URL, Groq settings
├── requirements.txt
└── .env.example
```

## How the mock → real backend switch works

Every page imports functions from `services/api_client.py` — never from
`mock_data.py` directly. `api_client.py` checks `config.USE_MOCK_DATA`:

- **True** → calls functions in `services/mock_data.py` (fake but realistic data)
- **False** → calls your real backend at `config.BACKEND_BASE_URL` via `requests`

To go live once your backend exists:

1. Build these endpoints on your backend (they already match the spec):
   - `POST /experiments`
   - `POST /personas/generate`
   - `POST /survey/run`
   - `POST /interview/message`
   - `POST /insights/extract`
   - `POST /reports/generate`
2. In `.env`, set `USE_MOCK_DATA=false` and `BACKEND_BASE_URL` to your server.
3. Restart the app. No page or component code needs to change.

Where does Groq fit in? Your **backend** should call the Groq API (persona
generation, survey answers, interview replies, insight extraction) and return
plain JSON to this frontend — that keeps your API key server-side and out of
the browser/Streamlit client. The `GROQ_API_KEY` in `.env` is only there as a
fallback if you ever want the frontend to call Groq directly.

## Known follow-ups

- Swap the DiceBear placeholder avatars in `persona_card.py` for real generated
  images if desired.
- `services/export_service.py` builds a straightforward PDF; feel free to add
  your logo/branding to the reportlab story.
- Add authentication once your backend has it — `utils/state_manager.py`
  already tracks a `user_id`/`session_id` you can wire up.
