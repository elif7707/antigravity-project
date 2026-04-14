import os
import json
import datetime
from dotenv import load_dotenv
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load environment variables from .env
load_dotenv()

# Configure Gemini AI
GENIMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GENIMINI_API_KEY)

def run_workflow(inputs):
    print("🚀 Starting Antigravity Python Workflow Engine...")
    
    # Load workflow.ag
    try:
        with open('workflow.ag', 'r', encoding='utf-8') as f:
            workflow = json.load(f)
    except Exception as e:
        print(f"❌ Error loading workflow.ag: {e}")
        return

    context = inputs.copy()

    for node in workflow['nodes']:
        print(f"\n📦 Executing Node: {node['name']} ({node['type']})")
        
        try:
            if node['type'] == 'Webhook':
                # Inputs already provided
                pass

            elif node['type'] == 'Function':
                print("  > Running JS Transformation Simulation (Python equivalent)...")
                # Since we are in Python, we simulate the JS logic or use a JS runner if needed.
                # For this specific workflow: { ...inputs, order_id: inputs.order_id.trim(), timestamp: new Date().toISOString() }
                context['order_id'] = context['order_id'].strip()
                context['timestamp'] = datetime.datetime.now().isoformat()
                print(f"  > Output Data: {json.dumps(context, indent=2)}")

            elif node['type'] == 'AI Completion':
                print("  > Calling Gemini AI (gemini-2.0-flash)...")
                model = genai.GenerativeModel('gemini-2.0-flash')
                
                prompt = f"""
                Task: {node['config']['task']}
                Input: {json.dumps(context)}
                Rules: {json.dumps(node['config']['rules'])}
                
                Respond ONLY with a JSON object containing the following keys: {', '.join(node['config']['outputs'])}.
                Do not include markdown or explanations.
                """
                
                try:
                    response = model.generate_content(prompt)
                    text = response.text.strip()
                    print(f"  > AI Raw Output: {text}")
                    
                    # Extract JSON
                    import re
                    json_match = re.search(r'\{.*\}', text, re.DOTALL)
                    if json_match:
                        ai_data = json.loads(json_match.group())
                        context.update(ai_data)
                        print(f"  > AI Decoded: {json.dumps(ai_data)}")
                    else:
                        raise ValueError("No JSON found in AI response")
                        
                except Exception as ai_e:
                    if "429" in str(ai_e):
                        print("  > ⚠️ QUOTA EXCEEDED (429). Using internal fallback logic...")
                        reason = context.get('return_reason', '').lower()
                        if 'damage' in reason or 'broken' in reason:
                            context['category'] = 'Shipping Damage'
                            context['urgency'] = 'High'
                        elif 'size' in reason or 'fit' in reason:
                            context['category'] = 'Exchange'
                            context['urgency'] = 'Medium'
                        else:
                            context['category'] = 'General Return'
                            context['urgency'] = 'Low'
                        print(f"  > Fallback Applied: {json.dumps({'category': context['category'], 'urgency': context['urgency']})}")
                    else:
                        raise ai_e

            elif node['type'] == 'Google Sheets':
                print("  > Exporting to Google Sheets...")
                
                # Check for credentials.json
                creds_path = 'credentials.json'
                if os.path.exists(creds_path):
                    creds = service_account.Credentials.from_service_account_file(
                        creds_path, scopes=['https://www.googleapis.com/auth/spreadsheets']
                    )
                    service = build('sheets', 'v4', credentials=creds)
                    
                    # Prepare row data based on mapping
                    mapping = node['config']['mapping']
                    row_values = []
                    # Assuming a specific order or following mapping keys if needed.
                    # For this workflow, the user wanted specific columns:
                    # Timestamp, Customer Name, Email, Message, AI Category, Urgency Level
                    
                    ordered_columns = ["Timestamp", "Customer Name", "Email", "Message", "AI Category", "Urgency Level"]
                    for col in ordered_columns:
                        field = mapping.get(col)
                        row_values.append(context.get(field, ""))

                    spreadsheet_id = node['config']['spreadsheet_id']
                    
                    # Append row
                    service.spreadsheets().values().append(
                        spreadsheetId=spreadsheet_id,
                        range='A1',
                        valueInputOption='USER_ENTERED',
                        body={'values': [row_values]}
                    ).execute()
                    
                    print(f"  > ✅ SUCCESS: Row pushed to spreadsheet! ({json.dumps(row_values)})")
                else:
                    print("  > ⚠️ WARNING: credentials.json not found. Row NOT pushed (MOCKED).")

        except Exception as node_e:
            print(f"  > ❌ ERROR in node {node['name']}: {node_e}")
            break

    print("\n🏁 Python Workflow Execution Finished.")
    return context

if __name__ == "__main__":
    import sys
    # Example test cases
    test_inputs = {
        "order_id": " ORD-PY-100 ",
        "customer_name": "Python Tester",
        "email": "py@example.com",
        "return_reason": "The item is broken and cracked."
    }
    
    # Overwrite with CLI args if provided
    if len(sys.argv) > 1:
        test_inputs['order_id'] = sys.argv[1]
    if len(sys.argv) > 2:
        test_inputs['customer_name'] = sys.argv[2]
    if len(sys.argv) > 3:
        test_inputs['email'] = sys.argv[3]
    if len(sys.argv) > 4:
        test_inputs['return_reason'] = sys.argv[4]

    run_workflow(test_inputs)
