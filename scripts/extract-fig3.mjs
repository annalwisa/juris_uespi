import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createCanvas } from "@napi-rs/canvas";
import { getDocument, GlobalWorkerOptions } from "pdfjs-dist/legacy/build/pdf.mjs";

const PDF_PATH = "C:\\Users\\anna luisa\\OneDrive\\Documentos\\TCC\\imagem.pdf";
const OUT_DIR = "C:\\Users\\anna luisa\\OneDrive\\Documentos\\TCC";
const OUT_FILE = path.join(OUT_DIR, "fig3.png");
const DPI = 400;

// Vertical band (in PDF points, origin bottom-left) that contains ONLY the
// Fig. 3 timeline: below the page number "9" (top) and above the caption
// "Fig. 3: ..." (bottom).
const BAND_TOP_PDF = 752; // exclui o número da página
const BAND_BOTTOM_PDF = 553; // exclui a legenda "Fig. 3: ..."
const WHITE_THRESHOLD = 245; // pixel considerado "conteúdo" se algum canal < isto
const MARGIN_PX = 16;

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

function fig3Pattern() {
  return /\bfig(?:ura)?\.?\s*3\b/i;
}

async function loadPdf() {
  const data = new Uint8Array(fs.readFileSync(PDF_PATH));
  return getDocument({ data, useSystemFonts: true }).promise;
}

async function findFig3Page(doc) {
  for (let i = 1; i <= doc.numPages; i++) {
    const page = await doc.getPage(i);
    const text = (await page.getTextContent()).items
      .map((item) => item.str)
      .join(" ");
    if (fig3Pattern().test(text)) return { pageNumber: i, page };
  }
  return null;
}

function findContentBBox(ctx, x0, y0, w, h) {
  const { data } = ctx.getImageData(x0, y0, w, h);
  let minX = w;
  let minY = h;
  let maxX = -1;
  let maxY = -1;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const idx = (y * w + x) * 4;
      const r = data[idx];
      const g = data[idx + 1];
      const b = data[idx + 2];
      const a = data[idx + 3];
      if (a > 10 && (r < WHITE_THRESHOLD || g < WHITE_THRESHOLD || b < WHITE_THRESHOLD)) {
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      }
    }
  }
  if (maxX < 0) return null;
  return { minX, minY, maxX, maxY };
}

async function main() {
  if (!fs.existsSync(PDF_PATH)) throw new Error(`PDF não encontrado: ${PDF_PATH}`);

  const doc = await loadPdf();
  const found = await findFig3Page(doc);
  if (!found) throw new Error('Texto "Fig. 3" não encontrado no PDF.');

  const { pageNumber, page } = found;
  const scale = DPI / 72;
  const viewport = page.getViewport({ scale });
  const canvas = createCanvas(viewport.width, viewport.height);
  const ctx = canvas.getContext("2d");
  await page.render({ canvasContext: ctx, viewport }).promise;

  const pageHeightPt = viewport.height / scale;

  // Faixa de busca em pixels (canvas é top-down).
  const bandY0 = Math.max(0, Math.floor((pageHeightPt - BAND_TOP_PDF) * scale));
  const bandY1 = Math.min(viewport.height, Math.ceil((pageHeightPt - BAND_BOTTOM_PDF) * scale));
  const bandH = bandY1 - bandY0;

  const bbox = findContentBBox(ctx, 0, bandY0, viewport.width, bandH);
  if (!bbox) throw new Error("Nenhum conteúdo encontrado na faixa da Fig. 3.");

  const x0 = Math.max(0, bbox.minX - MARGIN_PX);
  const y0 = Math.max(0, bandY0 + bbox.minY - MARGIN_PX);
  const x1 = Math.min(viewport.width, bbox.maxX + 1 + MARGIN_PX);
  const y1 = Math.min(viewport.height, bandY0 + bbox.maxY + 1 + MARGIN_PX);
  const width = x1 - x0;
  const height = y1 - y0;

  const cropped = createCanvas(width, height);
  const cctx = cropped.getContext("2d");
  cctx.drawImage(canvas, x0, y0, width, height, 0, 0, width, height);
  fs.writeFileSync(OUT_FILE, cropped.toBuffer("image/png"));

  console.log(`Fig. 3 (página ${pageNumber}) salva em: ${OUT_FILE}`);
  console.log(`Resolução: ${width} x ${height} px @ ${DPI} dpi`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
