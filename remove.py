# Save as clean_logo_backgrounds.py
from PIL import Image
import os

def remove_white_background(image_path, output_path, threshold=240):
    img = Image.open(image_path).convert("RGBA")
    datas = img.getdata()
    
    new_data = []
    for item in datas:
        # Detect near-white background
        if item[0] > threshold and item[1] > threshold and item[2] > threshold:
            new_data.append((255, 255, 255, 0))  # transparent
        else:
            new_data.append(item)
    
    img.putdata(new_data)

    # Save as WEBP with transparency
    img.save(output_path, "WEBP", quality=90)

# Folders
input_folder = "static/images/car_logo_webp/"
output_folder = "static/images/car_logo_webp_cleaned/"

# Create output folder if it does not exist
os.makedirs(output_folder, exist_ok=True)

# Process all .webp logos
for filename in os.listdir(input_folder):
    if filename.lower().endswith(".webp"):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, filename)  # SAME NAME, NEW FOLDER
        
        try:
            remove_white_background(input_path, output_path)
            print(f"✓ Cleaned {filename}")
        except Exception as e:
            print(f"✗ Failed {filename}: {e}")
print("Background removal complete.")