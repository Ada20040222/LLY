import os
from flask import Flask, request, send_file
import speech_recognition as sr
from openai import OpenAI
from gtts import gTTS
import io
import wave

app = Flask(__name__)
# 確保使用環境變數中的 API Key
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), base_url="https://api.deepseek.com/v1")

@app.route('/')
def home():
    return "柳如煙語音服務運作中"

@app.route('/voice', methods=['POST'])
def voice_endpoint():
    try:
        raw_audio = request.data
        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(raw_audio)
        wav_io.seek(0)
        
        # 1. 聽力調校：提高辨識靈敏度
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 200 # 數字越小越靈敏
        with sr.AudioFile(wav_io) as source:
            audio_data = recognizer.record(source)
        
        user_text = recognizer.recognize_google(audio_data, language="zh-TW")
        print(f"使用者說: {user_text}")

        # 2. 回答優化：強制溫柔語速
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "妳是溫柔的柳如煙，回答請簡短（20字內），多用緩慢的語氣詞。"},
                {"role": "user", "content": user_text}
            ]
        )
        ai_text = response.choices[0].message.content
        
        # 3. 語速優化：使用 gTTS 的 slow=True
        tts = gTTS(text=ai_text, lang='zh-tw', slow=True) 
        mp3_io = io.BytesIO()
        tts.write_to_fp(mp3_io)
        mp3_io.seek(0)
        
        return send_file(mp3_io, mimetype="audio/mpeg")

    except Exception as e:
        return str(e), 500
