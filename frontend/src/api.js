import axios from "axios";

// In production, the API is on the same origin (behind nginx/Cloud Run).
// In dev, CRA proxy (package.json "proxy") forwards /api/* to localhost:8000.
const API = process.env.REACT_APP_API_URL || "";

const api = axios.create({ baseURL: API });

/** Health check */
export const getHealth = () => api.get("/api/health").then(r => r.data);

/** Run detection on an image file */
export const runDetection = (file, params) => {
  const fd = new FormData();
  fd.append("file", file);
  Object.entries(params).forEach(([k, v]) => fd.append(k, String(v)));
  return api.post("/api/detect", fd).then(r => r.data);
};

/** Get enhancement comparison images */
export const runEnhance = (file, params) => {
  const fd = new FormData();
  fd.append("file", file);
  Object.entries(params).forEach(([k, v]) => fd.append(k, String(v)));
  return api.post("/api/enhance", fd).then(r => r.data);
};

/** Download PDF report */
export const downloadPDF = async (file, params) => {
  const fd = new FormData();
  fd.append("file", file);
  Object.entries(params).forEach(([k, v]) => fd.append(k, String(v)));
  const resp = await api.post("/api/report/pdf", fd, { responseType: "blob" });
  // Trigger browser download
  const url = window.URL.createObjectURL(new Blob([resp.data], { type: "application/pdf" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = resp.headers["content-disposition"]?.split("filename=")[1]?.replace(/"/g, "") || "NautiCAI_Report.pdf";
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
};

/** Run video analysis */
export const runVideoDetection = (file, params) => {
  const fd = new FormData();
  fd.append("file", file);
  Object.entries(params).forEach(([k, v]) => fd.append(k, String(v)));
  return api.post("/api/video/detect", fd).then(r => r.data);
};

/** Download PDF report for video (ROV footage) */
export const downloadVideoPDF = async (file, params) => {
  const fd = new FormData();
  fd.append("file", file);
  Object.entries(params).forEach(([k, v]) => fd.append(k, String(v)));
  const resp = await api.post("/api/report/pdf/video", fd, { responseType: "blob" });
  const url = window.URL.createObjectURL(new Blob([resp.data], { type: "application/pdf" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = resp.headers["content-disposition"]?.split("filename=")[1]?.replace(/"/g, "") || "NautiCAI_Video_Report.pdf";
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
};

/** Send PDF report to WhatsApp (image report). Returns { sent, message, download_url? } */
export const sendPDFToWhatsApp = async (file, params) => {
  const fd = new FormData();
  fd.append("file", file);
  Object.entries(params).forEach(([k, v]) => fd.append(k, String(v)));
  const { data } = await api.post("/api/report/pdf/send-whatsapp", fd);
  return data;
};

/** Send video PDF report to WhatsApp */
export const sendVideoPDFToWhatsApp = async (file, params) => {
  const fd = new FormData();
  fd.append("file", file);
  Object.entries(params).forEach(([k, v]) => fd.append(k, String(v)));
  const { data } = await api.post("/api/report/pdf/video/send-whatsapp", fd);
  return data;
};

/** Send a text message to WhatsApp (alerts). */
export const sendWhatsAppMessage = (to, message) =>
  api.post("/api/whatsapp/send", { to, message }).then((r) => r.data);
