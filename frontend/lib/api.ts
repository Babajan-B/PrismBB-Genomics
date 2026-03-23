const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

async function handleResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    if (typeof payload === "string") {
      throw new Error(payload || `HTTP error! status: ${response.status}`);
    }

    const detail =
      payload &&
      typeof payload === "object" &&
      "detail" in payload
        ? String((payload as { detail?: unknown }).detail || "")
        : "";

    throw new Error(detail || `HTTP error! status: ${response.status}`);
  }

  return payload as T;
}

export async function uploadVCF(formData: FormData) {
  try {
    const res = await fetch(`${API_URL}/api/upload`, {
      method: "POST",
      body: formData,
    });
    return handleResponse(res);
  } catch (error) {
    console.error("Upload error:", error);
    throw error;
  }
}

export async function getJobs(limit = 20) {
  try {
    const res = await fetch(`${API_URL}/api/jobs?limit=${limit}`, { cache: "no-store" });
    return handleResponse(res);
  } catch (error) {
    console.error("Get jobs error:", error);
    return { jobs: [] };
  }
}

export async function getJobStatus(jobId: string) {
  try {
    const res = await fetch(`${API_URL}/api/jobs/${jobId}/status`, { cache: "no-store" });
    return handleResponse(res);
  } catch (error) {
    console.error("Get job status error:", error);
    return null;
  }
}

export async function getVariants(jobId: string, params: Record<string, string | number | undefined> = {}) {
  try {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined) query.set(k, String(v)); });
    const res = await fetch(`${API_URL}/api/jobs/${jobId}/variants?${query}`, { cache: "no-store" });
    return handleResponse(res);
  } catch (error) {
    console.error("Get variants error:", error);
    return { variants: [] };
  }
}

export async function getVariantDetail(jobId: string, variantId: string) {
  try {
    const res = await fetch(`${API_URL}/api/jobs/${jobId}/variants/${variantId}`, { cache: "no-store" });
    return handleResponse(res);
  } catch (error) {
    console.error("Get variant detail error:", error);
    return { detail: "Not found" };
  }
}

export async function sendChat(payload: { message: string; job_id?: string; history?: unknown[] }) {
  try {
    const res = await fetch(`${API_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  } catch (error) {
    console.error("Send chat error:", error);
    return { response: "Connection error. Please try again." };
  }
}

export async function getAuditLog(jobId: string) {
  try {
    const res = await fetch(`${API_URL}/api/jobs/${jobId}/audit`, { cache: "no-store" });
    return handleResponse(res);
  } catch (error) {
    console.error("Get audit log error:", error);
    return [];
  }
}

export function getReportUrl(jobId: string, format: "json" | "csv" | "excel") {
  return `${API_URL}/api/jobs/${jobId}/report?format=${format}`;
}
