import os
import json
import requests
import io
import gspread
import time
from PIL import Image
from instagrapi import Client
from google.oauth2.service_account import Credentials

# 1. جلب البيانات السرية من GitHub Secrets
hf_token = os.getenv('HF_TOKEN')
ig_username = os.getenv('IG_USERNAME')
ig_password = os.getenv('IG_PASSWORD')
gcp_key_json = json.loads(os.getenv('GCP_SA_KEY'))

# 2. معرف ملف جوجل شيت الخاص بك (تم استخراجه من الرابط)
SHEET_ID = '1o-qImlB8GNLrAL1Kb7y5e1PPUERMFya5M6QZ3JjhEos'

# 3. إعدادات موديل الصور (Stable Diffusion v1.5 - الأكثر استقراراً للمجاني)
API_URL = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
headers = {"Authorization": f"Bearer {hf_token}"}

def generate_image(prompt):
    # تنظيف البرومبت من أي علامات تعيق الموديل
    clean_prompt = prompt.replace('|', ',').strip()
    print(f"🎨 جاري طلب صورة لـ: {clean_prompt}")
    
    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": clean_prompt}, timeout=60)
        if response.status_code == 200:
            return response.content
        else:
            print(f"❌ خطأ في توليد الصورة: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ حدث خطأ أثناء الاتصال بـ Hugging Face: {e}")
        return None

# 4. الاتصال بجوجل شيت باستخدام الـ ID
try:
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(gcp_key_json, scopes=scopes)
    gc = gspread.authorize(creds)
    # الفتح عن طريق الـ ID يضمن عدم حدوث أخطاء في الأسماء
    sh = gc.open_by_key(SHEET_ID).sheet1
    print("✅ تم الاتصال بـ Google Sheets بنجاح")
except Exception as e:
    print(f"❌ فشل الاتصال: تأكد من مشاركة الملف مع إيميل البوت ووضع الـ ID الصحيح. الخطأ: {e}")
    exit()

# 5. معالجة البيانات والنشر
rows = sh.get_all_records()
found_item = False

for i, row in enumerate(rows):
    # يبحث عن أول سطر يكون فيه عمود Status فارغاً
    status_value = str(row.get('Status', '')).strip().lower()
    
    if status_value == "" or status_value == "none":
        found_item = True
        print(f"🔄 جاري العمل على السطر رقم {i+2}...")
        
        # توليد الصورة
        img_data = generate_image(row['Prompt'])
        
        if img_data:
            try:
                # حفظ الصورة مؤقتاً
                image = Image.open(io.BytesIO(img_data))
                image.save("final_post.jpg")
                
                # تسجيل الدخول والنشر
                print("📲 جاري الدخول لإنستقرام...")
                cl = Client()
                cl.login(ig_username, ig_password)
                
                print("📤 جاري رفع المنشور...")
                cl.photo_upload("final_post.jpg", caption=row['Caption'])
                
                # تحديث حالة السطر في الشيت (العمود C)
                sh.update_cell(i + 2, 3, "Done") 
                print(f"✅ تم النشر بنجاح للسطر {i+2}")
                break # ينشر واحدة فقط في كل دورة تشغيل
                
            except Exception as e:
                print(f"❌ خطأ أثناء النشر: {e}")
                break
        else:
            print("🛑 توقف السكربت لأن الموديل لم يستجب.")
            break

if not found_item:
    print("ℹ️ لا توجد أسطر جديدة للنشر (تأكد أن عمود Status فارغ).")

print("🏁 انتهت العملية.")
