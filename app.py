import os
from flask import Flask, request, send_file
import speech_recognition as sr
from openai import OpenAI
from gtts import gTTS
import io
import wave

app = Flask(__name__)
DEEPSEEK_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")

@app.route('/voice', methods=['POST'])
def voice_endpoint():
    try:
        # 接收 ESP32 的 16kHz PCM 原始數據
        raw_audio = request.data
        
        # 1. 調整錄音讀取：把 PCM 包裝成 WAV 給 Google 辨識
        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(raw_audio)
        wav_io.seek(0)
        
        # 2. 提升辨識率：增加辨識的敏感度
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300  # 降低能量門檻，讓它更容易聽到小聲說話
        with sr.AudioFile(wav_io) as source:
            audio_data = recognizer.record(source)
        
        try:
            user_text = recognizer.recognize_google(audio_data, language="zh-TW")
            print(f"辨識結果: {user_text}")
        except:
            user_text = "沒聽清楚"

        # 3. 取得 AI 回覆
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "妳是柳如煙，請用繁體中文回答。講話速度要慢，多用逗號與語助詞，內容簡短溫柔。"},
                {"role": "user", "content": user_text}
            ],
            temperature=0.7
        )
        ai_response = response.choices[0].message.content
        
        # 4. 解決講太快：增加斷句與語助詞 (這是簡單的緩解法)
        slow_response = ai_response.replace("。", "......，").replace("，", "......，")
        
        # 5. 生成語音
        tts = gTTS(text=slow_response, lang='zh-tw', slow=True) # 關鍵：slow=True
        mp3_io = io.BytesIO()
        tts.write_to_fp(mp3_io)
        mp3_io.seek(0)
        
        # 這裡會回傳給 ESP32 播放
        return send_file(mp3_io, mimetype="audio/mpeg")

    except Exception as e:
        print(f"錯誤: {e}")
        return "Error", 500
