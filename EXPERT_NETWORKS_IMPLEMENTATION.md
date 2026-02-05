# Expert Networks Module - Implementation Complete

## Overview

Successfully integrated the expertNetworks application as a new module in the Bain Hackathon project. The module aggregates expert profiles from email (AlphaSights, Guidepoint, GLG), uses AI to extract/deduplicate experts, and provides a tracker table for managing expert calls.

## Architecture

### Backend (FastAPI)
- **Database**: SQLite (`backend/expert_networks.db`) with 8 tables
- **API Routes**: `/api/expert-networks/*` with full CRUD operations
- **AI Services**: OpenAI GPT-4o for extraction and recommendations
- **Deduplication**: Levenshtein distance-based fuzzy matching

### Frontend (React + TypeScript)
- **Module**: `/expert-networks` with 3 main pages
- **State Management**: React Query for API caching
- **UI Components**: shadcn/ui with Tailwind CSS

## Files Created

### Backend (12 files)
```
backend/
├── expert_networks.db                          # SQLite database (auto-generated)
├── create_database.py                          # Database setup script
├── prisma/schema.prisma                        # Database schema definition
├── app/
    ├── db/
    │   ├── database.py                         # DB connection singleton
    │   └── queries/
    │       ├── projects.py                     # Project CRUD
    │       ├── experts.py                      # Expert CRUD
    │       ├── emails.py                       # Email CRUD
    │       └── dedupe.py                       # Deduplication queries
    ├── schemas/
    │   └── expert_extraction.py                # Pydantic models
    ├── services/
    │   ├── expert_extraction.py                # AI extraction service
    │   ├── expert_dedupe.py                    # Deduplication service
    │   ├── expert_commit.py                    # Commit service
    │   └── expert_export.py                    # CSV export service
    └── api/routes/
        └── expert_networks.py                  # FastAPI routes (15 endpoints)
```

### Frontend (11 files)
```
frontend/src/modules/expert-networks/
├── index.tsx                                   # Module registration
├── types.ts                                    # TypeScript types
├── api.ts                                      # API client + React Query hooks
├── ProjectListPage.tsx                         # Project management UI
├── IngestPage.tsx                              # Email extraction UI
└── TrackerPage.tsx                             # Main tracker table (MVP)
```

## API Endpoints

### Projects
- `GET /api/expert-networks/projects` - List all projects
- `POST /api/expert-networks/projects` - Create project
- `GET /api/expert-networks/projects/{id}` - Get project
- `PATCH /api/expert-networks/projects/{id}` - Update project
- `DELETE /api/expert-networks/projects/{id}` - Delete project

### Email Extraction & Commit
- `POST /api/expert-networks/projects/{id}/extract` - Extract experts from email (AI)
- `POST /api/expert-networks/projects/{id}/commit` - Commit selected experts to tracker

### Experts
- `GET /api/expert-networks/projects/{id}/experts` - List experts (with status filter)
- `GET /api/expert-networks/experts/{id}` - Get expert details
- `PATCH /api/expert-networks/experts/{id}` - Update expert
- `DELETE /api/expert-networks/experts/{id}` - Delete expert
- `GET /api/expert-networks/experts/{id}/sources` - Get expert sources (emails)
- `POST /api/expert-networks/experts/{id}/recommend` - Generate AI recommendation

### Deduplication
- `GET /api/expert-networks/projects/{id}/duplicates` - Get duplicate candidates
- `POST /api/expert-networks/duplicates/{id}/merge` - Merge duplicates
- `POST /api/expert-networks/duplicates/{id}/not-same` - Mark as different people

### Export
- `GET /api/expert-networks/projects/{id}/export` - Export experts to CSV

## Setup Instructions

### 1. Install Backend Dependencies
```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install databases aiosqlite
```

### 2. Create Database
```bash
cd backend
python create_database.py
```

### 3. Configure OpenAI API Key
Edit `backend/settings.json`:
```json
{
  "openai_api_key": "sk-your-key-here"
}
```

Or set environment variable:
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

### 4. Start Backend
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 5. Start Frontend
```bash
cd frontend
npm run dev
```

### 6. Access Application
Open browser to `http://localhost:5173` and click "Expert Networks" in the sidebar.

## Testing Guide

### Test 1: Create Project
1. Navigate to `/expert-networks`
2. Click "New Project"
3. Enter:
   - Name: "Test PE Due Diligence"
   - Hypothesis: "Understanding retail transformation in Southeast Asia"
4. Click "Create Project"

### Test 2: Ingest Email
1. Click "Ingest Email" button
2. Select network: "AlphaSights" (optional)
3. Paste test email from `~/Downloads/expertNetworks/seed/emails/alphasights-batch1.txt`
4. Click "Extract Experts"
5. Review extracted experts (should find 3 experts: Sarah Chen, Michael Rodriguez, Jennifer Walsh)
6. Select experts to commit (all selected by default)
7. Click "Commit X Experts to Tracker"

