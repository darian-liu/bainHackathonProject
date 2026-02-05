# Bain Productivity Tool

A modular web application for document-based AI chat, featuring a Data Room module with RAG (Retrieval-Augmented Generation) capabilities and an agent action visualizer.

## Features

- **Data Room Module**: Chat with your documents using AI
  - Folder picker for document selection
  - Document ingestion (PDF, DOCX, PPTX)
  - RAG-powered chat with source citations
  
- **Agent Visualizer**: Real-time visualization of AI agent actions
  - WebSocket-based event streaming
  - ReactFlow graph visualization
  
- **Modular Architecture**: Easy to extend with new modules

## Tech Stack

### Frontend
- React 18 + TypeScript
- Vite
- Tailwind CSS
- ReactFlow
- Zustand (state management)
- TanStack Query

### Backend
- Python 3.11+
- FastAPI
- ChromaDB (vector store)
- OpenAI API
- CAMEL-AI (agent framework)
- Unstructured (document parsing)

## Prerequisites

- Node.js 18+
- Python 3.11+
- OpenAI API key

### Windows Setup for Document Parsing

The `unstructured` library requires poppler for PDF support:

1. **Install poppler**:
   - Download from: https://github.com/osba/poppler-windows/releases
   - Extract to `C:\poppler`
   - Add `C:\poppler\Library\bin` to your system PATH

2. **Verify installation**:
   ```bash
   pdfinfo --version
   ```

## Quick Start

### 1. Clone and setup environment

```bash
# Copy environment file
cp .env.example .env

# Edit .env and add your OpenAI API key
```

### 2. Start the application

**Windows:**
```batch
start-windows.bat
```

**Mac/Linux:**
```bash
chmod +x start-mac.sh
./start-mac.sh
```

### 3. Manual setup (if scripts don't work)

**Backend:**
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### 4. Access the application

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Usage

1. **Add Documents**: Place PDF, DOCX, or PPTX files in the `demo-docs/` folder (create subfolders to organize)

2. **Ingest Documents**: Select a folder in the UI and click "Ingest"

3. **Chat**: Ask questions about your documents

4. **View Agent Actions**: The right sidebar shows real-time agent activity

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DOCUMENT_SOURCE_MODE` | `mock` (local files) or `live` (SharePoint) | `mock` |
| `OPENAI_API_KEY` | OpenAI API key (required) | - |
| `USE_SIMPLE_AGENT` | Use simple OpenAI agent instead of CAMEL | `false` |
| `AZURE_CLIENT_ID` | Azure AD client ID (for SharePoint) | - |
| `AZURE_CLIENT_SECRET` | Azure AD client secret | - |
| `AZURE_TENANT_ID` | Azure AD tenant ID | - |
| `SHAREPOINT_SITE_ID` | SharePoint site ID | - |

## Connecting Personal Outlook

The Expert Networks module supports connecting your personal Outlook inbox to automatically ingest expert network emails.

### Step 1: Register Azure App

1. Go to [Azure Portal](https://portal.azure.com) → **App registrations** → **New registration**
2. Configure:
   - **Name**: `Bain Productivity Tool - Outlook`
   - **Supported account types**: Select **"Personal Microsoft accounts only"** (or "Accounts in any organizational directory and personal Microsoft accounts" for both work and personal)
   - **Redirect URI**: Select **Web** and enter `http://localhost:8000/api/outlook/callback`
3. After creation, note the **Application (client) ID**
4. Go to **Certificates & secrets** → **New client secret** → Copy the secret value

### Step 2: Configure API Permissions

1. Go to **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated permissions**
2. Add these permissions:
   - `User.Read` - Sign in and read user profile
   - `Mail.Read` - Read user mail
   - `offline_access` - Maintain access to data (for refresh tokens)
3. Click **Grant admin consent** (if you have admin rights) or wait for user consent during OAuth

### Step 3: Configure in App

1. Start the application and go to **Settings**
2. In the **Personal Outlook Integration** section, enter:
   - **Outlook Client ID**: Your Azure app's Application (client) ID
   - **Outlook Client Secret**: Your client secret value
   - **Redirect URI**: `http://localhost:8000/api/outlook/callback` (default)
   - **Allowed Sender Domains** (optional): e.g., `alphasights.com, guidepoint.com, glg.it`
3. Click **Save Settings**
4. Click **Connect Outlook** and complete the Microsoft login/consent flow
5. After successful connection, use **Test Connection** to verify

### Troubleshooting

- **"Token exchange failed"**: Check that Client ID and Secret are correct
- **"AADSTS50011" redirect URI error**: Ensure the redirect URI in Azure matches exactly
- **"Insufficient privileges"**: User needs to consent to the requested permissions

## Project Structure

```
bainHackathonProject/
├── frontend/           # React/TypeScript frontend
│   ├── src/
│   │   ├── components/ # UI components
│   │   ├── modules/    # Feature modules
│   │   ├── hooks/      # Custom hooks
│   │   ├── stores/     # Zustand stores
│   │   └── services/   # API clients
│   └── ...
├── backend/            # Python/FastAPI backend
│   ├── app/
│   │   ├── api/        # API routes
│   │   ├── agents/     # AI agents
│   │   ├── services/   # Core services
│   │   └── modules/    # Feature modules
│   └── ...
├── demo-docs/          # Place documents here
└── ...
```

## Adding a New Module

### Backend

1. Create module in `backend/app/modules/your_module/`
2. Implement `ModuleBase` interface
3. Register in `backend/app/modules/__init__.py`

### Frontend

1. Create module in `frontend/src/modules/your-module/`
2. Export `WorkflowModule` object
3. Register in `frontend/src/modules/module-registry.ts`

## License

Private - Bain & Company Hackathon Project
