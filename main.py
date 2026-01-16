import os
import json
import requests
import io
import gspread
from PIL import Image
from instagrapi import Client
from google.oauth2.service_account import Credentials

# 1. جلب البيانات من الخزنة (Secrets)
hf_token = os.getenv('HF_TOKEN')
ig_username = os.getenv('IG_USERNAME')
ig_password = os.getenv('IG_PASSWORD')
gcp_key_json = json.loads(os.getenv('GCP_SA_KEY'))

# ⚠️ هام جداً: استبدل الاسم بين القوسين باسم ملف الشيت الخاص بك بالضبط
SHEET_NAME = 'ضع_اسم_ملف_الشيت_هنا' 

# 2. الموديل المجاني والمستقر (Stable Diffusion)
API_URL = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
headers = {"Authorization": f"Bearer {hf_token}"}

def generate_image(prompt):
    # تنظيف النص من العلامات الزائدة
    clean_prompt = prompt.replace('|', ',').strip()
    print(f"🎨 جاري طلب صورة لـ: {clean_prompt}")
    
    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": clean_prompt}, timeout=60)
        if response.status_code == 200:
            return response.content
        else:
            print(f"❌ فشل Hugging Face: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ خطأ أثناء الاتصال بـ Hugging Face: {e}")
        return None

# 3. الاتصال بجوجل شيت
try:
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(gcp_key_json, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open(SHEET_NAME).sheet1
    print("✅ تم الاتصال بـ Google Sheets")
except Exception as e:
    print(f"❌ خطأ في الاتصال بجوجل شيت (تأكد من اسم الملف والمشاركة): {e}")
    exit()

# 4. البحث عن سطر للنشر
rows = sh.get_all_records()
for i, row in enumerate(rows):
    # يبحث عن سطر حيث الـ Status فارغ
    if not row.get('Status') or str(row.get('Status')).strip() == "":
        print(f"🔄 جاري معالجة السطر رقم {i+2}...")
        
        img_data = generate_image(row['Prompt'])
        
        if img_data:
            try:
                # حفظ الصورة
                image = Image.open(io.BytesIO(img_data))
                image.save("post_image.jpg")
                
                # رفع للإنستقرام
                print("📲 جاري تسجيل الدخول لإنستقرام...")
                cl = Client()
                cl.login(ig_username, ig_password)
                
                print("📤 جاري رفع الصورة...")
                cl.photo_upload("post_image.jpg", caption=row['Caption'])
                
                # تحديث الشيت
                sh.update_cell(i + 2, 3, "Done") 
                print(f"✅ مبروك! تم النشر بنجاح للسطر {i+2}")
                break # ينشر واحدة فقط ثم يتوقف
            except Exception as e:
                print(f"❌ خطأ في النشر على إنستقرام: {e}")
                break
        else:
            print("🛑 فشل توليد الصورة، يرجى مراجعة صلاحيات التوكن.")
            break

print("🏁 انتهت المحاولة.")
