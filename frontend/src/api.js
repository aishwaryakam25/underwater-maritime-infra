import axios from "axios";

const API = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
});

export const getHealth = async () => (await API.get("/health")).data;

export const runDetection = async (file, params) => {
  const fd = new FormData();
  fd.append("file", file);
  Object.entries(params || {}).forEach(([k, v]) => fd.append(k, v));

  const res = await API.post("/api/detect", fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
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

  const res = await API.post("/api/report/pdf", fd, {
    headers: { "Content-Type": "multipart/form-data" },
    responseType: "blob",
  });

  const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = "NautiCAI_Report.pdf";
  a.click();
};

export const downloadBatchPDF = async (files, params) => {
  const fd = new FormData();
  files.forEach((file) => fd.append("files", file));
  Object.entries(params || {}).forEach(([k, v]) => fd.append(k, v));

  const res = await API.post("/api/report/pdf/batch", fd, {
    headers: { "Content-Type": "multipart/form-data" },
    responseType: "blob",
  });

  const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = "NautiCAI_Batch_Report.pdf";
  a.click();
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

export const downloadVideoPDF = async (file, params) => {
  const fd = new FormData();
  fd.append("file", file);
  Object.entries(params || {}).forEach(([k, v]) => fd.append(k, v));

  const res = await API.post("/api/video/report/pdf", fd, {
    headers: { "Content-Type": "multipart/form-data" },
    responseType: "blob",
  });

  const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = "NautiCAI_Video_Report.pdf";
  a.click();
};

export const sendPDFToWhatsApp = async (file, params) => {
  const fd = new FormData();
  fd.append("file", file);
  Object.entries(params || {}).forEach(([k, v]) => fd.append(k, v));

  const res = await API.post("/api/report/pdf/whatsapp", fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
};

export const sendVideoPDFToWhatsApp = async (file, params) => {
  const fd = new FormData();
  fd.append("file", file);
  Object.entries(params || {}).forEach(([k, v]) => fd.append(k, v));

  const res = await API.post("/api/video/report/pdf/whatsapp", fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
};

export const sendWhatsAppMessage = async (to, message) => {
  const res = await API.post("/api/whatsapp/message", { to, message });
  return res.data;
};