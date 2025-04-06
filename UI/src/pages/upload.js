'use client';

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
        let isMounted = true;

     // First, confirm your API endpoint is correct
const fetchData = async () => {
  try {
    // For debugging, log the request
    console.log("Fetching from: http://localhost:8000/checklist_output");
    
    const response = await fetch('http://localhost:8000/checklist_output');
    
    // Log the response status for debugging
    console.log("Response status:", response.status);
    
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    
    const contentType = response.headers.get('content-type');
    console.log("Content type:", contentType);
    
    if (!contentType?.includes('application/json')) {
      throw new Error('Invalid content-type. Expected application/json');
    }
    
    const data = await response.json();
    console.log("Received data:", data);
    
    if (isMounted) setComplianceData(data);
  } catch (err) {
    console.error("Failed to fetch compliance data:", err);
    if (isMounted) setError(`Failed to load compliance data: ${err.message}`);
  } finally {
    if (isMounted) setLoading(false);
  }
};

        fetchData();

        return () => {
            isMounted = false;
        };
    }, []);

    if (loading) return <div className="p-4 text-gray-500">Loading compliance data...</div>;
    if (error) return <div className="p-4 text-red-500 font-medium">{error}</div>;
    if (!complianceData) return <div className="p-4 text-yellow-600">No data available.</div>;

    const {
        compliance_status,
        requirements_checklist,
        recommendations,
        plan_of_action
    } = complianceData;

    return (
        <div className="container space-y-6 py-6">
            <h1 className="text-3xl font-bold text-blue-800 mb-4">
                RFP Analysis
            </h1>

            {compliance_status && <ComplianceSummary summary={compliance_status} />}
            {requirements_checklist && <RequirementsChecklist checklist={requirements_checklist} />}
            {recommendations && <Recommendations recommendations={recommendations} />}
            {plan_of_action && <PlanOfAction plan={plan_of_action} />}
        </div>
    );
}

export default App;
