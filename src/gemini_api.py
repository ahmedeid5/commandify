import requests
import os
import shutil
from linux_commands_data import LINUX_COMMANDS, LINUX_COMMANDS_NEED_FILE
import time

# إضافة التخزين المؤقت للاقتراحات
SUGGESTIONS_CACHE = {}
MAX_CACHE_SIZE = 100
CACHE_EXPIRY = 24 * 60 * 60  # مدة صلاحية التخزين المؤقت بالثواني (24 ساعة)

def get_api_key():
    key_path = os.path.expanduser('~/.gemini_api_key')
    if os.path.exists(key_path):
        with open(key_path, 'r') as f:
            return f.read().strip()
    else:
        return None

def save_api_key(key):
    key_path = os.path.expanduser('~/.gemini_api_key')
    with open(key_path, 'w') as f:
        f.write(key.strip())

def get_linux_command(user_text):
    """
    Sends the user_text to Google Gemini API and returns the suggested Linux command as a string.
    """
    api_key = get_api_key()
    if not api_key:
        return "API key not found. Please set it from the main app."
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    prompt = f"Convert the following English instruction to a single Linux bash command. Only return the command, nothing else. Instruction: {user_text}"
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    response = requests.post(endpoint, headers=headers, json=data)
    if response.status_code == 200:
        try:
            command = response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            return command
        except Exception as e:
            return f"Error parsing Gemini response: {e}"
    else:
        return f"Gemini API error: {response.status_code} {response.text}"

def get_command_suggestions(user_text):
    user_text = user_text.strip()

    # التحقق من التخزين المؤقت أولاً
    cache_key = user_text.lower()
    current_time = time.time()
    if cache_key in SUGGESTIONS_CACHE:
        cache_item = SUGGESTIONS_CACHE[cache_key]
        # التحقق من صلاحية التخزين المؤقت
        if current_time - cache_item['timestamp'] < CACHE_EXPIRY:
            return cache_item['suggestions']

    # إذا كان المستخدم لم يكتب إلا بادئة (حرف أو أكثر)
    if user_text in LINUX_COMMANDS:
        args = LINUX_COMMANDS[user_text]
        suggestions = []
        api_key = get_api_key()
        # أضف شرح للأمر نفسه أولاً
        if api_key:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            prompt = (
                f"What does the Linux command '{user_text}' do? Answer in less than 10 words. Only return the description, nothing else."
            )
            data = {"contents": [{"parts": [{"text": prompt}]}]}
            try:
                response = requests.post(endpoint, headers=headers, json=data, timeout=4)
                if response.status_code == 200:
                    desc = response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                else:
                    desc = f"{user_text} command"
            except Exception:
                desc = f"{user_text} command"
        else:
            desc = f"{user_text} command"
        extra = LINUX_COMMANDS_NEED_FILE.get(user_text, '')
        if extra:
            desc = f"{desc} (needs {extra})"
        suggestions.append((user_text, desc))
        # ثم أضف الأرجومنتات مع شرح مختصر
        for arg in args:
            if api_key:
                prompt = (
                    f"What does the Linux command '{user_text} {arg}' do? Answer in less than 10 words. Only return the description, nothing else."
                )
                data = {"contents": [{"parts": [{"text": prompt}]}]}
                try:
                    response = requests.post(endpoint, headers=headers, json=data, timeout=4)
                    if response.status_code == 200:
                        desc = response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                    else:
                        desc = f"{user_text} argument {arg}"
                except Exception:
                    desc = f"{user_text} argument {arg}"
            else:
                desc = f"{user_text} argument {arg}"
            extra = LINUX_COMMANDS_NEED_FILE.get(user_text, '')
            if extra:
                suggestions.append((f"{user_text} {arg} {extra}", f"{desc} (needs {extra})"))
            else:
                suggestions.append((f"{user_text} {arg}", desc))

        # تخزين النتائج في الذاكرة المؤقتة
        save_to_cache(cache_key, suggestions)

        return suggestions

    matches = [cmd for cmd in LINUX_COMMANDS if cmd.startswith(user_text)]
    if matches:
        suggestions = []
        api_key = get_api_key()
        for cmd in matches:
            if api_key:
                endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
                headers = {"Content-Type": "application/json"}
                prompt = (
                    f"What does the Linux command '{cmd}' do? Answer in less than 10 words. Only return the description, nothing else."
                )
                data = {"contents": [{"parts": [{"text": prompt}]}]}
                try:
                    response = requests.post(endpoint, headers=headers, json=data, timeout=4)
                    if response.status_code == 200:
                        desc = response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                    else:
                        desc = f"{cmd} command"
                except Exception:
                    desc = f"{cmd} command"
            else:
                desc = f"{cmd} command"
            extra = LINUX_COMMANDS_NEED_FILE.get(cmd, '')
            if extra:
                desc = f"{desc} (needs {extra})"
            suggestions.append((cmd, desc))

        # تخزين النتائج في الذاكرة المؤقتة
        save_to_cache(cache_key, suggestions)

        return suggestions

    # fallback: Gemini API
    api_key = get_api_key()
    if not api_key:
        return []
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    prompt = (
        f"Instruction: {user_text}\n"
        "Suggest 5 alternative or more accurate Linux commands for this task, each with a short description. "
        "Return ONLY a JSON list of objects: [{\"cmd\": \"...\", \"desc\": \"...\"}, ...]. No explanations, just the JSON."
    )
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(endpoint, headers=headers, json=data)
    if response.status_code == 200:
        import json, re
        text = response.json()['candidates'][0]['content']['parts'][0]['text']
        # حاول التقاط قائمة JSON من الرد حتى لو كانت داخل نص
        try:
            # التقط أول قائمة تبدأ بـ [ وتنتهي بـ ]
            match = re.search(r'(\[.*?\])', text, re.DOTALL)
            if match:
                json_text = match.group(1)
            else:
                json_text = text
            suggestions = json.loads(json_text)
            result = [(s.get('cmd', str(s)), s.get('desc', '')) for s in suggestions]
            save_to_cache(cache_key, result)
            return result
        except Exception as e:
            # إذا فشل التحويل، أظهر الرد الخام للمستخدم (للتصحيح)
            print(f"[Gemini RAW Response]:\n{text}\n[Parsing error: {e}]")
            return []
    else:
        return []

def save_to_cache(key, suggestions):
    """
    تخزين الاقتراحات في الذاكرة المؤقتة مع وقت الإضافة
    """
    # إذا وصل حجم التخزين المؤقت للحد الأقصى، حذف أقدم عنصر
    if len(SUGGESTIONS_CACHE) >= MAX_CACHE_SIZE:
        oldest_key = min(SUGGESTIONS_CACHE.keys(), key=lambda k: SUGGESTIONS_CACHE[k]['timestamp'])
        SUGGESTIONS_CACHE.pop(oldest_key)

    # إضافة الاقتراحات الجديدة مع الوقت الحالي
    SUGGESTIONS_CACHE[key] = {
        'suggestions': suggestions,
        'timestamp': time.time()
    }
