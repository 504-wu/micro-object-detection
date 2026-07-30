import cv2
import numpy as np
import pandas as pd
import streamlit as st
import io
import sqlite3
from google import genai
from google.genai import types
from PIL import Image  

# 設定網頁標題與排版
st.set_page_config(page_title="物件及環境問題診斷系統", layout="wide")
st.title("🔍 物件及環境問題診斷系統 (micro_object_detection_system)")
st.write("不管是零件瑕疵、現場設備故障還是日常生活中的大小煩事，上傳 1~5 張照片並輸入你的問題，讓 Gemini 好好分析後給你參考。")

#設定 Gemini API 金鑰
gemini_key = st.sidebar.text_input("請輸入 Gemini API Key", type="password")

# 初始化 SQLite 資料庫 (加入關鍵字)
def init_db():
    conn = sqlite3.connect("defects.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filenames TEXT,
            keywords TEXT,
            issue_type TEXT,
            severity TEXT,
            solution TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def delete_record_by_id(record_id):
    conn = sqlite3.connect("defects.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

def save_to_sqlite(data):
    conn = sqlite3.connect("defects.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO records (filenames, keywords, issue_type, severity, solution)
        VALUES (?, ?, ?, ?, ?)
    ''', (data["照片"], data["關鍵字"], data["問題"], data["嚴重程度"], data["解決方案"]))
    conn.commit()
    conn.close()

# 網頁暫時儲存
if "generic_report_data" not in st.session_state:
    st.session_state.generic_report_data = []

# Gemini 多模態視覺分析 (讀取照片結合關鍵字)
def analyze_issue_with_gemini(api_key, pil_images, keywords):
    if not api_key:
        return {
            "type": "未提供 API Key",
            "severity": "None",
            "solution": "請於左側輸入 Gemini API Key 以啟動 AI 。"
        }
    try:
        client = genai.Client(api_key=api_key)
        
        # 建立 prompt，限制 AI 輸出格式
        prompt = f"""
        這是一個物件及環境問題診斷系統_專門提供一些些建議。
        使用者上傳照片，並提供簡單關鍵字：【{keywords}】。
        
        結合照片中的資訊與關鍵字，評估並回答以下三個項目（請嚴格遵守字數與格式）：
        
        1. 問題：簡短說明照片中出了什麼問題（例如：牆壁滲水、零件表面磨損、螢幕裂痕、衣物髒污、汽車擦傷）。
        2. 嚴重程度：只能從 [輕度, 中度, 重度] 這三個詞中選擇一個。
        3. 解決方案：請針對該問題與嚴重程度，提供一個簡易的修復方式或應對建議。字數必須嚴格限制在 20 到 30 字之間，不要贅字。
        
        請按照下列格式輸出，不要包含任何其他廢話或標籤：
        類型: [在此輸入問題]
        程度: [在此輸入輕度或中度或重度]
        方案: [在此輸入20-30字方案]
        """
        
        # 將提示與照片丟給 Gemini 分析
        contents = [prompt] + pil_images

        #設定使用Gemini順序，不行就下一個
        models_to_try = ['gemini-3.5-flash-lite', 'gemini-3.5-flash', 'gemini-3.5-pro']
        
        last_error = ""
        for model_name in models_to_try:
            try:
                # 呼叫目前順位的模型進行分析
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(temperature=0.4)
                )
                break  # 成功就跳出

            except Exception as e:
                last_error = str(e)
                continue
        
        text_res = response.text.strip()
        
        # 分析回傳的格式
        res_dict = {"type": "未知", "severity": "None", "solution": text_res}
        for line in text_res.split('\n'):
            if line.startswith("類型:"):
                res_dict["type"] = line.replace("類型:", "").strip()
            elif line.startswith("程度:"):
                res_dict["severity"] = line.replace("程度:", "").strip()
            elif line.startswith("方案:"):
                res_dict["solution"] = line.replace("方案:", "").strip()
                
        return res_dict

    except Exception as e:
        return {
        "type": "服務忙碌", 
        "severity": "未知", 
        "solution": f"所有 Gemini 備用模型目前皆處於高流量負載狀態，請稍後幾分鐘再試。錯誤訊息: {last_error}"
    }

# 網頁：選取並上傳照片
st.subheader("📸 Step 1：上傳照片 (至少1張，最多5張)")
uploaded_files = st.file_uploader(
    "可以選取單張，或複選最多 5 張照片：", 
    type=["jpg", "jpeg", "png"], 
    accept_multiple_files=True
)

if uploaded_files:
    num_files = len(uploaded_files)
    if num_files > 5:
        st.error(f"⚠️ 你選了 {num_files} 張照片，超過上限。給我重新選擇 1 到 5 張照片。")
    else:
        st.success(f"✅ 已成功插入 {num_files} 張照片！")
        
        # 顯示上傳縮圖
        cols = st.columns(min(num_files, 5))
        pil_images = []
        file_names_str = ", ".join([f.name for f in uploaded_files])
        
        for idx, f in enumerate(uploaded_files):
            # 轉 PIL Image 供 Gemini 讀取，並在網頁顯示
            img = Image.open(f)
            pil_images.append(img)
            with cols[idx]:
                st.image(img, caption=f.name, use_container_width=True)
                
        # 關鍵字輸入，提供給 Gemini 分析
        st.write("---")
        st.subheader("✍️ Step 2：提供關鍵字與問題描述")
        user_keywords = st.text_input(
            "請輸入跟這張照片問題的關鍵字（例如：機車外殼刮傷、辦公椅輪子卡死、廚房漏水、晶片刮痕等）：",
            placeholder="輸入關鍵字能讓判斷得更明確..."
        )
        
        # 執行分析並將結果加入報表
        st.write("---")
        if st.button("🚀 啟動 Gemini 全面評斷（分析並加入報表）"):
            if not user_keywords.strip():
                st.warning("ℹ️ 建議輸入一些關鍵字，能更明確的分析！")
            
            with st.spinner("Gemini 正在多張照片比對與提供分析中..."):
                ai_result = analyze_issue_with_gemini(gemini_key, pil_images, user_keywords)
            
            # 建立資料
            new_data = {
                "照片": file_names_str,
                "關鍵字": user_keywords if user_keywords.strip() else "沒有",
                "問題": ai_result["type"],
                "嚴重程度": ai_result["severity"],
                "解決方案": ai_result["solution"]
            }
            
            # 檢查是否重複
            if not any(d['照片'] == file_names_str for d in st.session_state.generic_report_data):
                st.session_state.generic_report_data.append(new_data)
                save_to_sqlite(new_data)
                st.toast("✅ 分析完成！已加入資料庫與報表。", icon="🤖")
            else:
                st.warning("ℹ️ 這些照片的分析結果之前已處理並記錄過，不要再重複給了。")

# 分析報表與 Excel 下載
if st.session_state.generic_report_data:
    st.write("---")
    st.subheader("📋 本次分析報表")
    
    df = pd.DataFrame(st.session_state.generic_report_data)
    st.dataframe(df, use_container_width=True)
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='綜合分析報告')
    
    st.download_button(
        label="📥 匯出並下載 Excel 報表",
        data=buffer.getvalue(),
        file_name="問題分析報告.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    if st.button("🗑️ 清空目前網頁暫存"):
        st.session_state.generic_report_data = []
        st.rerun()

# 7. 查看資料庫過往總紀錄與後台管理
if st.sidebar.checkbox("顯示資料庫全部紀錄"):
    st.write("---")
    st.subheader("🗄️ 過往分析總數據庫")
    
    conn = sqlite3.connect("defects.db")
    db_df = pd.read_sql_query("SELECT * FROM records ORDER BY timestamp DESC", conn)
    conn.close()
    
    if not db_df.empty:
        st.dataframe(db_df, use_container_width=True)
        
        # 匯出完整過往 Excel 紀錄
        history_buffer = io.BytesIO()
        with pd.ExcelWriter(history_buffer, engine='openpyxl') as writer:
            db_df.to_excel(writer, index=False, sheet_name='過往總紀錄')
        
        st.download_button(
            label="📥 匯出全過往 Excel 紀錄",
            data=history_buffer.getvalue(),
            file_name="過往分析總報告.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        # 刪除功能
        st.write("---")
        st.write("🗑️ **管理後台：刪除之前紀錄**")
        id_options = [f"ID {row['id']} - 關鍵字: {row['keywords']} ({row['issue_type']})" for _, row in db_df.iterrows()]
        selected_option = st.selectbox("請選取欲刪除的之前紀錄", id_options)
        
        if st.button("🔴 確認刪除此筆資料"):
            selected_id = int(selected_option.split(" ")[1])
            delete_record_by_id(selected_id)
            st.toast(f"🗑️ 已成功刪除資料 ID {selected_id}！", icon="❌")
            st.rerun()
    else:
        st.info("ℹ️ 資料庫目前尚無過往數據。")
