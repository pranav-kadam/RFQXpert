import React, { useEffect, useState } from 'react';

export default function Home() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    const fetchData = () => {
      fetch('http://localhost:8001/data')
        .then((res) => {
          if (!res.ok) {
            throw new Error('Network response was not ok');
          }
          return res.json();
        })
        .then((data) => {
          setData(data);
          setLoading(false);
        })
        .catch((error) => {
          console.error('Error fetching data:', error);
          // Instead of showing error immediately, we'll retry
          setRetryCount(prevCount => prevCount + 1);
          // Wait before retrying
          setTimeout(fetchData, 3000);
        });
    };

    fetchData();
  }, []);

  if (loading) return <LoadingState retryCount={retryCount} />;
  if (error) return <ErrorState message={error} />;
  if (!data) return <div className="text-center p-8 text-gray-300">No data available</div>;

  return (
    <div className="min-h-screen bg-gray-900 text-gray-200">
      <header className="bg-gradient-to-r from-indigo-900 to-purple-900 shadow-lg">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <h1 className="text-3xl font-bold text-white">RFP Analysis Dashboard</h1>
        </div>
      </header>
      
      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          <ComplianceSummary data={data.compliance_status} />
          
          <div className="lg:col-span-3 grid grid-cols-1 gap-8">
            <RequirementsPanel requirements={data.requirements_checklist} />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <RecommendationsPanel recommendations={data.recommendations} />
              <ActionPlanPanel actionPlan={data.plan_of_action} />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

function LoadingState({ retryCount = 0 }) {
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-900">
      <div className="text-center">
        <div className="w-16 h-16 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
        <p className="mt-4 text-lg text-gray-300 font-medium">Loading dashboard data...</p>
        {retryCount > 0 && (
          <p className="mt-2 text-sm text-gray-400">
            Waiting for server to respond... (Attempt {retryCount})
          </p>
        )}
      </div>
    </div>
  );
}

function ErrorState({ message }) {
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-900">
      <div className="text-center p-8 bg-gray-800 rounded-xl shadow-xl max-w-md border border-gray-700">
        <div className="w-16 h-16 bg-red-900 rounded-full flex items-center justify-center mx-auto">
          <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
          </svg>
        </div>
        <h2 className="mt-4 text-xl font-semibold text-gray-200">Failed to load data</h2>
        <p className="mt-2 text-gray-400">{message}</p>
        <button 
          onClick={() => window.location.reload()} 
          className="mt-6 px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors shadow-md"
        >
          Try Again
        </button>
      </div>
    </div>
  );
}

