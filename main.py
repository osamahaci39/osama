import os
import json
import io
import gspread
import time
from PIL import Image
from instagrapi import Client
from google.oauth2.service_account import Credentials
import requests

# 1. جلب البيانات السرية
hf_token = os.getenv('HF_TOKEN')
ig_username = os.getenv('IG_USERNAME')
ig_password = os.getenv('IG_PASSWORD')
gcp_key_json = json.loads(os.getenv('GCP_SA_KEY'))

# 2. معرف ملف جوجل شيت
SHEET_ID = '1o-qImlB8GNLrAL1Kb7y5e1PPUERMFya5M6QZ3JjhEos'

# 3. استخدام موديل OpenJourney (مستقر جداً ومجاني)
# سنستخدم طلب الـ HTTP المباشر بدلاً من المكتبة لنرى الخطأ بوضوح
MODEL_URL = "https://router.huggingface.co/models/prompthero/openjourney"
headers = {"Authorization": f"Bearer {hf_token}"}

def generate_image(prompt):
    clean_prompt = prompt.replace('|', ',').strip()
    print(f"🎨 جاري طلب صورة لـ: {clean_prompt}")
    
    payload = {"inputs": clean_prompt, "options": {"wait_for_model": True}}
    
    try:
        response = requests.post(MODEL_URL, headers=headers, json=payload, timeout=90)
        
        if response.status_code == 200:
            return response.content
        elif response.status_code == 503:
            print("⏳ الموديل يتم تحميله الآن (Cold Start)، سننتظر 20 ثانية...")
            time.sleep(20)
            return generate_image(prompt) # إعادة المحاولة
        else:
            print(f"❌ خطأ من Hugging Face (Status {response.status_code}): {response.text}")
            return None
    except Exception as e:
        print(f"❌ خطأ تقني في الاتصال: {str(e)}")
        return None

# 4. الاتصال بجوجل شيت
try:
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(gcp_key_json, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID).sheet1
    print("✅ تم الاتصال بـ Google Sheets")
except Exception as e:
    print(f"❌ فشل الاتصال بالشيت: {str(e)}")
    exit()

# 5. معالجة البيانات والنشر
rows = sh.get_all_records()
found_item = False

for i, row in enumerate(rows):
    status_value = str(row.get('Status', '')).strip().lower()
    
    if status_value == "" or status_value == "none":
        found_item = True
        # التأكد من وجود برومبت
        prompt = str(row.get('Prompt', '')).strip()
        if not prompt:
            continue
            
        print(f"🔄 جاري معالجة السطر رقم {i+2}...")
        img_data = generate_image(prompt)
        
        if img_data:
            try:
                with open("final_post.jpg", "wb") as f:
                    f.write(img_data)
                
                print("📲 جاري تسجيل الدخول لإنستقرام...")
                cl = Client()
                cl.login(ig_username, ig_password)
                
                print("📤 جاري رفع المنشور...")
                cl.photo_upload("final_post.jpg", caption=row['Caption'])
                
                sh.update_cell(i + 2, 3, "Done") 
                print(f"✅ تم النشر بنجاح للسطر {i+2}")
                break 
                
            except Exception as e:
                print(f"❌ خطأ أثناء النشر: {str(e)}")
                break
        else:
            print("🛑 فشل توليد الصورة.")
            break

if not found_item:
    print("ℹ️ لا توجد أسطر جديدة للنشر.")

print("🏁 انتهت العملية.")
