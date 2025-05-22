# Gemini Terminal AI

تطبيق تفاعلي في الطرفية لتحويل الأوامر الإنجليزية إلى أوامر لينكس باستخدام Google Gemini API.

## المتطلبات
- Python 3.8+
- requests
- حساب Google Gemini API (ضع مفتاح API في متغير البيئة `GEMINI_API_KEY`)

## التشغيل
```bash
pip install -r requirements.txt
export GEMINI_API_KEY=your_gemini_api_key
python3 src/main.py
```
