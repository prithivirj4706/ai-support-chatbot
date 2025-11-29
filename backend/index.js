/**
 * SmartAssist AI - Multi-Mode Support Engine
 * Modes: Customer Support, Lead Scoring, Spam Detection, Internal Workflows, Analytics
 * Integrations: Zoho CRM, Zoho Desk, WhatsApp, Webhooks
 */

const express = require('express');
const axios = require('axios');
const app = express();
app.use(express.json());

// ============ CONFIG ============
const ZOHO_CRM_TOKEN = process.env.ZOHO_CRM_TOKEN;
const ZOHO_DESK_TOKEN = process.env.ZOHO_DESK_TOKEN;
const OPENAI_KEY = process.env.OPENAI_KEY;
const WHATSAPP_TOKEN = process.env.WHATSAPP_TOKEN;

const MODE_TRIGGERS = {
  SUPPORT: ['help', 'support', 'issue', 'problem', 'faq', 'how to', 'guide'],
  LEAD_SCORING: ['pricing', 'demo', 'buy', 'available', 'features'],
  INTERNAL: ['crm', 'ticket', 'workflow', 'api', 'automation'],
  ANALYTICS: ['dashboard', 'report', 'metrics', 'analytics', 'performance']
};

// ============ MODE DETECTION ============
function detectMode(message) {
  const msg = message.toLowerCase();
  
  if (MODE_TRIGGERS.INTERNAL.some(t => msg.includes(t))) return 'INTERNAL';
  if (MODE_TRIGGERS.LEAD_SCORING.some(t => msg.includes(t))) return 'LEAD_SCORING';
  if (MODE_TRIGGERS.ANALYTICS.some(t => msg.includes(t))) return 'ANALYTICS';
  if (/^[a-z]{10,}$/.test(msg) || msg.length < 3) return 'SPAM';
  return 'SUPPORT';
}

// ============ LEAD SCORING ============
function scoreVisitor(message, metadata) {
  let score = 0;
  const msg = message.toLowerCase();
  
  const hotKeywords = ['buy', 'pricing', 'demo', 'purchase', 'urgent', 'asap'];
  const warmKeywords = ['interested', 'learn more', 'how', 'features', 'cost'];
  
  hotKeywords.forEach(kw => score += msg.includes(kw) ? 30 : 0);
  warmKeywords.forEach(kw => score += msg.includes(kw) ? 15 : 0);
  
  if (metadata.visitCount > 3) score += 20;
  if (metadata.timeSpentMinutes > 5) score += 15;
  
  if (score >= 60) return 'HOT';
  if (score >= 30) return 'WARM';
  return 'COLD';
}

// ============ ZOHO CRM - CREATE LEAD ============
async function createZohoCRMLead(visitorData, leadScore) {
  try {
    const payload = {
      data: [{
        Last_Name: visitorData.name || 'Unknown',
        Email: visitorData.email,
        Phone: visitorData.phone,
        Lead_Source: 'Website Chat',
        Description: visitorData.inquiry,
        Lead_Score: leadScore === 'HOT' ? 100 : leadScore === 'WARM' ? 50 : 20
      }]
    };
    
    const response = await axios.post(
      'https://www.zohoapis.com/crm/v3/Leads',
      payload,
      { headers: { Authorization: `Zoho-oauthtoken ${ZOHO_CRM_TOKEN}` } }
    );
    
    return { success: true, leadId: response.data.data[0].id };
  } catch (error) {
    console.error('CRM Error:', error.message);
    return { success: false, error: error.message };
  }
}

// ============ ZOHO DESK - CREATE TICKET ============
async function createZohoDeskTicket(visitorData, subject, description) {
  try {
    const payload = {
      subject: subject,
      description: description,
      email: visitorData.email,
      priority: description.includes('urgent') ? 'High' : 'Medium',
      status: 'Open'
    };
    
    const response = await axios.post(
      'https://desk.zoho.com/api/v1/tickets',
      payload,
      { headers: { Authorization: `Zoho-oauthtoken ${ZOHO_DESK_TOKEN}` } }
    );
    
    return { success: true, ticketId: response.data.id };
  } catch (error) {
    console.error('Desk Error:', error.message);
    return { success: false, error: error.message };
  }
}

