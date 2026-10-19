/** Folder picks (especially on Windows) often leave File.type empty; MIME alone is unreliable. */
const IMAGE_EXT_RE = /\.(jpe?g|png|bmp|gif|webp|tiff?|heic|heif)$/i;

export function isLikelyImageFile(f) {
  const t = f?.type || "";
  if (t.startsWith("image/")) return true;
  return IMAGE_EXT_RE.test(f?.name || "");
}
