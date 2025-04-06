import path from "path";
import fs from "fs";

export default function handler(req, res) {
  const filePath = path.join(process.cwd(), "public", "relevant_tenders_report.pdf");

  if (!fs.existsSync(filePath)) {
    return res.status(404).json({ error: "PDF not found" });
  }

  res.setHeader("Content-Type", "application/pdf");
  res.setHeader("Content-Disposition", 'inline; filename="relevant_tenders_report.pdf"');

  const fileStream = fs.createReadStream(filePath);
  fileStream.pipe(res);
}
