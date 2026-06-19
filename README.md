# Security Log Analyzer

> **Production-ready cybersecurity SOC platform** for ingesting, analyzing and visualizing
> authentication logs to detect brute-force attacks, suspicious IPs, and unusual access
> patterns — built as a portfolio-grade full-stack project.

![Tech](https://img.shields.io/badge/Stack-React%20%7C%20FastAPI%20%7C%20Pandas%20%7C%20MongoDB-blue?style=flat-square)
![Auth](https://img.shields.io/badge/Auth-JWT%20%2B%20TOTP%202FA-green?style=flat-square)
![Docker](https://img.shields.io/badge/Deploy-Docker%20%7C%20GH%20Actions-purple?style=flat-square)

---

## Features

- **JWT Authentication** (Register / Login / Logout) with bcrypt password hashing
- **Forgot / Reset Password** flow (Resend integration — placeholder logs link to console in dev)
- **TOTP Two-Factor Authentication** with QR code provisioning (Google Authenticator / Authy)
- **Brute-force lockout** (5 failed attempts → 15-minute lockout)
- **Log ingestion** for CSV, JSON, TXT (drag-drop upload, 10 MB cap, schema validation)
- **Pandas-powered analytics engine** detects:
  - Failed login bursts (≥ 5 failures in 10 min per user)
  - Brute-force attacks (≥ 20 failures from same IP)
  - Suspicious IP activity (top sources ranked)
  - Unusual login hours (00:00–05:00)
  - Risk scoring 0–100 → Low / Medium / High / Critical
- **SOC Dashboard** with KPI cards, attack timeline, success/failure bars, top suspicious IPs, event distribution donut
- **Live alerts feed** with severity badges and acknowledgement workflow
- **Incident Investigation** page: per-IP timeline, geolocation, related events, related alerts
- **MITRE ATT&CK matrix** with heat-mapped technique hits
- **PDF Threat Reports** (executive summary, KPIs, top threats, recommendations) via ReportLab
- **CSV exports** for logs and alerts
- **Search & filtering** by date range, event type, status, IP, username
- **IP Geolocation** lookup via `ip-api.com` (free tier, no key required)

---

## Architecture

```
            +-----------+         +---------------+
            |  React    |  HTTPS  |   FastAPI     |
            | (Tailwind |<------->|   Backend     |
            |  Recharts)|         |   + Pandas    |
            +-----------+         +-------+-------+
                                          |
                              +-----------+-----------+
                              |                       |
                       +------v-----+         +-------v---------+
                       |  MongoDB   |         | Python Analytics |
                       |   (Motor)  |         |  (Flask · sep    |
                       +------------+         |   Docker service)|
                                              +------------------+
```

**Running version** (this repo): FastAPI backend with pandas embedded.
**Docker deliverable** also ships a standalone Python analytics microservice that a Node.js backend could call.

---

## Quick Start (local)

### 1. Backend
```bash
cd backend
pip install -r requirements.txt
# .env keys (see backend/.env)
uvicorn server:app --reload --port 8001
```

### 2. Frontend
```bash
cd frontend
yarn install
yarn start    # http://localhost:3000
```

### 3. Default Admin
- **Email**: `admin@soc.com`
- **Password**: `Admin@123`

> Use the **"Inject Demo Data"** button on the dashboard to populate a realistic threat dataset.

---

## Docker

```bash
docker-compose up --build
```

Services:
| Service     | Port  | Description                                  |
|-------------|-------|----------------------------------------------|
| frontend    | 3000  | Nginx serving React build, `/api` proxied    |
| backend     | 8001  | FastAPI + embedded analytics                 |
| analytics   | 9000  | Standalone Pandas Flask service (deliverable)|
| mongo       | 27017 | MongoDB 7                                    |

Environment variables (override in a `.env` next to `docker-compose.yml`):
```
JWT_SECRET=<64-char-hex>
ADMIN_EMAIL=admin@soc.com
ADMIN_PASSWORD=Admin@123
RESEND_API_KEY=re_xxx          # optional — enables real password-reset emails
SENDER_EMAIL=onboarding@resend.dev
FRONTEND_URL=http://localhost:3000
```

---

## CI/CD (GitHub Actions)

`.github/workflows/ci.yml` runs on every push and pull request:

- Backend lint + tests
- Python analytics tests
- Frontend build
- Docker Compose build

---

## API Reference

Base URL: `/api`

### Auth (`/api/auth`)
| Method | Path                | Body                                  | Description                       |
|--------|---------------------|---------------------------------------|-----------------------------------|
| POST   | /register           | `{email,password,name}`               | Create account, sets cookies      |
| POST   | /login              | `{email,password,totp_code?}`         | Sign in, supports 2FA             |
| POST   | /logout             | —                                     | Clear auth cookies                |
| GET    | /me                 | —                                     | Current user                      |
| POST   | /refresh            | —                                     | Rotate access token               |
| POST   | /forgot-password    | `{email}`                             | Issue reset token (Resend/log)    |
| POST   | /reset-password     | `{token,new_password}`                | Set new password                  |
| POST   | /2fa/setup          | —                                     | Generate TOTP secret + QR         |
| POST   | /2fa/verify         | `{code}`                              | Confirm and enable 2FA            |
| POST   | /2fa/disable        | `{code}`                              | Disable 2FA                       |

### Logs (`/api/logs`)
| Method | Path                | Description                                   |
|--------|---------------------|-----------------------------------------------|
| POST   | /upload             | Multipart upload (CSV/JSON/TXT)               |
| GET    | ?filters            | Paginated log listing                         |
| GET    | /by-ip/{ip}         | All logs for an IP + geo info                 |
| DELETE | /                   | Clear all logs and alerts for current user    |
| POST   | /seed-demo          | Insert realistic demo dataset                 |

### Analytics (`/api/analytics`)
| GET | /kpi        | KPI card data                                                  |
| GET | /dashboard  | Full dashboard payload (KPIs, timeseries, charts, suspects)    |
| GET | /run        | Run analysis and persist a report                              |

### Alerts (`/api/alerts`)
| GET  | ?severity                  | List alerts                              |
| POST | /{alert_id}/acknowledge    | Acknowledge alert                        |

### Reports (`/api/reports`)
| GET | /                  | Past analysis reports     |
| GET | /pdf               | Download PDF threat report|
| GET | /csv/logs          | Download logs as CSV      |
| GET | /csv/alerts        | Download alerts as CSV    |

### Other
| GET  | /api/mitre/matrix     | MITRE ATT&CK matrix + hit counts          |
| GET  | /api/geo/{ip}         | Geolocation lookup                        |
| POST | /api/geo/batch        | Batch geo lookup (max 50 IPs)             |

---

## Screenshots

> See the **/screenshots** folder (add your screenshots after running locally).

- `dashboard.png` — SOC control-room dashboard
- `investigation.png` — Per-IP forensic timeline
- `mitre.png` — ATT&CK matrix heat-map
- `alerts.png` — Live alerts feed
- `report.png` — PDF report sample

---

## Tech Stack

| Layer      | Tech                                         |
|------------|----------------------------------------------|
| Frontend   | React 19, Tailwind CSS, Recharts, Phosphor Icons, shadcn/ui, sonner |
| Backend    | FastAPI, Motor (async MongoDB), Pandas, PyJWT, bcrypt, pyotp, qrcode, ReportLab |
| Database   | MongoDB 7                                    |
| Analytics  | Pandas (embedded + standalone Flask service) |
| Auth       | JWT (httpOnly cookies) + TOTP 2FA + bcrypt   |
| Deploy     | Docker Compose, GitHub Actions               |

---

## Security Notes

- Passwords hashed with bcrypt (cost factor 12)
- JWT secrets sourced from env; tokens stored in `httpOnly` cookies (XSS-safe)
- Brute-force protection (per IP+email rolling window with lockout)
- Password reset tokens are single-use and expire in 1 hour
- MongoDB TTL index auto-purges expired reset tokens
- TOTP secrets stored server-side and only revealed once during QR provisioning
- CORS configurable per environment

---

## License

MIT
