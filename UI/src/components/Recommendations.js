import React from 'react';

function Recommendations({ recommendations }) {
    if (!recommendations || recommendations.length === 0) return null;

    // Optional: Sort by priority here if needed, similar to vanilla JS example
    const sortedRecommendations = [...recommendations].sort((a, b) => {
         const priorities = { 'High': 1, 'Medium': 2, 'Low': 3 };
         return (priorities[a.priority] || 99) - (priorities[b.priority] || 99);
    });


    return (
        <section className="recommendations card">
            <h2>Recommendations</h2>
            <table>
                <thead>
                    <tr>
                        <th>Priority</th>
                        <th>Recommendation</th>
                        <th>Related Gap</th>
                    </tr>
                </thead>
                <tbody>
                    {sortedRecommendations.map((item, index) => (
                        <tr key={index}>
                            <td className={`priority-${item.priority?.toLowerCase()}`}>{item.priority}</td>
                            <td>{item.recommendation}</td>
                            <td>{item.related_gap}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </section>
    );
}

export default Recommendations;