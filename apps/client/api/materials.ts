import type { LibraryItem } from "../types";
import { correlationHeaders, readJson } from "./http";

export async function fetchMaterials(): Promise<LibraryItem[]> {
  const response = await fetch("/api/materials");
  return readJson<LibraryItem[]>(response);
}

export async function uploadMaterial(file: File, correlationId?: string): Promise<LibraryItem> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("displayName", file.name.replace(/\.pdf$/i, ""));

  const response = await fetch("/api/materials", {
    method: "POST",
    headers: correlationHeaders(correlationId),
    body: formData,
  });

  return readJson<LibraryItem>(response);
}
