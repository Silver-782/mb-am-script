import json
import time
import random
import csv
import os
import subprocess
from datetime import datetime
from playwright.sync_api import sync_playwright

#
ACK_MESSAGE = """Thank you for contacting the Mercedes-Benz Alice support.
We have received your request and will process it as soon as possible.

Please refer to our Knowledge article for more information about our support process and resolution times.
Link to our Knowledge articke:  https://servicenow.i.mercedes-benz.com/esc?id=kb_article&sysparm_article=KB0346126

If you want to explore Mercedes‑Benz IAM in more depth, we now offer a unified Documentation Platform where all our guidance, resources, and technical information are brought together in one place. 
For more details, please check the Documentation Platform: https://documentation.iam.mercedes-benz.com/"""

def run():
    try:
        with open('incident.json', 'r', encoding='utf-8') as f:
            tickets = json.load(f).get('records', [])
    except FileNotFoundError:
        print("Error: 'incident.json' not found.")
        return
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    log_filename = f"acknowledgment_log_{timestamp}.csv"

    subprocess.run(["taskkill", "/F", "/IM", "msedge.exe", "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    
    with sync_playwright() as p:
        edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        
        user_data_path = os.path.expanduser("~") + r"\AppData\Local\Microsoft\Edge\Playwright Data"

        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_path,
            executable_path=edge_path,
            headless=False,
            slow_mo=1000,
            args=["--profile-directory=Default"] # Your specific flag
        )
        
        if len(context.pages) > 0:
            page = context.pages[0]
        else:
            page = context.new_page()

        page.goto("https://servicenow.i.mercedes-benz.com/")

        print("\n" + "="*50)
        input("🛑 PAUSED: Please complete your SSO login in the Edge window.\nPress ENTER in this terminal when you are fully logged in to continue...")
        print("="*50 + "\n")

        for ticket in tickets:
            sys_id = ticket.get('sys_id')
            number = ticket.get('number')
            url = f"https://servicenow.i.mercedes-benz.com/incident.do?sys_id={sys_id}"
            
            try:
                textarea = None
                for attempt in range(3):
                    print(f"Loading {number} (Attempt {attempt + 1})...")
                    page.goto(url) 

                    # Identify target (frame or page)
                    if page.locator('iframe[name="gsft_main"]').count() > 0:
                        target = page.frame_locator('iframe[name="gsft_main"]')
                    else:
                        target = page
                    
                    textarea = target.locator("#activity-stream-textarea")

                    time.sleep(random.uniform(1, 3))
                    try:
                        # 15s wait for the element to prove the page is truly "ready"
                        textarea.wait_for(state="visible", timeout=15000)
                        break 
                    except:
                        if attempt == 2:
                            raise Exception("Textarea not found after 3 URL loads")
                        print(f"  {number} not ready. Re-hitting URL...")

                time.sleep(random.uniform(1, 3))
                toggle_label = target.locator("label[for*='journal-checkbox']:has-text('Additional comments')")
                if "Work notes" in textarea.get_attribute("aria-label"):
                    print(f"-> Switching to Customer Visible...")
                    toggle_label.click()
                    page.wait_for_timeout(1000)

                time.sleep(random.uniform(1, 3))
                textarea.fill(ACK_MESSAGE, force=True)
                target.locator("button.activity-submit").click()
                
                print(f"SUCCESS: {number}")

                with open(log_filename, mode='a', newline='') as log_file:
                    csv.writer(log_file).writerow([number, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "SUCCESS"])
                
                time.sleep(random.uniform(3, 7))

            except Exception as e:
                print(f"FAILED {number}: {e}")
                with open(log_filename, mode='a', newline='') as log_file:
                    csv.writer(log_file).writerow([number, datetime.now(), f"ERROR: {e}"])

        context.close()

if __name__ == "__main__":
    run()