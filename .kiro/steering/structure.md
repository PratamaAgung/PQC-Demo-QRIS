# Project Structure

```
PQC Demo QRIS/
├── app.py              # Entire backend: Flask routes, RSA logic, QR generation, global state
├── requirements.txt    # Python dependencies
├── templates/
│   ├── base.html       # Shared layout: navbar, all CSS (design tokens + components), shared JS helpers
│   ├── index.html      # Dashboard — attack flow diagram, intro, links to other pages
│   ├── kasir.html      # Kasir (merchant) view — generate keypair, generate QRIS, display QR
│   ├── attacker.html   # Attacker view — intercept, run Shor's crack, forge QRIS, attack toggle
│   └── mbanking.html   # M-Banking (customer) view — scan QRIS, verify, confirm payment
└── static/
    ├── css/            # (currently empty — all CSS lives in base.html)
    └── js/             # (currently empty — all JS lives inline in templates)
```

## Architecture Patterns

### Backend (`app.py`)
- **Single-file backend** — all routes, utilities, and state live in `app.py`
- **Global `state` dict** — shared mutable state simulating cross-entity communication (Bank ↔ Attacker ↔ M-Banking). This is intentional for demo simplicity, not a pattern to replicate in production
- **Global `crack_job` dict** — tracks background thread status for the Shor's factorization worker
- **Background thread** — `_crack_worker()` runs factorization in a daemon thread; frontend polls `/api/crack-status` for progress
- Utility functions (`rsa_sign`, `rsa_verify`, `generate_qr_base64`, `add_log`, etc.) are defined at module level above the routes

### Frontend (templates)
- All templates extend `base.html` using Jinja2 `{% extends %}` / `{% block %}` 
- Page-specific styles go in `{% block extra_style %}`, scripts in `{% block scripts %}`
- Active navbar link is set per-template via `{% block nav_X %}active{% endblock %}`
- Shared JS helpers (`formatRp`, `renderLog`, `escHtml`) are defined in `base.html` and available globally
- Each page manages its own UI state via vanilla JS; no shared JS module system

### API Conventions
- All endpoints: `POST /api/<action>` (most state-mutating calls) or `GET /api/<resource>`
- Request body: JSON via `request.get_json()`
- Response shape: `{ "status": "ok" | "error", ...payload }`
- Logs are appended to `state["attack_log"]` via `add_log(entity, message, level)` and polled by the frontend

## Adding New Features

- **New API endpoint**: Add a `@app.route` function in `app.py`, update `state` if new fields are needed
- **New page**: Create `templates/<name>.html` extending `base.html`, add a Flask route, add a navbar link in `base.html`
- **New CSS component**: Add to the `<style>` block in `base.html` using existing design tokens
- **New JS utility**: Add to the shared `<script>` block in `base.html` if reusable, or inline in the page template
