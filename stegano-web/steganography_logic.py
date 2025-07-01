from PIL import Image
import numpy as np

# Definisikan pemetaan rotasi channel yang akan digunakan.
# 5 rotasi untuk data (base-5), 1 untuk penanda akhir.
ROTATIONS = {
    0: (0, 1, 2),  # Digit 0
    1: (0, 2, 1),  # Digit 1
    2: (1, 0, 2),  # Digit 2
    3: (1, 2, 0),  # Digit 3
    4: (2, 0, 1),  # Digit 4
    5: (2, 1, 0),  # Penanda Akhir (Terminator)
}

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

def encode(image_path, secret_message):
    """
    Menyembunyikan pesan ke dalam gambar menggunakan metode rotasi channel.

    Args:
        image_path (str): Path menuju file gambar asli.
        secret_message (str): Pesan rahasia yang ingin disembunyikan.

    Returns:
        PIL.Image.Image: Objek gambar baru yang berisi pesan.

    Raises:
        ValueError: Jika pesan terlalu panjang atau file tidak ditemukan.
    """
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
    except FileNotFoundError:
        raise ValueError(f"File gambar tidak ditemukan di path: {image_path}")
    except Exception as e:
        raise ValueError(f"Terjadi kesalahan saat encoding: {e}")

def decode(original_image_path, stego_image_path):
    """
    Mengungkap pesan dari gambar stego dengan membandingkannya dengan gambar asli.

    Args:
        original_image_path (str): Path menuju file gambar asli.
        stego_image_path (str): Path menuju file gambar yang berisi pesan.

    Returns:
        str: Pesan rahasia yang berhasil diungkap.

    Raises:
        ValueError: Jika gambar tidak cocok, file tidak ditemukan, atau terjadi error lain.
    """
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
            
            # Cari tahu rotasi mana yang diaplikasikan
            rot_id_found = -1
            for rot_id, rotation_map in ROTATIONS.items():
                permuted_pixel = original_pixel[list(rotation_map)]
                if np.array_equal(permuted_pixel, stego_pixel):
                    if rot_id == 5: # Penanda akhir
                        rot_id_found = rot_id
                        break 
                    base5_digits.append(rot_id)
                    rot_id_found = rot_id
                    break
            
            if rot_id_found == 5:
                break
                
        # Konversi kembali urutan digit base-5 ke pesan asli
        decoded_message = ""
        for i in range(0, len(base5_digits), 4):
            chunk = base5_digits[i:i+4]
            if len(chunk) < 4:
                break
            
            base5_str = "".join(map(str, chunk))
            ascii_val = base5_to_int(base5_str)
            decoded_message += chr(ascii_val)
                
        if not decoded_message:
            return "Pesan tidak ditemukan atau file rusak (penanda akhir tidak ada)."
        return decoded_message

    except FileNotFoundError:
        raise ValueError("Salah satu file gambar tidak ditemukan.")
    except Exception as e:
        raise ValueError(f"Terjadi kesalahan saat decoding: {e}")