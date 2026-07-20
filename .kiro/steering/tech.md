# Tech Stack

## Backend

- **Python 3** with **Flask** (web framework + REST API)
- **sympy** — prime number generation (`sympy.randprime`) and math utilities
- **cryptography** — cryptographic primitives (installed but RSA logic is hand-rolled for demo clarity)
- **qrcode[pil]** + **Pillow** — QR code generation, returned as base64-encoded PNG
- **threading** — background worker for the crack job (non-blocking Shor's simulation)

## Frontend

- **Vanilla HTML/CSS/JavaScript** — no frontend framework
- **Jinja2** templates (Flask's built-in templating)
- All CSS is defined inline in `base.html` using CSS custom properties (design tokens)
- No build step, no bundler — static files in `static/css` and `static/js`
- Frontend polling pattern: JS calls `/api/crack-status` repeatedly to track background job progress

## API Style

- JSON REST API via Flask route decorators
- All API endpoints are prefixed with `/api/`
- Shared mutable global `state` dict in `app.py` — simulates cross-entity shared state (intentional for demo simplicity)
- Responses always include a `"status"` field (`"ok"` or `"error"`)

## Common Commands

```bash
# Install dependencies
pip3 install flask qrcode Pillow sympy cryptography

# Or install from requirements.txt
pip3 install -r requirements.txt

# Run the development server (port 5050)
python3 app.py
```

## URLs

| Page       | URL                          |
|------------|------------------------------|
| Dashboard  | http://localhost:5050/       |
| Kasir      | http://localhost:5050/kasir  |
| Attacker   | http://localhost:5050/attacker |
| M-Banking  | http://localhost:5050/mbanking |

## Design Tokens (CSS)

Defined as CSS variables in `base.html` `:root`:
- `--mandiri-navy: #003F7F` — primary brand color
- `--mandiri-blue: #0066CC`
- `--mandiri-gold: #F5A623`
- `--danger-red: #D93025`
- `--success-green: #1A7F4E`
- `--font-main: 'Inter', sans-serif`
