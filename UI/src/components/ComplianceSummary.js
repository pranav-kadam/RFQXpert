import React from 'react';

function ComplianceSummary({ summary }) {
    if (!summary) return null;

    return (
        <section className="compliance-summary card">
            <h2>Compliance Summary</h2>
            <p><strong>Overall Compliance:</strong> {summary.compliance_percentage || 'N/A'}</p>
            <p><strong>Summary:</strong> {summary.summary || 'No summary provided.'}</p>
            <p><strong>Major Gaps:</strong></p>
            {summary.major_gaps && summary.major_gaps.length > 0 ? (
                <ul>
                    {summary.major_gaps.map((gap, index) => (
                        <li key={index}>{gap}</li>
                    ))}
                </ul>
            ) : (
                <p>No major gaps identified.</p>
            )}
        </section>
    );
}

export default ComplianceSummary;