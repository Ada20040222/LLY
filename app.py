import os
from flask import Flask, request, send_file
import speech_recognition as sr
from openai import OpenAI
from gtts import gTTS
from pydub import AudioSegment
import io

app = Flask(__name__)

# 🔑 填入妳的 DeepSeek API 金鑰
import os
DEEPSEEK_API_KEY = os.environ.get("OPENAI_API_KEY")

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1"
)

# 網頁首頁（測試雲端有沒有活著用）
@app.route('/')
def home():
    return "<h1>柳如煙的雲端大腦正在運行中！</h1>"

@app.route('/voice', methods=['POST'])
def voice_endpoint():
    try:
        raw_audio = request.data
        
        # 將 PCM 轉為標準 WAV
        audio_segment = AudioSegment(
            data=raw_audio,
            sample_width=2,
            frame_rate=16000,
            channels=1
        )
        
        wav_io = io.BytesIO()
        audio_segment.export(wav_io, format="wav")
        wav_io.seek(0)
        
        # 🎙️ 語音轉文字 (STT)
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_io) as source:
            audio_data = recognizer.record(source)
        
        try:
            user_text = recognizer.recognize_google(audio_data, language="zh-TW")
        except:
            user_text = "聽不清楚"

        if user_text == "聽不清楚":
            ai_response = "對不起，我剛才恍神了，可以請妳再說一遍嗎？"
        else:
            # 🧠 問 DeepSeek
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "妳是智慧語音助理柳如煙，請用繁體中文給出極為簡短、生活化、口語溫柔的回答，不超過30個字。"},
                    {"role": "user", "content": user_text}
                ],
                temperature=0.7,
                max_tokens=60
            )
            ai_response = response.choices[0].message.content
        
        print(f"User: {user_text} -> AI: {ai_response}")
        
        # 🔊 文字轉語音 (TTS) 
        tts = gTTS(text=ai_response, lang='zh-tw')
        mp3_io = io.BytesIO()
        tts.write_to_fp(mp3_io)
        mp3_io.seek(0)
        
        # 轉成 16000Hz WAV 純 PCM 串流給 ESP32 大喇叭
        output_audio = AudioSegment.from_file(mp3_io, format="mp3")
        output_audio = output_audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        final_pcm = output_audio.raw_data
        
        return send_file(io.BytesIO(final_pcm), mimetype="application/octet-stream")

    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)