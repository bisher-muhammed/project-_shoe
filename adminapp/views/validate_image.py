from PIL import Image
def validate_image(image_file):
    try:
        image_file.seek(0)
        img = Image.open(image_file)
        img.verify()

        image_file.seek(0)
        return img.format.lower()
    except Exception:
        return None