// ============ AI RESPONSE GENERATION (OpenAI) ============
async function generateAIResponse(userMessage, mode, context) {
  try {
    const systemPrompt = `You are SmartAssist AI - a natural, helpful support agent.
    Mode: ${mode}
    Context: ${JSON.stringify(context)}
    
    Rules:
    - Sound like a real person, not a bot
    - Be concise and helpful
    - Never repeat the same phrase
    - Offer next steps or escalation when needed`;
    
    const response = await axios.post(
      'https://api.openai.com/v1/chat/completions',
      {
        model: 'gpt-4',
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userMessage }
        ],
        temperature: 0.8,
        max_tokens: 150
      },
      { headers: { Authorization: `Bearer ${OPENAI_KEY}` } }
    );
    
    return response.data.choices[0].message.content;
  } catch (error) {
    console.error('AI Error:', error.message);
    return 'Let me connect you with our team for better assistance!';
  }
}

// ============ ANALYTICS DASHBOARD DATA ============
function getAnalyticsDashboard() {
  return {
    kpis: {
      total_leads: 1245,
      qualified_leads: 320,
      response_time_avg_minutes: 2.3,
      faq_success_rate: '78%',
      escalation_rate: '12%',
      customer_satisfaction: '4.7/5'
    },
    source_breakdown: {
      website_chat: 450,
      whatsapp: 380,
      email: 220,
      direct: 195
    },
    funnel: {
      visitors: 5000,
      engaged: 1500,
      leads: 320,
      qualified: 280,
      converted: 45
    },
    chart_data: {
      type: 'line',
      labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
      datasets: [{
        label: 'Leads Generated',
        data: [45, 52, 38, 61, 55, 40, 35],
        borderColor: '#00b4d8'
      }]
    }
  };
}

// ============ MAIN WEBHOOK ENDPOINT ============
app.post('/api/chat', async (req, res) => {
  const { message, visitorData, metadata } = req.body;
  
  try {
    // Step 1: Detect Mode
    const mode = detectMode(message);
    console.log(`[MODE] ${mode}`);
    
    // Step 2: Route based on Mode
    let responseData = {};
    
    if (mode === 'SPAM') {
      responseData.message = "Hmm… that doesn't seem like a valid query. Could you clarify?";
      return res.json(responseData);
    }
    
    if (mode === 'LEAD_SCORING') {
      const leadScore = scoreVisitor(message, metadata);
      const crmResult = await createZohoCRMLead(visitorData, leadScore);
      
      responseData = {
        message: `Great! I've connected your interest with our sales team. They'll reach out shortly!`,
        leadScore,
        crmId: crmResult.leadId,
        escalated: true
      };
    }
    
    if (mode === 'INTERNAL') {
      const ticketResult = await createZohoDeskTicket(
        visitorData,
        `Internal: ${message.substring(0, 50)}`,
        message
      );
      
      responseData = {
        message: `Workflow triggered. Ticket #${ticketResult.ticketId} created.`,
        ticketId: ticketResult.ticketId,
        ticketUrl: `https://desk.zoho.com/tickets/${ticketResult.ticketId}`
      };
    }
    
    if (mode === 'ANALYTICS') {
      responseData = {
        message: 'Here\'s your dashboard snapshot:',
        analytics: getAnalyticsDashboard()
      };
    }
    
    if (mode === 'SUPPORT') {
      const aiResponse = await generateAIResponse(message, mode, visitorData);
      responseData = {
        message: aiResponse,
        canEscalate: true,
        escalateLink: '/escalate-to-human'
      };
    }
    
    res.json(responseData);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ============ ESCALATION ENDPOINT ============
app.post('/api/escalate-to-human', async (req, res) => {
  const { visitorData, conversation } = req.body;
  
  const ticket = await createZohoDeskTicket(
    visitorData,
    'Customer Escalation - Needs Human Support',
    `Conversation: ${JSON.stringify(conversation)}`
  );
  
  res.json({
    message: 'You\'ve been connected with our support team!',
    ticketId: ticket.ticketId,
    estimatedWait: '< 2 minutes'
  });
});

// ============ WEBHOOK HEALTH ============
app.get('/api/health', (req, res) => {
  res.json({ status: 'SmartAssist AI is running' });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`🚀 SmartAssist AI running on :${PORT}`));

module.exports = app;
