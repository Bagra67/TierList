English | [Français](emails.fr.md)

# Emails

The backend sends transactional emails (email address verification, password reset) over **SMTP**. The provider is only a configuration: changing it does not change the code.

## 1. How it works

| Piece              | Where                                | Role                                                                                           |
| ------------------ | ------------------------------------ | ---------------------------------------------------------------------------------------------- |
| `Email`            | `backend/app/services/email.py`      | One email: recipient, subject, text version and HTML version.                                  |
| `EmailSender`      | `backend/app/services/email.py`      | Sends an `Email` with `smtplib` (standard library), with STARTTLS and sign-in when configured. |
| `get_email_sender` | `backend/app/api/dependencies.py`    | Injects the sender into the routes; the tests replace it with a fake that keeps the emails.    |
| SMTP settings      | `backend/app/core/config.py`, `.env` | `SMTP_*`, `EMAIL_FROM`, `FRONTEND_BASE_URL` (see below).                                       |

- **Sent after the response** (FastAPI `BackgroundTasks`): the request does not wait for the SMTP server, and the response time does not reveal whether an email was sent.
- **A failure is logged, never raised**: nobody could handle it once the response is gone, and the user can ask for the email again. Only the error type is logged, never the address.
- **Without `SMTP_HOST`**, no email is sent: the sending is only logged as a warning. The application keeps working.
- **Emails are the only user-facing text produced by the backend.** They are written in French and English, in the language sent by the frontend. Everything else follows the usual rule: error codes translated by the frontend ([i18n guide](i18n.md)).

## 2. In development: Mailpit

[Mailpit](https://mailpit.axllent.org/) (`compose.yaml`) receives the emails **without ever delivering them**: you can send to any address safely.

- It starts with the database: `docker compose up -d --wait` (or `dev.ps1` / `dev.sh`).
- Read the emails at **http://localhost:8025**.
- `backend/.env.example` already points to it: `SMTP_HOST=127.0.0.1`, `SMTP_PORT=1025`, `SMTP_STARTTLS=false`.

## 3. Settings

| Variable               | Purpose                                                                  | Default                         |
| ---------------------- | ------------------------------------------------------------------------ | ------------------------------- |
| `SMTP_HOST`            | SMTP server; without it, no email is sent                                | — (optional)                    |
| `SMTP_PORT`            | Port                                                                     | `587`                           |
| `SMTP_USERNAME`        | Sign-in of the SMTP provider                                             | — (optional)                    |
| `SMTP_PASSWORD`        | Password or API key of the SMTP provider                                 | — (optional)                    |
| `SMTP_STARTTLS`        | Encrypts the connection with STARTTLS; `false` only for Mailpit, locally | `true`                          |
| `SMTP_TIMEOUT_SECONDS` | Timeout of the exchanges with the SMTP server                            | `10`                            |
| `EMAIL_FROM`           | Sender, e.g. `TierList <no-reply@example.com>`                           | `TierList <no-reply@localhost>` |
| `FRONTEND_BASE_URL`    | Frontend address as seen by the user, base of the links sent by email    | `http://localhost:5173`         |

## 4. In production

1. **Choose a provider** that offers SMTP (Brevo, Resend, Postmark, Amazon SES, Mailgun…) and create SMTP credentials (often an API key used as password).
2. **Authorize your domain** at the provider: SPF, DKIM and DMARC DNS records. Without them, emails end up in spam or are refused.
3. Set `SMTP_HOST`, `SMTP_PORT` (usually `587`), `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM` (an address of the authorized domain) and `FRONTEND_BASE_URL` (the HTTPS address of the site). Keep `SMTP_STARTTLS=true`.

Port 465 (implicit TLS, without STARTTLS) is not supported: every provider above also offers 587.
