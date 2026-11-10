# AGRI-TECH: API Keys & External Credentials Guide

This guide details all environment variables in AGRI-TECH, what each integration accomplishes, where to procure credentials, and how the application behaves when keys are absent.

---

## 1. Core Security & System

| Variable | Description | Where to Get | Default / Fallback Without Key |
|---|---|---|---|
| `SECRET_KEY` | Signs and validates JWT tokens and salted OTP hashes | Generate via `openssl rand -hex 32` | Uses development default string |
| `DATABASE_URL` | SQLite database URI | Standard filesystem path | `sqlite:///./agritech.db` |
| `OTP_EXPIRY_MINUTES` | OTP expiration window in minutes | Numeric value | `5` |
| `ACCESS_TOKEN_EXPIRE_DAYS` | User JWT session lifetime | Numeric value | `7` |

---

## 2. Item 1: Real OTP Providers

| Variable | Description | Where to Get | Fallback Behavior |
|---|---|---|---|
| `OTP_PROVIDER` | `mock`, `twilio`, or `msg91` | Config choice | Defaults to `mock`. Prints `[MOCK OTP]` in terminal. |
| `TWILIO_ACCOUNT_SID` | Twilio Account identifier | [twilio.com/console](https://www.twilio.com/console) | Falls back to console log print |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token | [twilio.com/console](https://www.twilio.com/console) | Falls back to console log print |
| `TWILIO_FROM_NUMBER` | Twilio SMS sender phone | [twilio.com/console](https://www.twilio.com/console) | Falls back to console log print |
| `MSG91_AUTH_KEY` | MSG91 Indian SMS Gateway Key | [msg91.com](https://msg91.com) | Falls back to console log print |
| `MSG91_SENDER_ID` | 6-character DLT registered Sender ID | MSG91 DLT Portal | Defaults to `AGRITC` |
| `MSG91_TEMPLATE_ID` | DLT Approved OTP Template ID | MSG91 Dashboard | Required for live Indian SMS |

---

## 3. Item 2: Weather & Agricultural Meteorology

| Variable | Description | Where to Get | Fallback Behavior |
|---|---|---|---|
| `DEBUG_MOCK` | When set to `true`, forces synthetic weather profiles | Development flag | Defaults to `false`. Uses live Open-Meteo API -> fresh cache -> stale cache. |

---

## 4. Item 3 & 6: Claude AI (Anthropic Vision & Chatbot)

| Variable | Description | Where to Get | Fallback Behavior |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Enables Claude 3.5 Sonnet / Haiku for vision OCR and conversational assistant | [console.anthropic.com](https://console.anthropic.com) | Chatbot switches to CIB&RC verified rule-based expert engine with **"Basic mode (AI offline)"** badge. Soil card OCR switches to simulated extractor for farmer confirmation. |
| `ANTHROPIC_MODEL` | Anthropic model identifier | Anthropic docs | Defaults to `claude-3-5-sonnet-20241022` |

---

## 5. Item 4: SoilGrids v2 REST API (ISRIC)

- **No key required**: Public scientific API provided by ISRIC Global Soil Information.
- **Behavior**: Uses live REST queries with exponential backoff on HTTP 429 rate limits, cached in SQLite for 30 days. Fallback to regional Deccan Vertisol profile when network is down. Always displays **"ESTIMATE, not a lab test."**

---

## 6. Item 7: Mandi Prices (data.gov.in Agmarknet)

| Variable | Description | Where to Get | Fallback Behavior |
|---|---|---|---|
| `DATA_GOV_API_KEY` | Open Government Data (OGD) Platform India API Key | [data.gov.in](https://data.gov.in) | Falls back to SQLite cached records with last arrival date, or static 8-APMC Maharashtra benchmark dataset (labeled MOCK). |
| `AGMARKNET_RESOURCE_ID` | Data.gov.in Daily Mandi Price Resource ID | OGD Agmarknet dataset | Defaults to `9ef84268-d588-465a-a308-a864a43d0070` |

---

## 7. Item 9: Razorpay Payment Gateway (Test Mode)

| Variable | Description | Where to Get | Fallback Behavior |
|---|---|---|---|
| `RAZORPAY_KEY_ID` | Razorpay Merchant Test Key ID | [dashboard.razorpay.com](https://dashboard.razorpay.com) | Creates mock digital order records labeled **"TEST MODE, no real money"**. |
| `RAZORPAY_KEY_SECRET` | Razorpay Test Key Secret for signature verification | Razorpay Dashboard | In test mode, simulates signature check. |

