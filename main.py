import uuid
import os
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = FastAPI()

# Google Sheets Configuration
SPREADSHEET_ID = "1G7pGNSOADTmnKq_wKP0ikwckzOkvt_-Rjfk2wYnAJUY"
SERVICE_ACCOUNT_FILE = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_NAME = "Sayfa1"

# 1. AI Analysis & Urgency Calculation
def calculate_urgency(message: str) -> int:
    """Calculates an urgency score from 1 (Low) to 5 (Critical) based on keywords."""
    msg = message.lower()
    
    # Keyword weights
    critical = ["iade", "refund", "acil", "bozuk", "broken", "hata", "error", "error 500"]
    high = ["sorun", "problem", "sikayet", "complaint", "calismiyor"]
    medium = ["yardim", "help", "destek", "support", "nasil"]
    low = ["tesekkur", "thanks", "bilgi", "nasilsiniz"]
    
    if any(k in msg for k in critical): return 5
    if any(k in msg for k in high): return 4
    if any(k in msg for k in medium): return 3
    if any(k in msg for k in low): return 1
    
    return 3 # Default to Medium

# Add CORS Middleware to allow requests from the UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Processing Function
def process_data(payload: dict) -> dict:
    """Receives data and initializes properly."""
    print("-> Status: Running Process Function...")
    
    # Extract values with safe fallbacks
    customer_name = payload.get("customer", "Unknown Customer")
    inquiry = payload.get("message", "No message provided")
    
    # Calculate Urgency
    urgency = calculate_urgency(inquiry)
    
    # Initialize basic properties
    # Validates whether the minimum required field (message) is provided
    processed = {
        "id": str(uuid.uuid4()),
        "customer": customer_name,
        "message": inquiry,
        "urgency_level": urgency,
        "processed_at": datetime.now().isoformat(),
        "is_valid": bool(inquiry and inquiry != "No message provided")
    }
    
    print(f"   [Data Initialized] {processed}")
    return processed

# 4. External API (Sheets/CRM)
def send_to_crm(data: dict) -> bool:
    """Saves data to a real Google Sheet."""
    print("-> Status: Calling Google Sheets API...")
    if not data.get("is_valid"):
        print("   [Failed] Data is invalid, skipped Sheets.")
        return False

    try:
        # Authentication
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        service = build("sheets", "v4", credentials=creds)

        # Prepare the row: [Timestamp, Name, Email(empty), Message, AI Category(empty), Urgency]
        values = [[
            data.get("processed_at"),
            data.get("customer"),
            "", # Email placeholder
            data.get("message"),
            "", # AI Category placeholder
            data.get("urgency_level")
        ]]
        body = {"values": values}

        # Append data to the sheet
        result = service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A1",
            valueInputOption="RAW",
            body=body
        ).execute()

        print(f"   [Success] Appended row to '{SHEET_NAME}'. Sheets Updated: {result.get('updates').get('updatedCells')} cells. Urgency Score: {data.get('urgency_level')}")
        return True

    except Exception as e:
        print(f"   [Error] Failed to write to Google Sheets: {e}")
        return False

# 5. AI Completion
def get_ai_completion(data: dict) -> str:
    """Mock AI Completion."""
    print("-> Status: Calling AI Completion API...")
    
    if not data.get("is_valid"):
        print("   [Failed] Cannot process invalid data with AI.")
        return "Error: Invalid data."
        
    inquiry = data.get("message", "")
    
    # Simple simulated logic based on inquiry content
    if "refund" in inquiry.lower():
        response = "AI Response: I can help you process your refund. Please provide your order number."
    elif "password" in inquiry.lower():
        response = "AI Response: It looks like you need help resetting your password. I will email you a reset link."
    else:
        response = "AI Response: Thank you for reaching out. A human agent will review your inquiry shortly."
        
    print(f"   [AI Generated] {response}")
    return response

# 2. Trigger (Webhook)
@app.post("/webhook")
async def handle_trigger(request: Request):
    """
    Trigger point: 
    Receives JSON payload, e.g. {"customer": "Alice", "message": "I need a refund"}
    """
    print("\n==================================")
    print("-> Status: Trigger Fired! Received Webhook POST request.")
    
    # Get JSON payload from webhook
    data = await request.json()
    print(f"   [Payload] {data}")
    
    # Execute Pipeline Steps
    processed_data = process_data(data)
    crm_success = send_to_crm(processed_data)
    ai_response = get_ai_completion(processed_data)
    
    print("-> Status: Pipeline Completed.")
    print("==================================\n")
    
    # Return success payload mimicking a successful workflow run
    return {
        "status": "success",
        "urgency_level": processed_data.get("urgency_level"),
        "pipeline_results": {
            "trigger_fired": True,
            "data_processed": True,
            "crm_written": crm_success,
            "ai_completion": ai_response
        }
    }

@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Serves the UI frontend."""
    with open("index.html", "r") as f:
        return f.read()

# Run directly if file is executed
if __name__ == "__main__":
    import uvicorn
    print("Starting AI Customer Support Assignment Webhook Server on port 8000...")
    uvicorn.run(app, host="127.0.0.1", port=8000)

