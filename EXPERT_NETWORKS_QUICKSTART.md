# Expert Networks Module - Quick Start Guide

## 🚀 Quick Setup (5 minutes)

### 1. Install Dependencies
```bash
# Backend
cd backend
pip install databases aiosqlite

# Database setup
python create_database.py
```

### 2. Configure OpenAI Key
Edit `backend/settings.json`:
```json
{
  "openai_api_key": "sk-your-openai-key-here"
}
```

### 3. Start Application
```bash
# Terminal 1 - Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### 4. Access Expert Networks
Open browser to `http://localhost:5173` → Click "Expert Networks" in sidebar

## 🧪 Quick Test (2 minutes)

1. **Create Project**
   - Click "New Project"
   - Name: "Test Project"
   - Hypothesis: "Understanding retail logistics"
   - Click "Create"

2. **Ingest Test Email**
   - Click "Ingest Email"
   - Paste from: `~/Downloads/expertNetworks/seed/emails/alphasights-batch1.txt`
   - Click "Extract Experts"
   - Review 3 extracted experts
   - Click "Commit Experts"

3. **Use Tracker**
   - See experts in table
   - Edit names, status, dates inline
   - Export to CSV

## 📁 Test Email Locations

Sample emails available at:
```
~/Downloads/expertNetworks/seed/emails/
├── alphasights-batch1.txt   # 3 healthcare logistics experts
├── alphasights-batch2.txt   # Additional experts
├── guidepoint-batch1.txt    # Guidepoint format
└── glg-batch1.txt           # GLG format
```

## ✅ What Works

- ✅ AI-powered expert extraction from emails
- ✅ Automatic deduplication detection
- ✅ Interactive tracker table with inline editing
- ✅ Status management (recommended → scheduled → completed)
- ✅ Conflict tracking
- ✅ CSV export
- ✅ Search and filters
- ✅ Multi-project support

## 🔧 Troubleshooting

**"OpenAI API key not set"**
→ Add key to `backend/settings.json`

**"Database not found"**
→ Run `python backend/create_database.py`

**Frontend can't connect**
→ Check backend is running on port 8000

## 📚 Full Documentation

See `EXPERT_NETWORKS_IMPLEMENTATION.md` for:
- Complete architecture details
- All 15 API endpoints
- Database schema
- Advanced features
- Production deployment guide
