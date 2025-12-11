# 🚀 ACTIVATION GUIDE: VC-Quality Concept Cards

## Current Status: ✅ CODE READY, ⚠️ API KEY NEEDED

Your Elevare platform is **fully upgraded** with VC-analyst-grade AI prompts. The only missing piece is a valid Groq API key.

---

## 🎯 What You Get With the API Key

### Before (Current - Template Mode):
```json
{
  "title": "VoiceBridge is a real",
  "one_line": "VoiceBridge is a real helps neurodivergent professionals...",
  "differentiation": "Speed (decisions in seconds); Focused on SaaS",
  "business_model": "SaaS: Free trial • Pro ($15–$29/mo)"
}
```

### After (With API Key - LLM Mode):
```json
{
  "title": "VoiceBridge",
  "one_line": "Real-time AI that transforms hesitant speech into clear, confident, fluent audio.",
  "problem_summary": "Neurodivergent professionals lose promotions because interviewers mistake hesitation for incompetence. Their brilliant ideas get silenced by delivery friction.",
  "differentiation": "vs Grammarly: We fix audio, not text. vs Standard TTS: Preserves emotional intonation and vocal identity.",
  "business_model": "Freemium B2C ($20/mo Pro tier) + B2B enterprise licensing for inclusive workplaces."
}
```

---

## 📋 Quick Setup (2 Minutes)

### Option 1: Interactive Setup
```bash
bash setup_groq_key.sh
```
This will:
1. Prompt you for your API key
2. Update `.env` automatically
3. Restart the server
4. Run a test

### Option 2: Manual Setup
```bash
# 1. Get your free key from https://console.groq.com/keys
# 2. Edit .env file
nano .env

# 3. Replace this line:
GROQ_API_KEY=your_groq_api_key_here

# 4. With your real key:
GROQ_API_KEY=gsk_abc123xyz...

# 5. Restart server
bash start.sh
```

---

## 🧪 Testing

After setting up the key, test immediately:

```bash
# Test with VoiceBridge example
python3 test_refine.py

# Or use the intake page
open http://localhost:8000/intake
```

You should see:
- ✅ Specific target users (not "people")
- ✅ Empathetic problem statements
- ✅ Domain-coherent business models
- ✅ Detailed differentiation vs competitors
- ✅ Punchy elevator pitches under 15 words

---

## 🔍 How to Get a Groq API Key (FREE)

1. Visit: **https://console.groq.com/keys**
2. Sign in with Google or GitHub
3. Click **"Create API Key"**
4. Copy the key (starts with `gsk_`)
5. Paste it when running `bash setup_groq_key.sh`

**Note**: The free tier includes:
- 30 requests/minute
- 14,400 requests/day
- More than enough for development and testing

---

## 🛠️ Troubleshooting

### "Invalid API Key" Error
```bash
# Check what key is currently loaded
source .env && echo $GROQ_API_KEY

# If it shows "your_groq_api_key_here", run:
bash setup_groq_key.sh
```

### "Falling back to heuristics" in logs
This means the LLM call failed. Check:
```bash
# View recent errors
tail -50 server.log | grep "concept card"

# Common causes:
# - API key not set
# - Rate limit exceeded (wait 1 minute)
# - Network issue (check internet)
```

### Server not restarting
```bash
# Force kill and restart
killall python3
bash start.sh
```

---

## 📊 Verification Checklist

After setup, verify these outputs in the concept card:

- [ ] **Title**: Actual brand name (not "A platform" or "Draft concept")
- [ ] **One-line**: Under 15 words, punchy format
- [ ] **Problem**: Paints vivid picture with empathy (not "People face challenges")
- [ ] **Target Users**: Specific segments (not "Early adopters" or "Users")
- [ ] **Differentiation**: "vs X: We do Y" format with named competitors
- [ ] **Business Model**: Aligned with domain (SaaS → tiers, Fintech → take-rates)
- [ ] **Key Features**: Specific technical details (not generic "Analytics dashboard")

---

## 📚 Files Modified

All changes are already in place:

1. ✅ `api/validation.py` - Enhanced prompts (lines 30-80, 365-460)
2. ✅ `services/agent_tools.py` - Fixed API URL
3. ✅ `services/agent_workflow.py` - Fixed fallback URL
4. ✅ `test_refine.py` - VoiceBridge test example

**You just need the API key to activate everything!**

---

## 🎬 Next Steps

1. **Get API Key**: https://console.groq.com/keys (30 seconds)
2. **Run Setup**: `bash setup_groq_key.sh`
3. **Test Output**: `python3 test_refine.py`
4. **Compare Quality**: Check against the VoiceBridge example in `CONCEPT_CARD_UPGRADE.md`

Once activated, **every idea submitted through your intake page** will get VC-quality analysis automatically! 🚀
