# Kiro AI Support Chatbot

**Natural-language customer support + lead capture + internal CRM automation**

## What This Does

✅ Website live chat (Zoho SalesIQ)
✅ Auto-lead scoring & qualification
✅ Smart internal routing (Sales/Billing/Support/Technical)
✅ FAQ auto-answers with human tone
✅ Zoho CRM + Desk integration
✅ Spam/bot detection
✅ Real-time analytics dashboard
✅ WhatsApp fallback suggestions

## Project Structure

```
kiro-ai-support-chatbot/
├── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── SETUP.md
│   └── API_REFERENCE.md
├── zobot-scripts/
│   ├── lead_capture.ds          # Zoho Deluge - Lead collection
│   ├── intent_detection.ds       # Intent → Team routing
│   ├── faq_autoanswer.ds         # FAQ engine
│   └── spam_detector.ds          # Bot behavior detection
├── backend/
│   ├── python/
│   │   ├── crm_lead.py           # Zoho CRM API helper
│   │   ├── desk_ticket.py        # Zoho Desk API helper
│   │   ├── lead_scoring.py       # Lead qualification logic
│   │   └── main.py               # FastAPI app
│   ├── nodejs/
│   │   ├── crm-lead.js
│   │   ├── desk-ticket.js
│   │   └── app.js                # Express app
│   └── .env.example
├── analytics/
│   ├── schema.sql                # Database models
│   ├── queries.sql               # Analytics queries
│   └── dashboard.json            # Dashboard config
├── webhooks/
│   ├── zobot_lead_webhook.json
│   └── zoho_crm_webhook.json
└── integrations/
    ├── whatsapp_fallback.py
    └── sms_alert.py
```

## Quick Start

### 1. Zobot Setup
- Import `zobot-scripts/` files to SalesIQ bot builder
- Set webhook URL to your backend
- Connect Zoho CRM API credentials

### 2. Backend Setup
```bash
cd backend/python
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Zoho credentials
python main.py
```

### 3. Analytics DB
```bash
psql -U username -d chatbot_analytics < analytics/schema.sql
```

## Data Flow

```
[Visitor on Website]
        ↓
  [Zobot triggers]
        ↓
  [Collect: name, email, phone, requirement, urgency]
        ↓
  [Build lead JSON + lead_score]
        ↓
  [Detect intent → route to team]
        ↓
  [POST to backend webhook]
        ↓
  [Create Zoho CRM Lead]
  [Create Zoho Desk Ticket if needed]
  [Store metrics to analytics DB]
        ↓
  [Internal team gets notification]
```

## Example: How a Lead Flows

**Visitor:** "Hi, I need WhatsApp support bot for my e-commerce store"

**Zobot:**
1. Detects intent: "Sales" (keyword: "need")
2. Asks: "What's your name?", "Email?", "Phone?", "What's your business?"
3. Builds lead JSON:
```json
{
  "lead": {
    "name": "Prithivi",
    "email": "prithivi@example.com",
    "phone": "+91-9876543210",
    "business_type": "E-commerce",
    "requirement": "WhatsApp support bot",
    "urgency": "High",
    "pages_visited": ["/pricing", "/features/whatsapp"],
    "time_on_site": 420
  }
}
```

4. Scores lead: 78/100 (hot lead)
5. Routes to Sales team
6. Calls backend webhook

**Backend:**
- Creates Lead in Zoho CRM
- Creates Task in CRM for Sales agent
- Stores interaction in analytics DB
- Sends Slack notification to sales channel

## Key Features

### Lead Scoring Algorithm
```
Score = Base(50) + Pages_Bonus + Urgency_Bonus + Engagement_Bonus
- Base: 50 points
- Pages visited (5+ pages): +15
- Time on site (5+ min): +10
- Urgency high: +10
- Urgency medium: +5
- Rapid repeat messages: -20 (spam detector)

Qualification:
- 75+: Hot (contact within 2 hours)
- 50-74: Warm (contact within 24 hours)
- <50: Cold
```

### Intent Detection Keywords
- **Sales:** need, pricing, quote, demo, features, interested
- **Billing:** invoice, payment, refund, charge, subscription
- **Support:** error, bug, not working, issue, problem, help
- **Technical:** integration, API, setup, deploy, crash
- **FAQ:** how, where, what, can I, why

### Spam Detection Rules
- Message length < 3 chars
- Repeated same message 3+ times
- Messages sent < 2 sec apart (5+ times)
- All caps + special chars (> 50%)
- Unknown sender IP seen 100+ times

## Environment Variables

```env
# Zoho CRM
ZOHO_CLIENT_ID=xxxx
ZOHO_CLIENT_SECRET=xxxx
ZOHO_REFRESH_TOKEN=xxxx
ZOHO_CRM_URL=https://www.zohoapis.in

# Zoho Desk
ZOHO_DESK_ORG_ID=xxxx
ZOHO_DESK_AUTH_TOKEN=xxxx
ZOHO_DESK_URL=https://desk.zoho.in

# Database
DB_HOST=localhost
DB_USER=chatbot_user
DB_PASSWORD=xxxx
DB_NAME=chatbot_analytics

# Webhook
WEBHOOK_SECRET=xxxx
BACKEND_URL=https://yourdomain.com/webhook

# Integrations
WHATSAPP_FALLBACK_NUMBER=+91-9876543210
SLACK_WEBHOOK_URL=https://hooks.slack.com/xxx
```

## API Endpoints

### POST /webhook/zobot
Receive lead from Zobot, create CRM lead + ticket

**Payload:**
```json
{
  "lead": {...},
  "routing": {
    "team": "Sales",
    "priority": "High",
    "context": "..."
  },
  "channel": "Website Chat"
}
```

### GET /analytics/leads?days=30
Fetch lead count, qualified count, source breakdown

### GET /analytics/ticket-trends?team=Sales
Fetch ticket escalation trends per team

## Testing

```bash
# Run backend tests
cd backend/python
pytest tests/ -v

# Test Zobot with sample message
curl -X POST http://localhost:8000/webhook/zobot \
  -H "Content-Type: application/json" \
  -d @tests/sample_lead.json
```

## Deployment

### Deploy Backend
```bash
# Docker
docker build -t kiro-chatbot .
docker run -p 8000:8000 --env-file .env kiro-chatbot

# Or Heroku
git push heroku main
```

### Deploy Zobot
1. Export scripts from local → SalesIQ
2. Test with sample visitor
3. Go live

## Monitoring

- **SalesIQ Analytics:** Visit Zoho SalesIQ dashboard for chat metrics
- **Backend Logs:** `tail -f logs/app.log`
- **Database:** Run SQL queries in `analytics/queries.sql`
- **Slack Alerts:** Set up integration for ticket escalations

## Common Issues

**Q: Lead not showing in CRM?**
A: Check webhook logs. Verify Zoho API credentials in .env. Check CORS if frontend is different domain.

**Q: Desk ticket creation failing?**
A: Ensure department ID is correct. Check if contact already exists in Desk (may need to use existing contact ID).

**Q: Spam detector too aggressive?**
A: Adjust thresholds in `backend/python/spam_detector.py`

## Contributing

1. Create feature branch: `git checkout -b feature/xyz`
2. Make changes
3. Commit: `git commit -m "Add: xyz feature"`
4. Push: `git push origin feature/xyz`
5. Open PR

## License

MIT

---

**Need help?** Check `/docs/` folder or open an issue.
