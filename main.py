import os
import json
import io
import gspread
from PIL import Image
from instagrapi import Client
from google.oauth2.service_account import Credentials
from huggingface_hub import InferenceClient

# 1. جلب البيانات السرية
hf_token = os.getenv('HF_TOKEN')
ig_username = os.getenv('IG_USERNAME')
ig_password = os.getenv('IG_PASSWORD')
gcp_key_json = json.loads(os.getenv('GCP_SA_KEY'))

# 2. معرف ملف جوجل شيت
SHEET_ID = '1o-qImlB8GNLrAL1Kb7y5e1PPUERMFya5M6QZ3JjhEos'

# 3. إعداد العميل الرسمي لـ Hugging Face
# نستخدم موديل Stable Diffusion v1.5 لأنه مستقر جداً ومجاني
client_hf = InferenceClient(token=hf_token)
MODEL_ID = "runwayml/stable-diffusion-v1-5"

def generate_image(prompt):
    clean_prompt = prompt.replace('|', ',').strip()
    print(f"🎨 جاري طلب صورة لـ: {clean_prompt}")
    try:
        # استخدام المكتبة الرسمية لتوليد الصورة
        image = client_hf.text_to_image(clean_prompt, model=MODEL_ID)
        
        # تحويل الصورة إلى Bytes لتتوافق مع الكود
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG')
        return img_byte_arr.getvalue()
    except Exception as e:
        print(f"❌ خطأ في توليد الصورة عبر المكتبة الرسمية: {e}")
        return None

# 4. الاتصال بجوجل شيت
try:
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(gcp_key_json, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID).sheet1
    print("✅ تم الاتصال بـ Google Sheets بنجاح")
except Exception as e:
    print(f"❌ فشل الاتصال بالشيت: {e}")
    exit()

# 5. معالجة البيانات والنشر
rows = sh.get_all_records()
found_item = False

for i, row in enumerate(rows):
    status_value = str(row.get('Status', '')).strip().lower()
    
    if status_value == "" or status_value == "none":
        found_item = True
        print(f"🔄 جاري معالجة السطر رقم {i+2}...")
        
        img_data = generate_image(row['Prompt'])
        
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
                
                # تحديث الحالة
                sh.update_cell(i + 2, 3, "Done") 
                print(f"✅ تم النشر بنجاح للسطر {i+2}")
                break 
                
            except Exception as e:
                print(f"❌ خطأ أثناء النشر: {e}")
                break
        else:
            print("🛑 فشل توليد الصورة.")
            break

if not found_item:
    print("ℹ️ لا توجد أسطر جديدة للنشر.")

print("🏁 انتهت العملية.")
