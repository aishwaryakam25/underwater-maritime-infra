import axios from "axios";
import { getApiBaseUrl } from "./apiConfig";

const _base = getApiBaseUrl();
const API = axios.create(_base ? { baseURL: _base } : {});

async function parseBlobError(blob) {
  const text = await blob.text();
  try {
    const j = JSON.parse(text);
    if (Array.isArray(j.detail))
      return j.detail.map((x) => (typeof x === "string" ? x : x.msg || JSON.stringify(x))).join("; ");
    if (typeof j.detail === "string") return j.detail;
    return j.message || text.slice(0, 400);
  } catch {
    return text.slice(0, 400) || "Request failed";
  }
}

async function blobAsPdfOrThrow(blob, status) {
  if (!blob?.size) throw new Error(status ? `Empty response (${status})` : "Empty PDF response");
  const head = await blob.slice(0, Math.min(8, blob.size)).text();
  if (head.startsWith("%PDF")) return blob;
  throw new Error(await parseBlobError(blob));
}

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export const getHealth = async () => (await API.get("/api/health")).data;

/** Active model key + official 19 defect names + archive category names */
export const getModelClasses = async () => (await API.get("/api/model/classes")).data;
export const runDetection = async (file, params) => {
  const fd = new FormData();
  fd.append("file", file);
  Object.entries(params || {}).forEach(([k, v]) => fd.append(k, v));

  const res = await API.post("/api/detect", fd, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 0,
  });
  return res.data;
};

/** Side-scan sonar branch (`/api/sonar/analyze`) — uses same base URL as main detection API */
export const runSonarAnalyze = async (file, confidence_threshold = 0.25) => {
  const fd = new FormData();
  fd.append("file", file);
  const res = await API.post(`/api/sonar/analyze?confidence_threshold=${encodeURIComponent(confidence_threshold)}`, fd, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 0,
  });
  return res.data;
};

/** Professional sonar PDF (`/api/sonar/report/pdf`) */
export const downloadSonarReportPdf = async (files, results, { vessel_name = "", inspector = "NautiCAI AutoScan v1.0", inspection_mode = "General Inspection" } = {}) => {
  const fd = new FormData();
  fd.append("results_json", JSON.stringify(results));
  fd.append("vessel_name", vessel_name);
  fd.append("inspector", inspector);
  fd.append("inspection_mode", inspection_mode);
  (files || []).forEach((f) => fd.append("files", f));
  try {
    const res = await API.post("/api/sonar/report/pdf", fd, {
      headers: { "Content-Type": "multipart/form-data" },
      responseType: "blob",
      timeout: 0,
    });
    const blob = await blobAsPdfOrThrow(res.data, res.status);
    triggerDownload(blob, `NautiCAI_Sonar_Report_${new Date().toISOString().slice(0, 10)}.pdf`);
  } catch (e) {
    if (e.response?.data instanceof Blob) throw new Error(await parseBlobError(e.response.data));
    throw e;
  }
};

export const runEnhance = async (file, params) => {
  const fd = new FormData();
  fd.append("file", file);
  Object.entries(params || {}).forEach(([k, v]) => fd.append(k, v));

  const res = await API.post("/api/enhance", fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
};

export const downloadPDF = async (file, params) => {
  const fd = new FormData();
  fd.append("file", file);
  Object.entries(params || {}).forEach(([k, v]) => fd.append(k, v));

  try {
    const res = await API.post("/api/report/pdf", fd, {
      headers: { "Content-Type": "multipart/form-data" },
      responseType: "blob",
      timeout: 0,
    });
    const blob = await blobAsPdfOrThrow(res.data, res.status);
    triggerDownload(blob, "NautiCAI_Report.pdf");
  } catch (e) {
    if (e.response?.data instanceof Blob) throw new Error(await parseBlobError(e.response.data));
    throw e;
  }
};

export const downloadBatchPDF = async (files, params) => {
  const fd = new FormData();
  files.forEach((file) => fd.append("files", file));
  Object.entries(params || {}).forEach(([k, v]) => fd.append(k, v));

  try {
    const res = await API.post("/api/report/pdf/batch", fd, {
      headers: { "Content-Type": "multipart/form-data" },
      responseType: "blob",
      timeout: 0,
    });
    const blob = await blobAsPdfOrThrow(res.data, res.status);
    triggerDownload(blob, "NautiCAI_Batch_Report.pdf");
  } catch (e) {
    if (e.response?.data instanceof Blob) throw new Error(await parseBlobError(e.response.data));
    throw e;
  }
};

export const runVideoDetection = async (file, params) => {
  const fd = new FormData();
  fd.append("file", file);
  Object.entries(params || {}).forEach(([k, v]) => fd.append(k, v));

  const res = await API.post("/api/video/detect", fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
};

/** Full-length MP4 with detection boxes/labels burned in (server-side; may take several minutes). */
export const downloadAnnotatedVideo = async (file, params) => {
  const fd = new FormData();
  fd.append("file", file);
  Object.entries(params || {}).forEach(([k, v]) => fd.append(k, v));

  try {
    const res = await API.post("/api/video/export-annotated", fd, {
      headers: { "Content-Type": "multipart/form-data" },
      responseType: "blob",
      timeout: 0,
    });
    const blob = res.data;
    if (!blob?.size) throw new Error("Empty video export");
    const base = (file?.name || "video").replace(/\.[^.]+$/, "");
    const safe = base.replace(/[^\w.\-]+/g, "_").slice(0, 80);
    triggerDownload(blob, `NautiCAI_annotated_${safe}.mp4`);
  } catch (e) {
    if (e.response?.data instanceof Blob) throw new Error(await parseBlobError(e.response.data));
    throw e;
  }
};

export const downloadVideoPDF = async (file, params) => {
  const fd = new FormData();
  fd.append("file", file);
  Object.entries(params || {}).forEach(([k, v]) => fd.append(k, v));

  try {
    const res = await API.post("/api/report/pdf/video", fd, {
      headers: { "Content-Type": "multipart/form-data" },
      responseType: "blob",
      timeout: 0,
    });
    const blob = await blobAsPdfOrThrow(res.data, res.status);
    triggerDownload(blob, "NautiCAI_Video_Report.pdf");
  } catch (e) {
    if (e.response?.data instanceof Blob) throw new Error(await parseBlobError(e.response.data));
    throw e;
  }
};

export const sendPDFToWhatsApp = async (file, params) => {
  const fd = new FormData();
  fd.append("file", file);
  Object.entries(params || {}).forEach(([k, v]) => fd.append(k, v));

  const res = await API.post("/api/report/pdf/send-whatsapp", fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
};

export const sendVideoPDFToWhatsApp = async (file, params) => {
  const fd = new FormData();
  fd.append("file", file);
  Object.entries(params || {}).forEach(([k, v]) => fd.append(k, v));

  const res = await API.post("/api/report/pdf/video/send-whatsapp", fd, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 0,
  });
  return res.data;
};

export const sendWhatsAppMessage = async (to, message) => {
  const res = await API.post("/api/whatsapp/send", { to, message });
  return res.data;
};