import React from "react";

export default function ExplorePage() {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-semibold mb-4">Relevant Tenders Report</h1>
      <a
        href="/api/relevant-tenders-report"
        target="_blank"
        rel="noopener noreferrer"
        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
      >
        📄 View PDF Report
      </a>
    </div>
  );
}

