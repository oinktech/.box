from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import lzma
import os
import struct
import zipfile
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# 壓縮邏輯
def create_box(files):
    compressed_data = BytesIO()
    with compressed_data:
        compressed_data.write(struct.pack('I', len(files)))
        for file in files:
            filename = file.filename
            file_data = file.read()
            compressed = lzma.compress(file_data)
            
            compressed_data.write(struct.pack('I', len(filename)))
            compressed_data.write(filename.encode('utf-8'))
            compressed_data.write(struct.pack('I', len(compressed)))
            compressed_data.write(compressed)
    
    compressed_data.seek(0)
    return compressed_data

# 解壓縮邏輯
def extract_box(file):
    extracted_files = []
    with file:
        num_files = struct.unpack('I', file.read(4))[0]
        for _ in range(num_files):
            filename_length = struct.unpack('I', file.read(4))[0]
            filename = file.read(filename_length).decode('utf-8')
            compressed_size = struct.unpack('I', file.read(4))[0]
            compressed_data = file.read(compressed_size)
            decompressed_data = lzma.decompress(compressed_data)
            
            extracted_files.append((filename, decompressed_data))
    
    return extracted_files

# 使用 zipfile 壓縮
def create_zip(files):
    zip_data = BytesIO()
    with zipfile.ZipFile(zip_data, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file in files:
            zip_file.writestr(file.filename, file.read())
    zip_data.seek(0)
    return zip_data

# 壓縮頁面
@app.route('/')
def index():
    return render_template('index.html')

# 解壓縮頁面
@app.route('/decompress')
def decompress_page():
    return render_template('decompress.html')

# 比較頁面
@app.route('/compare')
def compare_page():
    return render_template('compare.html')

# 處理壓縮請求
@app.route('/upload', methods=['POST'])
def upload_files():
    if 'file' not in request.files:
        flash('未選擇任何文件！')
        return redirect(request.url)
    
    files = request.files.getlist('file')
    if not files:
        flash('請選擇文件進行壓縮！')
        return redirect(request.url)
    
    try:
        first_filename = os.path.splitext(files[0].filename)[0]
        
        compressed_data = create_box(files)
        box_filename = f"{first_filename}.box"
        
        return send_file(compressed_data, as_attachment=True, download_name=box_filename)
    except Exception as e:
        flash(f'壓縮過程中出錯：{str(e)}')
        return redirect(url_for('index'))

# 處理解壓縮請求
@app.route('/extract', methods=['POST'])
def extract_files():
    if 'file' not in request.files:
        flash('未選擇任何文件！')
        return redirect(request.url)
    
    file = request.files['file']
    try:
        extracted_files = extract_box(file)
        return render_template('extracted.html', files=extracted_files)
    except Exception as e:
        flash(f'解壓縮過程中出錯：{str(e)}')
        return redirect(url_for('decompress_page'))

# 處理比較請求
@app.route('/compare/upload', methods=['POST'])
def compare_files():
    if 'file' not in request.files:
        flash('未選擇任何文件！')
        return redirect(request.url)

    files = request.files.getlist('file')
    if not files:
        flash('請選擇文件進行比較！')
        return redirect(request.url)

    try:
        # 計算 .box 的大小
        box_data = create_box(files)
        box_size = len(box_data.getvalue())

        # 計算 .zip 的大小
        zip_data = create_zip(files)
        zip_size = len(zip_data.getvalue())

        return render_template('comparison_result.html', box_size=box_size, zip_size=zip_size)
    except Exception as e:
        flash(f'比較過程中出錯：{str(e)}')
        return redirect(url_for('compare_page'))

if __name__ == '__main__':
    app.run(debug=True,port=10000, host='0.0.0.0')
