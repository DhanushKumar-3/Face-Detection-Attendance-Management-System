import os
import face_recognition
from PIL import Image
import numpy as np
import json
from datetime import datetime, timezone

ALLOWED_EXT = {'png', 'jpg', 'jpeg'}


def allowed_file(filename):
    """Check file extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def safe_load_to_rgb_array(filepath):
    """Load and convert ANY image to RGB uint8 numpy array."""
    try:
        img = Image.open(filepath)
        img = img.convert("RGB")
        arr = np.array(img).astype("uint8")
        return arr
    except Exception as e:
        print("Error loading image:", e)
        return None


def get_face_encodings_from_image_file(filepath):
    """
    Fully safe version:
    - Loads using PIL
    - Converts to RGB
    - Ensures uint8
    - Ensures C-contiguous memory
    """
    print("---- DEBUG: Loading image ----")

    try:
        pil_img = Image.open(filepath)
        print("Original mode:", pil_img.mode)
        pil_img = pil_img.convert("RGB")
        print("Converted mode:", pil_img.mode)
    except Exception as e:
        print("PIL loading error:", e)
        return []

    # Convert to proper numpy uint8 contiguous array
    try:
        arr = np.asarray(pil_img, dtype=np.uint8)
        arr = np.ascontiguousarray(arr)
        print("Array shape:", arr.shape, "dtype:", arr.dtype)
    except Exception as e:
        print("Array conversion error:", e)
        return []

    if arr.ndim != 3 or arr.shape[2] != 3:
        print("Invalid image shape:", arr.shape)
        return []

    try:
        # ALWAYS detect face locations first
        locations = face_recognition.face_locations(arr, model="hog")
        print("Face locations:", locations)

        encs = face_recognition.face_encodings(arr, known_face_locations=locations)
        print("Encodings:", len(encs))

        return [e.tolist() for e in encs]

    except Exception as e:
        print("Final encoding error:", e)
        return []





def get_face_encodings_from_pil_image(pil_image):
    try:
        # Convert to raw RGB manually (bypasses all PIL stride bugs)
        img = pil_image.convert("RGB")
        w, h = img.size
        rgb_bytes = img.tobytes("raw", "RGB")  # FULL force raw decode
        arr = np.frombuffer(rgb_bytes, dtype=np.uint8)
        arr = arr.reshape((h, w, 3))

        # Make sure fully contiguous
        arr = np.ascontiguousarray(arr)

    except Exception as e:
        print("Manual reconstruction error:", e)
        return []

    try:
        face_locations = face_recognition.face_locations(arr, model="hog")

        if not face_locations:
            print("No face found in this frame")
            return []

        encs = face_recognition.face_encodings(arr, known_face_locations=face_locations)
        return [e.tolist() for e in encs]

    except Exception as e:
        print("Face encoding PIL error:", e)
        return []






def compare_face_to_user_encodings(user_encodings, face_encoding, tolerance=0.6):
    """Compare a face encoding to stored encodings."""
    import numpy as np

    if isinstance(face_encoding, list):
        face_encoding = np.array(face_encoding)

    distances = []
    for enc in user_encodings:
        enc = np.array(enc)
        d = np.linalg.norm(enc - face_encoding)
        distances.append(d)

    if not distances:
        return None, None

    best_idx = int(np.argmin(distances))
    best_distance = float(distances[best_idx])

    matched = best_distance <= tolerance
    return best_distance, (best_idx if matched else None)


def load_all_known_users(db_session, User):
    """Return all users with decoded face encodings."""
    users = User.query.all()
    output = []
    for u in users:
        try:
            encs = json.loads(u.encodings_json) if u.encodings_json else []
        except:
            encs = []
        output.append((u, encs))
    return output


def encoding_to_json(enc):
    return json.dumps(enc)



def parse_date_utc(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
