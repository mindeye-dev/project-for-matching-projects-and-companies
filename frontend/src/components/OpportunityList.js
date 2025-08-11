import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { DataGrid } from '@mui/x-data-grid';
import { Box, TextField, Button, CircularProgress, Paper, Typography, Grid } from '@mui/material';
import * as XLSX from 'xlsx';
import jsPDF from 'jspdf';
import 'jspdf-autotable';

const columns = [
    { field: 'project_name', headerName: 'Project Name', flex: 1 },
    { field: 'client', headerName: 'Client', flex: 1 },
    { field: 'country', headerName: 'Country', flex: 1 },
    { field: 'sector', headerName: 'Sector', flex: 1 },
    { field: 'deadline', headerName: 'Deadline', flex: 1 },
    { field: 'score', headerName: 'Score', flex: 0.5, type: 'number' },
    {
        field: 'url',
        headerName: 'URL',
        flex: 0.7,
        renderCell: (params) => params.value ? <a href={params.value} target="_blank" rel="noopener noreferrer">Link</a> : ''
    }
];

function toCSV(rows) {
    if (!rows.length) return '';
    const header = Object.keys(rows[0]);
    const csv = [header.join(',')];
    for (const row of rows) {
        csv.push(header.map(h => '"' + (row[h] ? String(row[h]).replace(/"/g, '""') : '') + '"').join(','));
    }
    return csv.join('\r\n');
}

function toXLSX(rows, filename = 'opportunities_filtered.xlsx') {
    const ws = XLSX.utils.json_to_sheet(rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Opportunities');
    XLSX.writeFile(wb, filename);
}

function toPDF(rows, filename = 'opportunities_filtered.pdf') {
    const doc = new jsPDF();
    if (!rows.length) {
        doc.text('No data to export.', 10, 10);
        doc.save(filename);
        return;
    }
    const headers = Object.keys(rows[0]).map(h => h.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()));
    const data = rows.map(row => headers.map((h, i) => row[Object.keys(rows[0])[i]]));
    doc.autoTable({ head: [headers], body: data });
    doc.save(filename);
}

export default function OpportunityList() {
    const [opps, setOpps] = useState([]);
    const [loading, setLoading] = useState(false);
    const [country, setCountry] = useState('');
    const [sector, setSector] = useState('');
    const [minScore, setMinScore] = useState('');
    const [deadlineFrom, setDeadlineFrom] = useState('');
    const [deadlineTo, setDeadlineTo] = useState('');
    const [page, setPage] = useState(0);
    const [pageSize, setPageSize] = useState(10);

    const fetchOpps = async () => {
        setLoading(true);
        let url = '/api/opportunities';
        const params = [];
        if (country) params.push(`country=${encodeURIComponent(country)}`);
        if (sector) params.push(`sector=${encodeURIComponent(sector)}`);
        url += params.length ? '?' + params.join('&') : '';
        const res = await axios.get(url);
        let data = res.data;
        // Advanced filtering (client-side for demo)
        if (minScore) data = data.filter(o => o.score >= parseInt(minScore));
        if (deadlineFrom) data = data.filter(o => o.deadline && o.deadline >= deadlineFrom);
        if (deadlineTo) data = data.filter(o => o.deadline && o.deadline <= deadlineTo);
        setOpps(data);
        setLoading(false);
    };

    useEffect(() => {
        fetchOpps();
        // eslint-disable-next-line
    }, [country, sector, minScore, deadlineFrom, deadlineTo]);

    const handleExport = () => {
        // Export only currently filtered (and paginated) rows
        const start = page * pageSize;
        const end = start + pageSize;
        const rows = opps.slice(start, end);
        const csv = toCSV(rows);
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'opportunities_filtered.csv';
        a.click();
        window.URL.revokeObjectURL(url);
    };

    const handleExportAllXLSX = () => {
        toXLSX(opps, 'opportunities_filtered.xlsx');
    };

    const handleExportAllPDF = () => {
        toPDF(opps, 'opportunities_filtered.pdf');
    };

    return (
        <Paper sx={{ p: 3 }}>
            <Typography variant="h5" gutterBottom>Opportunities</Typography>
            <Grid container spacing={2} sx={{ mb: 2 }}>
                <Grid item xs={12} sm={6} md={2}>
                    <TextField label="Country" value={country} onChange={e => setCountry(e.target.value)} size="small" fullWidth />
                </Grid>
                <Grid item xs={12} sm={6} md={2}>
                    <TextField label="Sector" value={sector} onChange={e => setSector(e.target.value)} size="small" fullWidth />
                </Grid>
                <Grid item xs={12} sm={6} md={2}>
                    <TextField label="Min Score" value={minScore} onChange={e => setMinScore(e.target.value)} size="small" type="number" fullWidth />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <TextField label="Deadline From" value={deadlineFrom} onChange={e => setDeadlineFrom(e.target.value)} size="small" type="date" InputLabelProps={{ shrink: true }} fullWidth />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                    <TextField label="Deadline To" value={deadlineTo} onChange={e => setDeadlineTo(e.target.value)} size="small" type="date" InputLabelProps={{ shrink: true }} fullWidth />
                </Grid>
                <Grid item xs={12} sm={6} md={1}>
                    <Button variant="outlined" onClick={fetchOpps} fullWidth>Refresh</Button>
                </Grid>
                <Grid item xs={12} sm={6} md={2}>
                    <Button variant="contained" color="primary" onClick={handleExport} fullWidth sx={{ height: '100%' }}>Export Page (CSV)</Button>
                </Grid>
                <Grid item xs={12} sm={6} md={2}>
                    <Button variant="contained" color="success" onClick={handleExportAllXLSX} fullWidth sx={{ height: '100%' }}>Export All Filtered (Excel)</Button>
                </Grid>
                <Grid item xs={12} sm={6} md={2}>
                    <Button variant="contained" color="secondary" onClick={handleExportAllPDF} fullWidth sx={{ height: '100%' }}>Export All Filtered (PDF)</Button>
                </Grid>
            </Grid>
            {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
                    <CircularProgress />
                </Box>
            ) : (
                <DataGrid
                    autoHeight
                    rows={opps.map((o, i) => ({ ...o, id: o.id || i }))}
                    columns={columns}
                    page={page}
                    pageSize={pageSize}
                    onPageChange={setPage}
                    onPageSizeChange={setPageSize}
                    rowsPerPageOptions={[5, 10, 20, 50]}
                    pagination
                />
            )}
        </Paper>
    );
} 