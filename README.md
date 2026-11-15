# Dental-IQ

AI-ready platform for Goa Dental College & Hospital: digitised dental records + student competency tracking.

*(Full README is completed at the end of Phase 1.)*

## Run

```bash
# backend
cd backend
python -m venv .venv && .venv/Scripts/activate   # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000

# frontend
cd frontend
npm install
npm run dev
```
