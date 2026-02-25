"""
NautiCAI — Visibility enhancement pipeline.
"""
import cv2
import numpy as np
from PIL import Image, ImageEnhance


def pil_to_cv(img):
    return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)


def cv_to_pil(arr):
    return Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))


def apply_clahe(bgr, clip=3.0, grid=8):
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=clip, tileGridSize=(grid, grid)).apply(l)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)


def apply_green_water(bgr, s=0.6):
    o = bgr.astype(np.float32)
    o[:, :, 1] = np.clip(o[:, :, 1] * (1 + 0.4 * s), 0, 255)
    o[:, :, 0] = np.clip(o[:, :, 0] * (1 - 0.3 * s), 0, 255)
    o[:, :, 2] = np.clip(o[:, :, 2] * (1 + 0.15 * s), 0, 255)
    return o.astype(np.uint8)


def apply_turbidity(bgr, level=0.4):
    if level < 0.01:
        return bgr
    bl = cv2.GaussianBlur(bgr, (0, 0), sigmaX=level * 12)
    sim = cv2.addWeighted(bgr, 1 - level * 0.7, bl, level * 0.7, 0)
    t = sim.astype(np.float32)
    t[:, :, 1] = np.clip(t[:, :, 1] * (1 + level * 0.35), 0, 255)
    t[:, :, 0] = np.clip(t[:, :, 0] * (1 - level * 0.2), 0, 255)
    t[:, :, 2] = np.clip(t[:, :, 2] * (1 - level * 0.3), 0, 255)
    return np.clip(t * (1 - level * 0.25), 0, 255).astype(np.uint8)


def apply_turbidity_correction(bgr, level=0.4):
    o = bgr.astype(np.float32)
    o[:, :, 0] = np.clip(o[:, :, 0] / max(0.01, 1 - level * 0.2), 0, 255)
    o[:, :, 1] = np.clip(o[:, :, 1] / max(0.01, 1 + level * 0.35), 0, 255)
    o[:, :, 2] = np.clip(o[:, :, 2] / max(0.01, 1 - level * 0.3), 0, 255)
    return np.clip(o / max(0.01, 1 - level * 0.25), 0, 255).astype(np.uint8)


def apply_edge_estimator(bgr):
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    ec = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    ec[:, :, 0] = 0
    ec[:, :, 2] = 0
    ec[:, :, 1] = edges
    return cv2.addWeighted(bgr, 0.75, ec, 0.8, 0)


def apply_marine_snow(pil_img, intensity=0.5):
    img_array = np.array(pil_img)
    num_particles = int(300 * intensity)
    for _ in range(num_particles):
        x = np.random.randint(0, img_array.shape[1])
        y = np.random.randint(0, img_array.shape[0])
        radius = np.random.randint(1, 4)
        brightness = np.random.randint(150, 255)
        cv2.circle(img_array, (x, y), radius, (brightness, brightness, brightness), -1)
    return Image.fromarray(img_array)


def full_enhance(pil_img, use_clahe=True, use_green=True, turb_in=0.0,
                 corr_turb=True, use_edge=False, clahe_clip=3.0, marine_snow=False):
    bgr = pil_to_cv(pil_img)
    if turb_in > 0.01:
        bgr = apply_turbidity(bgr, turb_in)
    if corr_turb and turb_in > 0.01:
        bgr = apply_turbidity_correction(bgr, turb_in * 0.85)
    if use_green:
        bgr = apply_green_water(bgr)
    if use_clahe:
        bgr = apply_clahe(bgr, clip=clahe_clip)
    if use_edge:
        bgr = apply_edge_estimator(bgr)
    result = cv_to_pil(bgr)
    if marine_snow:
        result = apply_marine_snow(result, intensity=0.5)
    return result
