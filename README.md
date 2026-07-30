# 物件及環境問題診斷系統(micro_object_detection_system)
整合視覺比對及語言模型，並建立雲端資料庫，可以使用不同裝置上傳照片後，自動判定問題並提供意見，然後一鍵整理出 Excel 的通用型判斷工具。

# 實作重點
- **AI整合**：串接 Google GenAI SDK，利用 Gemini 模型，達成輸入 1~5 張照片與關鍵字進行評估，提供建議給使用者，使處理多種的難題時，有個參考。
- **容錯與備援機制**：使用 Model Routing，當主要模型（Gemini 3.5 Flash-lite）遇到流量過大發生錯誤時，系統會自動切換至備用模型（Gemini 3.5 Flash / 3.5 Pro）確保系統高可用性。
- **影像邊緣前處理**：基於 OpenCV 影像預處理，透過灰階化、高斯模糊與直方圖均衡化提升照片對比度，並利用輪廓偵測進行環境雜訊判定。
- **雲端數據自動化**：打造輕量化本機數據庫，結合 Streamlit 狀態管理，實現數據的暫存，並透過 Pandas 與 Openpyxl 能一鍵匯出 Excel 報表與過往數據，也提供刪除功能。
- **無伺服器部署**：結合 GitHub 與 Streamlit Community Cloud，擺脫架站限制，實現跨裝置多元使用。

# 使用工具
- Python 3.x (OpenCV-headless, Pandas, Openpyxl, Pillow, Sqlite3)
- Google GenAI SDK (Gemini-3.5-Flash-lite / Gemini-3.5-Flash / Gemini-3.5-Pro)
- GitHub (Version Control)
- Streamlit Community Cloud (Serverless Deployment / CI/CD)
# 專案結構
- requirements.txt：雲端環境依賴套件設定檔，採用 opencv-python-headless 確保伺服器在無圖片介面下穩定執行不閃退。
- detection.py：影像前處理、備援 AI 串接、SQLite 讀寫及互動式網頁與 Excel 導出的一體化程式。

# 執行成果