### Test 3: Tracker Table
1. Verify experts appear in tracker table
2. Test inline editing:
   - Click on name to edit
   - Change status dropdown
   - Set conflict status
   - Pick interview date
   - Enter lead interviewer name
3. Test filters:
   - Search by name
   - Filter by status
4. Click "Export CSV" to download

### Test 4: Deduplication (Automatic)
1. Ingest another email with same expert (different email from seed folder)
2. Backend automatically detects duplicates
3. View duplicates at `/api/expert-networks/projects/{id}/duplicates`

## Features Implemented

### MVP Features (Complete)
✅ Project creation
✅ Email extraction (AI-powered)
✅ Tracker table (read + edit)
✅ Status management
✅ CSV export
✅ Automatic deduplication detection
✅ Inline editing
✅ Search and filters

### Advanced Features (Partially Implemented)
⚠️ AI recommendations - Backend ready, UI button not added (can call API directly)
⚠️ Duplicates UI - Detection works, merge UI not built (can merge via API)
⚠️ Source viewer modal - Backend ready, UI not built

### Skipped for MVP
❌ Pending updates (auto-accept all)
❌ User conflict resolution
❌ Multi-email thread UI
❌ Network inference refinement

## Database Schema

### Core Tables
- **Project**: Due diligence projects with hypothesis text
- **Email**: Raw ingested emails with extraction results
- **Expert**: Canonical/deduplicated expert profiles with status tracking
- **ExpertSource**: Links experts to email sources with extracted data
- **FieldProvenance**: Stores exact text excerpts for each extracted field
- **DedupeCandidate**: Tracks potential duplicate expert pairs
- **UserEdit**: Tracks manual field edits for conflict detection
- **PendingUpdate**: Queues extraction updates that conflict with user edits

## AI Extraction Process

1. **Input**: Raw email text + project hypothesis
2. **OpenAI GPT-4o**: Structured JSON extraction with provenance
3. **Deduplication**: Email threads automatically deduplicated (same expert mentioned multiple times → single entry)
4. **Selective Commit**: User reviews and selects experts to commit
5. **Automatic Matching**: New experts checked against existing for duplicates

## Key Technical Decisions

### SQLite Database
- **Why**: Self-contained, proven, fast for hackathon (2-3 days vs 4-5 days for SharePoint)
- **Trade-off**: Can migrate to SharePoint Lists later without changing API contracts
- **Location**: `backend/expert_networks.db` (gitignored, portable)

### No Prisma (JavaScript ORM)
- **Why**: Prisma 7 had compatibility issues
- **Solution**: Raw SQL via Python `databases` library (async-compatible)
- **Trade-off**: More verbose queries, but full control and no JS dependency

### Simplified TrackerPage
- **Why**: Original 746 lines too large for initial implementation
- **MVP Scope**: Core table with inline editing, filters, export
- **Future**: Add AI recommendation buttons, source viewer modals, advanced features

## Performance Considerations

### Rate Limiting
- Email extraction: 10 requests/minute
- AI recommendations: 20 requests/minute
- All other endpoints: Unlimited (add limits before production)

### Caching
- React Query caches API responses client-side
- Automatic refetch on mutations
- Database has indexes on frequently queried fields

## Security Notes

⚠️ **IMPORTANT**: Add authentication before production
- All endpoints currently unprotected
- TODO comments added to routes
- See `backend/app/main.py` for auth options

## Troubleshooting

### "OpenAI API key not set"
- Check `backend/settings.json` has `openai_api_key`
- Or set `OPENAI_API_KEY` environment variable

### "Database not found"
- Run `python backend/create_database.py`
- Check file exists at `backend/expert_networks.db`

### "Module not found" errors
- Install dependencies: `pip install databases aiosqlite`
- Check virtual environment is activated

### Frontend shows "Failed to fetch"
- Ensure backend is running on port 8000
- Check CORS settings in `backend/app/main.py`
- Verify `VITE_API_URL` environment variable

## Next Steps

### Immediate (Polish MVP)
1. Add AI recommendation button to TrackerPage
2. Test with all seed emails
3. Add loading states and error messages
4. Improve mobile responsiveness

### Short-term (Complete Features)
1. Build DuplicatesPage UI for manual merge review
2. Add ExpertSourceModal to view email excerpts
3. Implement pending updates workflow
4. Add bulk actions (delete, status change)

### Long-term (Production Ready)
1. Add authentication (OAuth2 + JWT)
2. Migrate to SharePoint Lists for persistence
3. Add user permissions and project ownership
4. Implement audit logging
5. Add email attachment parsing
6. Build analytics dashboard

## Credits

**Original expertNetworks**: Next.js full-stack app with Prisma ORM
**Integration**: Ported to Bain Hackathon FastAPI + React architecture
**AI Model**: OpenAI GPT-4o with structured output
**UI Components**: shadcn/ui + Tailwind CSS
