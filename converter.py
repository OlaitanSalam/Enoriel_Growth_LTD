import os
from PIL import Image

# Input folder: your original images
INPUT_FOLDER = "static/input_images"

# Output folder: converted WebP images
OUTPUT_FOLDER = "static/images/car_logo_webp"

# Create output folder if it doesn’t exist
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Allowed source image formats
VALID_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".tiff")

for filename in os.listdir(INPUT_FOLDER):
    file_path = os.path.join(INPUT_FOLDER, filename)

    # Skip directories
    if not os.path.isfile(file_path):
        continue

    # Skip already webp files
    if filename.lower().endswith(".webp"):
        print(f"Skipping (already webp): {filename}")
        continue

    # Skip unsupported formats
    if not filename.lower().endswith(VALID_EXTENSIONS):
        print(f"Skipping (unsupported type): {filename}")
        continue

    # Open and convert image
    img = Image.open(file_path).convert("RGB")

    # Generate new filename with .webp extension
    new_filename = os.path.splitext(filename)[0] + ".webp"
    new_path = os.path.join(OUTPUT_FOLDER, new_filename)

    # Save as WebP
    img.save(new_path, "webp", quality=85)

    print(f"Converted → {new_filename}")

print("\n🎉 Conversion complete!")
