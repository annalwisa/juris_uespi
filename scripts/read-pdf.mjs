import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { getDocument, GlobalWorkerOptions } from "pdfjs-dist/legacy/build/pdf.mjs";

const PDF_PATH = process.argv[2];
if (!PDF_PATH) {
  console.error("uso: node read-pdf.mjs <caminho.pdf>");
  process.exit(1);
}

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
console.log(`### PÁGINAS: ${doc.numPages}\n`);

for (let i = 1; i <= doc.numPages; i++) {
  const page = await doc.getPage(i);
  const tc = await page.getTextContent();
  let lastY = null;
  let line = "";
  const lines = [];
  for (const item of tc.items) {
    const y = item.transform[5];
    if (lastY !== null && Math.abs(y - lastY) > 2) {
      lines.push(line.trimEnd());
      line = "";
    }
    line += item.str;
    if (item.hasEOL) {
      lines.push(line.trimEnd());
      line = "";
    }
    lastY = y;
  }
  if (line.trim()) lines.push(line.trimEnd());
  console.log(`\n===== PÁGINA ${i} =====`);
  console.log(lines.join("\n"));
}
