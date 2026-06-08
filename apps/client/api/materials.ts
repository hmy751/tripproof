import type { LibraryItem } from "../types";
import { readJson } from "./http";

export async function fetchMaterials(): Promise<LibraryItem[]> {
  const response = await fetch("/api/materials");
  return readJson<LibraryItem[]>(response);
}

export async function uploadMaterial(file: File): Promise<LibraryItem> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("displayName", file.name.replace(/\.pdf$/i, ""));

  const response = await fetch("/api/materials", {
    method: "POST",
    body: formData,
  });

  return readJson<LibraryItem>(response);
}
