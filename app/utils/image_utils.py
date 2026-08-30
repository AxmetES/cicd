import io

from PIL import Image


def process_photo(file_data) -> bytes:
    image = Image.open(file_data)
    image = image.convert("RGB")
    image.thumbnail((500, 500))
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=85)
    output.seek(0)
    return output