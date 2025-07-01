import os
import io
from flask import Flask, request, render_template, send_from_directory, flash, redirect, url_for
from werkzeug.utils import secure_filename
from PIL import Image
import numpy as np
import base64
import mimetypes

# Konfigurasi aplikasi Flask
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png'} # Format file yang didukung hanya png untuk menghindari masalah dengan format lossy seperti JPEG.
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'kunci-rotasi-channel-yang-benar'

# Definisikan pemetaan rotasi channel dan kebalikannya.
# 5 rotasi untuk data (base-5), 1 untuk penanda akhir.
ROTATIONS = {
    0: (0, 1, 2),  # Digit 0
    1: (0, 2, 1),  # Digit 1
    2: (1, 0, 2),  # Digit 2
    3: (1, 2, 0),  # Digit 3
    4: (2, 0, 1),  # Digit 4
    5: (2, 1, 0),  # Penanda Akhir (Terminator)
}

def allowed_file(filename):
    """Mengecek apakah ekstensi file diizinkan."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def int_to_base5(n):
    """Mengubah integer (ASCII) menjadi 4 digit string base-5."""
    if n == 0:
        return "0000"
    nums = []
    while n:
        n, r = divmod(n, 5)
        nums.append(str(r))
    base5_str = ''.join(reversed(nums))
    return base5_str.zfill(4)

def base5_to_int(s):
    """Mengubah string base-5 menjadi integer (ASCII)."""
    return int(s, 5)

def encode_rotation_revised(image_path, secret_message):
    """Fungsi utama untuk menyembunyikan pesan ke dalam gambar."""
    try:
        img = Image.open(image_path).convert('RGB')
        data = np.array(img)
        
        # Validasi kapasitas pesan
        max_chars = (data.shape[0] * data.shape[1] - 1) // 4
        if len(secret_message) > max_chars:
            raise ValueError(f"Pesan terlalu panjang. Maksimal {max_chars} karakter.")

        # Konversi seluruh pesan menjadi urutan digit base-5
        base5_digits = []
        for char in secret_message:
            ascii_val = ord(char)
            base5_str = int_to_base5(ascii_val)
            base5_digits.extend([int(d) for d in base5_str])

        flat_data = data.reshape(-1, 3)
        
        # Terapkan rotasi channel untuk setiap digit pesan
        for i, digit in enumerate(base5_digits):
            pixel = flat_data[i].copy()
            rotation_map = ROTATIONS[digit]
            flat_data[i] = pixel[list(rotation_map)]
            
        # Terapkan rotasi penanda akhir setelah pesan selesai
        terminator_index = len(base5_digits)
        pixel = flat_data[terminator_index].copy()
        flat_data[terminator_index] = pixel[list(ROTATIONS[5])]

        new_data = flat_data.reshape(data.shape)
        new_img = Image.fromarray(new_data.astype('uint8'), 'RGB')
        return new_img

    except Exception as e:
        flash(f"Error saat encoding: {e}")
        return None

def decode_rotation_revised(original_image_path, stego_image_path):
    """Fungsi utama untuk mengungkap pesan dengan membandingkan dua gambar."""
    try:
        original_img = Image.open(original_image_path).convert('RGB')
        stego_img = Image.open(stego_image_path).convert('RGB')

        if original_img.size != stego_img.size:
            raise ValueError("Ukuran gambar asli dan stego tidak cocok.")

        original_data = np.array(original_img).reshape(-1, 3)
        stego_data = np.array(stego_img).reshape(-1, 3)
        
        # Ekstrak digit base-5 dengan membandingkan piksel
        base5_digits = []
        for i in range(len(original_data)):
            original_pixel = original_data[i]
            stego_pixel = stego_data[i]
            
            if np.array_equal(original_pixel, stego_pixel):
                base5_digits.append(0)
                continue

            # Cari rotasi mana yang cocok
            for rot_id, rotation_map in ROTATIONS.items():
                permuted_pixel = original_pixel[list(rotation_map)]
                if np.array_equal(permuted_pixel, stego_pixel):
                    if rot_id == 5:
                        break 
                    base5_digits.append(rot_id)
                    break
            if 'rot_id' in locals() and rot_id == 5:
                break
                
        # Konversi kembali urutan digit base-5 ke pesan asli
        decoded_message = ""
        for i in range(0, len(base5_digits), 4):
            chunk = base5_digits[i:i+4]
            if len(chunk) < 4:
                break
            
            base5_str = "".join(map(str, chunk))
            try:
                ascii_val = base5_to_int(base5_str)
                decoded_message += chr(ascii_val)
            except:
                pass
                
        return decoded_message if decoded_message else "Pesan tidak ditemukan atau file rusak."

    except Exception as e:
        flash(f"Error saat decoding: {e}")
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    """Mengatur routing utama dan logika form."""
    if request.method == 'POST':
        action = request.form.get('action')
        
        # Logika untuk proses encode
        if action == 'encode':
            if 'file' not in request.files or not request.form.get('secret_message'):
                flash('Pilih file gambar (.png) dan isi pesan rahasia.')
                return redirect(request.url)
            file = request.files['file']
            message = request.form['secret_message']
            if file.filename == '' :
                flash('Tidak ada file yang dipilih.')
                return redirect(request.url)
            if file and allowed_file(file.filename):
                file_content = file.read()
                encoded_image = encode_rotation_revised(file.stream, message)
                if encoded_image:

                    img_io = io.BytesIO()
                    encoded_image.save(img_io, 'PNG')
                    img_io.seek(0)
                    
                    # Konversi ke base64 untuk dikirim ke frontend
                    original_base64 = base64.b64encode(file_content).decode()
                    encoded_base64 = base64.b64encode(img_io.getvalue()).decode()

                    mime_type = mimetypes.guess_type(file.filename)[0] or 'image/png'
                    original_image = f"data:{mime_type};base64,{original_base64}"
                    encoded_image = f"data:{mime_type};base64,{encoded_base64}"
                    return render_template('result.html', original_image=original_image, encoded_image=encoded_image)
                return redirect(request.url)
            else:
                flash('File tidak valid! Harap gunakan format .png')
                return redirect(request.url)

        # Logika untuk proses decode
        elif action == 'decode':
            if 'original_file' not in request.files or 'stego_file' not in request.files:
                flash('Pilih gambar asli dan gambar stego untuk decode.')
                return redirect(request.url)
            original_file = request.files['original_file']
            stego_file = request.files['stego_file']
            if original_file.filename == '' or stego_file.filename == '':
                flash('Pilih kedua gambar untuk decode.')
                return redirect(request.url)
            if allowed_file(original_file.filename) and allowed_file(stego_file.filename):
                decoded_message = decode_rotation_revised(original_file.stream, stego_file.stream)
                return render_template('result.html', decoded_message=decoded_message)
            else:
                flash('File tidak valid! Harap gunakan format .png untuk kedua file.')
                return redirect(request.url)

    return render_template('index.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Menyajikan file yang telah diupload."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    # Membuat folder 'uploads' jika belum ada
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)