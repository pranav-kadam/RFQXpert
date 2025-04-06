// /pages/api/checklist_output.ts (or .js)

import fs from 'fs';
import path from 'path';

export default function handler(req, res) {
    try {
        const filePath = path.join(process.cwd(), 'public', 'checklist_output.json');
        const fileContents = fs.readFileSync(filePath, 'utf8');
        const json = JSON.parse(fileContents);

        res.status(200).json(json);
    } catch (error) {
        console.error('Error reading checklist_output.json:', error);
        res.status(500).json({ error: 'Failed to read checklist data' });
    }
}
