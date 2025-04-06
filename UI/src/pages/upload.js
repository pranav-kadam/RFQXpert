import React, { useState, useEffect } from 'react';
import ComplianceSummary from '@/components/ComplianceSummary';
import RequirementsChecklist from '@/components/RequirementsChecklist';
import Recommendations from '@/components/Recommendations';
import PlanOfAction from '@/components/PlanOfAction';

function App() {
    const [complianceData, setComplianceData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        // Fetch data from the public folder
        fetch('/checklist_output.json') // Path relative to public folder
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                setComplianceData(data);
                setLoading(false);
            })
            .catch(err => {
                console.error("Failed to fetch compliance data:", err);
                setError("Failed to load compliance data. Please check the console.");
                setLoading(false);
            });
    }, []); // Empty dependency array means this runs once on mount

    if (loading) {
        return <div className="container">Loading compliance data...</div>;
    }

    if (error) {
        return <div className="container error">{error}</div>;
    }

    if (!complianceData) {
         return <div className="container">No data available.</div>
    }

    return (
        <div className="container">
            <h1>RFP Compliance Analysis for RFQXpert</h1>

            {complianceData.compliance_status && (
                <ComplianceSummary summary={complianceData.compliance_status} />
            )}

            {complianceData.requirements_checklist && (
                <RequirementsChecklist checklist={complianceData.requirements_checklist} />
            )}

            {complianceData.recommendations && (
                <Recommendations recommendations={complianceData.recommendations} />
            )}

            {complianceData.plan_of_action && (
                <PlanOfAction plan={complianceData.plan_of_action} />
            )}
        </div>
    );
}

export default App;