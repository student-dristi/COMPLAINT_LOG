from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import sqlite3
import csv
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "complaints.db"
EXPORT_FILE = "complaints_export.csv"

# --- DATABASE SETUP ---
def init_db():
    """Creates the database table if it doesn't exist."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                phone TEXT,
                plant TEXT,
                category TEXT,
                complaint TEXT,
                date TEXT,
                status TEXT
            )
        ''')
        conn.commit()

# Initialize DB on startup
init_db()

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

    current_time = datetime.now(timezone.utc).isoformat()
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO complaints (username, phone, plant, category, complaint, date, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (data.username, data.phone, data.plant, category, data.complaint, current_time, "pending"))
            conn.commit()
            
        return {"message": "Complaint stored successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving complaint: {e}")

@app.get("/api/user_logs")
async def get_user_logs(phone: str):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            # This makes the rows look like dictionaries (easier to use)
            conn.row_factory = sqlite3.Row 
            cursor = conn.cursor()
            
            # SQL Query: Get all pending complaints for this phone number, sorted by date
            cursor.execute('''
                SELECT * FROM complaints 
                WHERE phone = ? AND status = 'pending'
                ORDER BY date DESC
            ''', (phone.strip(),))
            
            rows = cursor.fetchall()
            return rows # FastAPI automatically converts these to JSON
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading complaints: {e}")
# main.py

# ... (Previous code remains the same)

# NEW: Endpoint to mark a complaint as resolved
@app.put("/api/complaint/{ticket_id}/resolve")
async def resolve_complaint(ticket_id: int):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # Check if ticket exists first
            cursor.execute("SELECT id FROM complaints WHERE id = ?", (ticket_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Ticket not found")

            # Update status
            cursor.execute("DELETE FROM complaints WHERE id = ?", (ticket_id,))
            conn.commit()
            
        return {"message": f"Ticket #{ticket_id} marked as resolved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating ticket: {e}")

# ... (Export function remains the same)

@app.get("/api/export_csv")
async def export_csv():
    """
    1. Reads all data from SQLite.
    2. Writes it to a temporary CSV file.
    3. Sends that file to the user.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username, phone, plant, category, complaint, date, status FROM complaints")
            rows = cursor.fetchall()

        # Generate a fresh CSV file from the database data
        with open(EXPORT_FILE, mode='w', newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            # Write Header
            writer.writerow(["username", "phone", "plant", "category", "complaint", "date", "status"])
            # Write Data
            writer.writerows(rows)

        # Headers to prevent caching (so you always get the latest data)
        headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
        
        return FileResponse(
            path=EXPORT_FILE, 
            filename="it_support_tickets.csv", 
            media_type='text/csv',
            headers=headers
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting data: {e}")