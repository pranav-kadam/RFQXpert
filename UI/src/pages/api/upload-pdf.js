import formidable from 'formidable';
import fs from 'fs';
import path from 'path';

export const config = {
  api: {
    bodyParser: false,
  },
};

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).end("Method Not Allowed");

  const form = new formidable.IncomingForm();
  const uploadDir = path.join(process.cwd(), 'public');

  form.uploadDir = uploadDir;
  form.keepExtensions = true;
  form.maxFileSize = 10 * 1024 * 1024; // 10MB

  form.parse(req, async (err, fields, files) => {
    if (err) return res.status(500).json({ error: err.message });

    const uploadedFile = files.file[0];
    const outputPath = path.join(uploadDir, 'relevant_tenders_report.pdf');

    try {
      fs.renameSync(uploadedFile.filepath, outputPath);
      return res.status(200).json({ message: "Uploaded successfully" });
    } catch (error) {
      return res.status(500).json({ error: "Failed to save file" });
    }
  });
}