function ComplianceSummary({ data }) {
  const percentage = parseFloat(data.compliance_percentage);
  
  let statusColor = "text-red-400";
  let statusBg = "bg-red-900";
  let statusRing = "ring-red-400";
  
  if (percentage >= 90) {
    statusColor = "text-green-400";
    statusBg = "bg-green-900";
    statusRing = "ring-green-400";
  } else if (percentage >= 70) {
    statusColor = "text-yellow-300";
    statusBg = "bg-yellow-900";
    statusRing = "ring-yellow-300";
  } else if (percentage >= 50) {
    statusColor = "text-amber-400";
    statusBg = "bg-amber-900";
    statusRing = "ring-amber-400";
  }

  return (
    <div className="bg-gray-800 shadow-xl rounded-xl p-6 transform transition-all hover:shadow-2xl border border-gray-700">
      <h2 className="text-xl font-semibold text-gray-200 border-b border-gray-700 pb-3 mb-5">Compliance Overview</h2>
      
      <div className="flex justify-center mb-6">
        <div className="relative w-36 h-36">
          <svg className="w-full h-full -rotate-90 transform" viewBox="0 0 36 36">
            <path 
              className="stroke-current text-gray-700" 
              fill="none" 
              strokeWidth="3.8" 
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            />
            <path 
              className={`stroke-current ${statusColor}`}
              fill="none" 
              strokeWidth="3.8" 
              strokeDasharray={`${percentage}, 100`} 
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            />
          </svg>
          <div className={`absolute inset-0 flex items-center justify-center text-3xl font-bold ${statusColor} ring-4 ${statusRing} rounded-full`}>
            {data.compliance_percentage}
          </div>
        </div>
      </div>
      
      <p className="text-gray-300 mb-6 text-center font-medium">{data.summary}</p>
      
      {data.major_gaps.length > 0 && (
        <div className={`${statusBg} p-4 rounded-lg bg-opacity-30`}>
          <h3 className="font-semibold text-gray-200 mb-2">Major Gaps:</h3>
          <ul className="space-y-2">
            {data.major_gaps.map((gap, index) => (
              <li key={index} className="flex items-start">
                <svg className={`h-5 w-5 ${statusColor} mr-2 mt-0.5 flex-shrink-0`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <span className="text-gray-300">{gap}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function RequirementsPanel({ requirements }) {
  const completedCount = requirements.filter(req => req.status).length;
  const completionPercentage = (completedCount / requirements.length * 100).toFixed(0);

  return (
    <div className="bg-gray-800 shadow-xl rounded-xl overflow-hidden border border-gray-700">
      <div className="p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-gray-200">Requirements Checklist</h2>
          <div className="flex items-center">
            <div className="w-24 h-2 bg-gray-700 rounded-full mr-3">
              <div 
                className="h-full rounded-full bg-indigo-500" 
                style={{ width: `${completionPercentage}%` }}
              ></div>
            </div>
            <span className="text-sm font-medium bg-indigo-900 text-indigo-200 py-1 px-3 rounded-full">
              {completedCount}/{requirements.length}
            </span>
          </div>
        </div>
      </div>
      
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-700">
          <thead className="bg-gray-900">
            <tr>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Requirement</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Explanation</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {requirements.map((req, index) => (
              <tr key={index} className={index % 2 === 0 ? 'bg-gray-800' : 'bg-gray-900'}>
                <td className="px-6 py-4 text-sm font-medium text-gray-200">{req.requirement}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {req.status ? (
                    <span className="px-3 py-1 inline-flex items-center rounded-full bg-green-900 text-green-200">
                      <svg className="w-4 h-4 mr-1.5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"></path>
                      </svg>
                      Compliant
                    </span>
                  ) : (
                    <span className="px-3 py-1 inline-flex items-center rounded-full bg-red-900 text-red-200">
                      <svg className="w-4 h-4 mr-1.5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                        <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd"></path>
                      </svg>
                      Non-Compliant
                    </span>
                  )}
                </td>
                <td className="px-6 py-4 text-sm text-gray-400">{req.explanation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RecommendationsPanel({ recommendations }) {
  const priorityClasses = {
    'High': 'border-red-500 bg-red-900 bg-opacity-20',
    'Medium': 'border-yellow-500 bg-yellow-900 bg-opacity-20',
    'Low': 'border-green-500 bg-green-900 bg-opacity-20'
  };

  const priorityBadges = {
    'High': 'bg-red-900 text-red-200',
    'Medium': 'bg-yellow-900 text-yellow-200',
    'Low': 'bg-green-900 text-green-200'
  };

  return (
    <div className="bg-gray-800 shadow-xl rounded-xl p-6 border border-gray-700">
      <h2 className="text-xl font-semibold text-gray-200 border-b border-gray-700 pb-3 mb-5">Recommendations</h2>
      
      <div className="space-y-5">
        {recommendations.map((rec, index) => (
          <div 
            key={index} 
            className={`border-l-4 rounded-lg p-4 ${priorityClasses[rec.priority]}`}
          >
            <div className="flex justify-between items-start">
              <h3 className="font-medium text-gray-200">{rec.recommendation}</h3>
              <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${priorityBadges[rec.priority]}`}>
                {rec.priority}
              </span>
            </div>
            <p className="text-sm text-gray-400 mt-2 flex items-center">
              <svg className="w-4 h-4 mr-1 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
              Related to: {rec.related_gap}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function ActionPlanPanel({ actionPlan }) {
  return (
    <div className="bg-gray-800 shadow-xl rounded-xl p-6 border border-gray-700">
      <h2 className="text-xl font-semibold text-gray-200 border-b border-gray-700 pb-3 mb-5">Action Plan</h2>
      
      <div className="relative">
        <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-indigo-900"></div>
        
        <div className="space-y-6 relative">
          {actionPlan.map((step, index) => (
            <div key={index} className="relative pl-10 group">
              <div className="absolute left-0 top-1 w-10 h-10 rounded-full bg-gradient-to-r from-indigo-800 to-purple-800 text-white flex items-center justify-center shadow-md group-hover:scale-110 transition-transform duration-200">
                {step.step}
              </div>
              <div className="bg-gray-900 p-4 rounded-lg border border-gray-700 shadow-sm group-hover:shadow-md transition-shadow duration-200">
                <h3 className="font-medium text-gray-200">{step.description}</h3>
                <p className="mt-2 text-sm text-gray-400 flex items-center">
                  <svg className="w-4 h-4 mr-1.5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                  </svg>
                  {step.timeline}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}