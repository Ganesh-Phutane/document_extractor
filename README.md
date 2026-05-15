# AI Document Extraction Platform

## 📖 1. Project Overview

### What is this project?

The **AI Document Extraction Platform** is a full-stack web application that uses AI to "read" documents and extract specific data points into a structured database. It acts as an automated data entry assistant for financial teams, business analysts, and operations managers.

### The Problem It Solves

Manual data entry from PDFs, images, and scanned documents is slow, expensive, and prone to human error. This project eliminates that bottleneck by providing a highly accurate, AI-driven pipeline that can process hundreds of documents in minutes.

### Application Flow & User Journey

1. **Authentication**: Users sign up and log in securely.
2. **Upload**: Users upload documents (PDF, Images, excel, XML).
3. **OCR Processing**: The system uses Azure Document Intelligence to analyze the layout and text.
4. **Multi-Agent Verification**: A multi-agent AI system processes the text, verifies data points for accuracy, and performs reconciliation.
5. **Validation**: Users review and verify the extracted data in the dashboard.
6. **Consolidation**: Verified data is saved into a "Master Database" for reporting and export.

---

## ✨ 2. Features

- **🔐 Secure Authentication**: JWT-based login and registration system with password encryption.
- **📊 Interactive Dashboard**: Real-time stats on processing volume, accuracy, and pending tasks.
- **🤖 Multi-Agent AI Extraction**: Uses a multi-agent system to verify data accuracy, process extraction results, and perform data reconciliation .
- **📂 Document Management**: A centralized queue to track the status of every uploaded document.
- **🗃️ Master Data Hub**: A consolidated view of all verified financial records across the entire history.
- **🚀 Automated CI/CD**: Ready-to-go Docker and GitHub Actions configuration for instant deployment.

---

## 🛠️ 3. Tech Stack

| Category            | Technology                                 |
| :------------------ | :----------------------------------------- |
| **Frontend**        | React.js (Vite)                            |
| **Backend**         | FastAPI (Python)                           |
| **Database**        | PostgreSQL (Azure Flexible Server)         |
| **Cloud Services**  | Azure Storage, Azure Document Intelligence |
| **AI Intelligence** | Google Gemini 1.5 Flash/Pro                |
| **DevOps**          | Docker, Nginx, GitHub Actions              |
| **Deployment**      | Azure App Service for Containers           |

---

## 🏗️ 4. Project Architecture

### Structure

The project is split into two main parts:

- **`/frontend`**: A modern Single Page Application (SPA) communicating via REST APIs.
- **`/backend`**: A high-performance Python API that handles AI logic and database operations.

### API & Data Flow

1. Frontend sends a document to the Backend API.
2. Backend uploads the file to **Azure Blob Storage**.
3. Backend triggers **Azure Document Intelligence** for OCR.
4. OCR results are sent to **Google Gemini** for structured mapping.
5. Structured data is returned to the Frontend and stored in **PostgreSQL**.

### Folder Structure

```text
project/
├── backend/                # FastAPI source code
│   ├── core/               # App configuration & security
│   ├── models/             # SQLAlchemy database models
│   ├── routes/             # API endpoints
│   ├── services/           # AI & Storage logic
│   └── scripts/            # Database seeding utility
├── frontend/               # React (Vite) source code
│   ├── src/
│   │   ├── components/     # UI Components
│   │   ├── pages/          # Page Views
│   │   └── services/       # API calling logic
├── .github/workflows/      # CI/CD pipelines
├── Dockerfile              # Production Docker config
└── start_dev.sh            # Local development script
```

---

## 💻 5. System Requirements

- **Operating System**: Windows 10+, macOS, or Linux (Ubuntu 22.04+ recommended).
- **Node.js**: v20.x or higher.
- **Python**: v3.11.x or higher.
- **RAM**: 8GB Minimum (16GB recommended for local development).
- **Storage**: 500MB for source code + extra for dependencies.
- **Browser**: Chrome, Firefox, or Edge (latest versions).

---

## 🔑 6. Environment Variables

Create a `.env` file in the root directory.

| Variable                          | Description                                                          |
| :-------------------------------- | :------------------------------------------------------------------- |
| `DATABASE_URL`                    | PostgreSQL connection string (`postgresql://user:pass@host:port/db`) |
| `SECRET_KEY`                      | Long random string for JWT token security                            |
| `AZURE_DI_KEY`                    | API Key for Azure Document Intelligence                              |
| `AZURE_DI_ENDPOINT`               | Endpoint URL for Azure Document Intelligence                         |
| `GEMINI_API_KEY`                  | API Key from Google AI Studio                                        |
| `AZURE_STORAGE_CONNECTION_STRING` | Connection string for Azure Blob Storage                             |

---

## ⚙️ 7. Installation Guide

### 1. Clone the Repository

```bash
git clone https://github.com/Flairminds/data-extraction-intelligence.git
cd data-extraction-intelligence
```

### 2. Backend Setup

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd ../frontend
npm install
```

### 4. Database Setup & Seeding

```bash
# From the project root
python backend/scripts/seed_templates.py
```

---

## 🏃 8. Running the Application

### Local Development

Run both servers at once from the root folder:

```bash
sh start_dev.sh
```

### Manual Start

- **Frontend**: `cd frontend && npm run dev` (Default: Port 5173)
- **Backend**: `cd backend && uvicorn main:app --reload` (Default: Port 8000)

**Access**: Open [http://localhost:5173](http://localhost:5173)

---

## 📑 9. API Documentation

The project includes interactive API docs (Swagger):

- **URL**: `http://localhost:8000/docs`

**Authentication Flow**:

- Send `POST /api/auth/login` with email/password.
- Receive `access_token`.
- Include `Authorization: Bearer <token>` in all subsequent headers.

---

## 🚢 11. Deployment Guide (Cloud Setup)

This project uses a modern **CI/CD pipeline** with Docker and Azure. Here is how the deployment works from start to finish:

### Step 1: Create a Docker Hub Repository
1. Log in to [Docker Hub](https://hub.docker.com/).
2. Create a new public repository (e.g., `your-username/document-extractor`).

### Step 2: Build and Push the Image
You can push your latest code to the cloud in two ways:

**Manual Way:**
Run the provided script in your terminal:
```bash
sh push_images.sh
```
*This script builds the image and pushes it to your Docker Hub account.*

**Automated Way (GitHub Actions):**
1. Push your code to the `main` branch on GitHub.
2. The robot in `.github/workflows/docker-push.yml` will automatically build and push the image for you.
3. **Note**: Make sure to add your `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` to your GitHub Repository Secrets.

### Step 3: Setup Azure App Service
1. Go to the [Azure Portal](https://portal.azure.com/).
2. Create a **Web App for Containers**.
3. In the **Deployment Center**:
   - Source: **Docker Hub**.
   - Repository: `your-username/document-extractor`.
   - Tag: `latest`.
4. In **Settings > Environment Variables**:
   - Add all keys from your `.env` (DATABASE_URL, AZURE_KEY, etc.).
   - Set `WEBSITE_PORT = 80`.
5. Enable **Continuous Deployment** so Azure pulls the new image every time it's updated on Docker Hub.

---

## 🖼️ 12. Screenshots

#### Authentication (Login/Register)

![Login Page](./screenshots/login.png)
![Register Page](./screenshots/register.png)

#### Dashboard & Extraction

![Dashboard](./screenshots/dashboard.png)
![Extraction](./screenshots/upload_extract.png)

#### Settings & Master Data

![Settings](./screenshots/extraction_settings.png)
![Master Data](./screenshots/master_data.png)
