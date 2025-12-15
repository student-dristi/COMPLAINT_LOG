from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse  # Imported FileResponse for downloads
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import csv
import os

app = FastAPI()

# Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CSV_FILE = "complaints.csv"

# Create file with header if missing OR empty
if not os.path.exists(CSV_FILE) or os.path.getsize(CSV_FILE) == 0:
    with open(CSV_FILE, mode='w', newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["username", "phone", "plant", "category", "complaint", "date", "status"])


class ComplaintRequest(BaseModel):
    username: str
    phone: str
    plant: str
    category: str
    complaint: str


@app.post("/api/complaint")
async def lodge_complaint(data: ComplaintRequest):
    category = data.category.lower()
    if category not in ["laptop", "desktop", "printer", "network", "software"]:
        raise HTTPException(status_code=400, detail="Invalid category")

    complaint_log = [
        data.username,
        data.phone,
        data.plant,
        category,
        data.complaint,
        datetime.now(timezone.utc).isoformat(),
        "pending"   # New complaints are always PENDING
    ]

    try:
        with open(CSV_FILE, mode='a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(complaint_log)
        return {"message": "Complaint stored successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving complaint: {e}")


def safe_parse(dt_string):
    try:
        return datetime.fromisoformat(dt_string)
    except:
        return datetime.strptime(dt_string, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)


@app.get("/api/user_logs")
async def get_user_logs(phone: str):
    logs = []
    try:
        with open(CSV_FILE, mode='r', newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Match phone + only pending complaints
                if row["phone"].strip() == phone.strip() and row["status"] == "pending":
                    logs.append(row)

        logs.sort(key=lambda x: safe_parse(x["date"]), reverse=True)
        return logs

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading complaints: {e}")



# --- NEW ENDPOINT FOR CSV EXPORT ---
@app.get("/api/export_csv")
async def export_csv():
    if not os.path.exists(CSV_FILE):
        raise HTTPException(status_code=404, detail="No complaints file found.")
    
    # We add headers to tell the browser NOT to cache this file
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }

    return FileResponse(
        path=CSV_FILE, 
        filename="complaints_export.csv", 
        media_type='text/xlx',
        headers=headers
    )