import React from 'react';

export default function Reports() {
    const handleDownload = () => {
        window.location.href = '/api/opportunities/report';
    };
    return (
        <div>
            <h3>Download Opportunities Report</h3>
            <button onClick={handleDownload}>Download Excel</button>
        </div>
    );
}
