import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { getDocument, GlobalWorkerOptions } from "pdfjs-dist/legacy/build/pdf.mjs";

const PDF_PATH = "C:\\Users\\anna luisa\\OneDrive\\Documentos\\TCC\\imagem.pdf";

GlobalWorkerOptions.workerSrc = pathToFileURL(
  path.join(
    path.dirname(fileURLToPath(import.meta.url)),
    "node_modules",
    "pdfjs-dist",
    "legacy",
    "build",
    "pdf.worker.mjs",
  ),
).href;

const data = new Uint8Array(fs.readFileSync(PDF_PATH));
const doc = await getDocument({ data, useSystemFonts: true }).promise;
const page = await doc.getPage(1);
const vp = page.getViewport({ scale: 1 });
console.log("pageWidth", vp.width, "pageHeight", vp.height);
const tc = await page.getTextContent();
const rows = tc.items
  .filter((it) => it.str && it.str.trim())
  .map((it) => ({
    x: +it.transform[4].toFixed(1),
    y: +it.transform[5].toFixed(1),
    h: +(it.height || 0).toFixed(1),
    w: +(it.width || 0).toFixed(1),
    str: it.str,
  }))
  .sort((a, b) => b.y - a.y);
for (const r of rows) {
  console.log(`y=${r.y}\tx=${r.x}\th=${r.h}\tw=${r.w}\t${JSON.stringify(r.str)}`);
}
