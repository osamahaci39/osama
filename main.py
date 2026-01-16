import os
import json
import io
import gspread
import requests
import urllib.parse
from PIL import Image
from instagrapi import Client
from google.oauth2.service_account import Credentials

# 1. جلب البيانات السرية من جيتهاب
ig_username = os.getenv('IG_USERNAME')
ig_password = os.getenv('IG_PASSWORD')
gcp_key_json = json.loads(os.getenv('GCP_SA_KEY'))

# 2. معرف ملف جوجل شيت الخاص بك
SHEET_ID = '1o-qImlB8GNLrAL1Kb7y5e1PPUERMFya5M6QZ3JjhEos'

def generate_image(prompt):
    # تنظيف البرومبت وتحويله لصيغة تناسب الروابط (URL Encoding)
    clean_prompt = prompt.replace('|', ',').strip()
    encoded_prompt = urllib.parse.quote(clean_prompt)
    
    # استخدام Pollinations AI (مجاني، سريع، ولا يحتاج توكن)
    # نطلب صورة مربعة 1024x1024 وبدون شعار الموقع
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&seed=42"
    
    print(f"🎨 جاري طلب صورة لـ: {clean_prompt}")
    try:
        response = requests.get(image_url, timeout=60)
        if response.status_code == 200:
            return response.content
        else:
            print(f"❌ فشل السيرفر: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {str(e)}")
        return None

# 3. الاتصال بجوجل شيت
try:
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(gcp_key_json, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID).sheet1
    print("✅ تم الاتصال بـ Google Sheets بنجاح")
except Exception as e:
    print(f"❌ فشل الاتصال بالشيت: {str(e)}")
    exit()

# 4. عملية النشر
rows = sh.get_all_records()
found_item = False

for i, row in enumerate(rows):
    status_value = str(row.get('Status', '')).strip().lower()
    
    if status_value == "" or status_value == "none":
        found_item = True
        prompt = str(row.get('Prompt', '')).strip()
        if not prompt: continue
            
        print(f"🔄 جاري معالجة السطر رقم {i+2}...")
        img_data = generate_image(prompt)
        
        if img_data:
            try:
                # حفظ الصورة
                with open("final_post.jpg", "wb") as f:
                    f.write(img_data)
                
                print("📲 جاري تسجيل الدخول لإنستقرام...")
                cl = Client()
                cl.login(ig_username, ig_password)
                
                print("📤 جاري رفع المنشور...")
                cl.photo_upload("final_post.jpg", caption=row['Caption'])
                
                # تحديث الحالة في الشيت
                sh.update_cell(i + 2, 3, "Done") 
                print(f"✅ تم النشر بنجاح على إنستقرام للسطر {i+2}")
                break 
                
            except Exception as e:
                print(f"❌ خطأ أثناء النشر: {str(e)}")
                # ملاحظة: إذا ظهر خطأ في تسجيل الدخول، تأكد من هاتفك (تأكيد الهوية)
                break
        else:
            print("🛑 لم يتم إنشاء الصورة.")
            break

if not found_item:
    print("ℹ️ لا توجد أسطر جديدة للنشر.")

print("🏁 انتهت العملية.")
