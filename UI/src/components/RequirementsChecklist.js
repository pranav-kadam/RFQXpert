import React from 'react';

function RequirementsChecklist({ checklist }) {
    if (!checklist || checklist.length === 0) return null;

    return (
        <section className="requirements-checklist card">
            <h2>Requirements Checklist</h2>
            <table>
                <thead>
                    <tr>
                        <th>Requirement</th>
                        <th>Status</th>
                        <th>Explanation</th>
                    </tr>
                </thead>
                <tbody>
                    {checklist.map((item, index) => (
                        <tr key={index}>
                            <td>{item.requirement}</td>
                            <td className={item.status ? 'status-met' : 'status-not-met'}>
                                {item.status ? 'Met' : 'Not Met'}
                            </td>
                            <td>{item.explanation}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </section>
    );
}

export default RequirementsChecklist;