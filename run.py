import os
import sys
import webbrowser
from threading import Timer
from app import app

def open_browser():
    webbrowser.open('http://127.0.0.1:5000/')

if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        # 如果是打包后的exe运行
        template_folder = os.path.join(sys._MEIPASS, 'templates')
        static_folder = os.path.join(sys._MEIPASS, 'static')
        fonts_folder = os.path.join(sys._MEIPASS, 'fonts')
        uploads_folder = os.path.join(os.path.dirname(sys.executable), 'uploads')
    else:
        # 如果是直接运行python脚本
        template_folder = 'templates'
        static_folder = 'static'
        fonts_folder = 'fonts'
        uploads_folder = 'uploads'

    # 确保上传文件夹存在
    if not os.path.exists(uploads_folder):
        os.makedirs(uploads_folder)

    # 设置自动打开浏览器
    Timer(1.5, open_browser).start()
    
    # 运行Flask应用
    app.run(debug=False, port=5000) 