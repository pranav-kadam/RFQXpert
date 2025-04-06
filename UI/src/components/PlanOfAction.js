import React from 'react';

function PlanOfAction({ plan }) {
     if (!plan || plan.length === 0) return null;

    return (
        <section className="plan-of-action card">
            <h2>Plan of Action</h2>
            <table>
                <thead>
                    <tr>
                        <th>Step</th>
                        <th>Description</th>
                        <th>Timeline</th>
                    </tr>
                </thead>
                <tbody>
                    {plan.map((item, index) => (
                        <tr key={index}>
                            <td>{item.step}</td>
                            <td>{item.description}</td>
                            <td>{item.timeline}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </section>
    );
}

export default PlanOfAction;