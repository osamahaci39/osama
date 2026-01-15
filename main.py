import os
import json
import requests
import io
import gspread
from PIL import Image
from instagrapi import Client
from google.oauth2.service_account import Credentials

# 1. جلب البيانات السرية من جيتهاب
hf_token = os.getenv('HF_TOKEN')
ig_username = os.getenv('IG_USERNAME')
ig_password = os.getenv('IG_PASSWORD')
# تحويل نص الـ JSON إلى قاموس بايثون
gcp_key_json = json.loads(os.getenv('GCP_SA_KEY'))

# 2. الاتصال بـ Google Sheets
# هام: استبدل 'MySheetName' باسم ملف الشيت الخاص بك بالضبط
SHEET_NAME = 'propm' 

try:
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(gcp_key_json, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open(SHEET_NAME).sheet1
    print("✅ تم الاتصال بـ Google Sheets بنجاح")
except Exception as e:
    print(f"❌ خطأ في الاتصال بجوجل شيت: {e}")
    exit()

# 3. إعدادات توليد الصور (Hugging Face)
API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
headers = {"Authorization": f"Bearer {hf_token}"}

def generate_image(prompt):
    print(f"🎨 جاري إنشاء صورة لـ: {prompt}")
    response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"خطأ في توليد الصورة: {response.status_code}")

# 4. عملية النشر
rows = sh.get_all_records()
for i, row in enumerate(rows):
    # الكود سيبحث عن أول سطر عمود الـ Status فيه ليس "Done"
    if str(row.get('Status', '')).strip().lower() != 'done':
        try:
            # توليد الصورة
            img_data = generate_image(row['Prompt'])
            image = Image.open(io.BytesIO(img_data))
            image.save("temp_post.jpg")
            
            # الدخول لنشر الصورة
            print("📲 جاري تسجيل الدخول في إنستقرام...")
            cl = Client()
            # لتقليل احتمالية الحظر، سنستخدم إعدادات بسيطة
            cl.login(ig_username, ig_password)
            
            print("📤 جاري رفع المنشور...")
            cl.photo_upload("temp_post.jpg", caption=row['Caption'])
            
            # تحديث حالة السطر في الشيت (تأكد أن عمود Status هو العمود الثالث C)
            sh.update_cell(i + 2, 3, "Done") 
            print(f"✅ تم النشر بنجاح للسطر {i+2}")
            break # ينشر صورة واحدة فقط في كل مرة يعمل فيها السكربت
            
        except Exception as e:
            print(f"❌ فشل في معالجة السطر {i+2}: {e}")
            break

print("🏁 انتهت العملية.")
