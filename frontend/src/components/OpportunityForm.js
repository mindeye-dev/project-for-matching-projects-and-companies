import React, { useState } from 'react';
import axios from 'axios';
import { TextField, Button, Box, CircularProgress, Typography, Paper } from '@mui/material';
import { useSnackbar } from 'notistack';

const initialState = {
    project_name: '',
    client: '',
    country: '',
    sector: '',
    summary: '',
    deadline: '',
    program: '',
    budget: '',
    url: ''
};

export default function OpportunityForm() {
    const [form, setForm] = useState(initialState);
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const { enqueueSnackbar } = useSnackbar();

    const handleChange = e => {
        setForm({ ...form, [e.target.name]: e.target.value });
    };

    const handleSubmit = async e => {
        e.preventDefault();
        setResult(null);
        setLoading(true);
        try {
            const res = await axios.post('/api/opportunity', form);
            setResult(res.data);
            setForm(initialState);
            enqueueSnackbar('Opportunity submitted successfully!', { variant: 'success' });
        } catch (err) {
            enqueueSnackbar('Submission failed. Please check your input.', { variant: 'error' });
        }
        setLoading(false);
    };

    return (
        <Paper sx={{ p: 3, maxWidth: 600, margin: 'auto' }}>
            <Typography variant="h5" gutterBottom>Submit New Opportunity</Typography>
            <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {Object.keys(initialState).map(key => (
                    <TextField
                        key={key}
                        label={key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        name={key}
                        value={form[key]}
                        onChange={handleChange}
                        required={key !== 'budget' && key !== 'program' && key !== 'url'}
                        size="small"
                    />
                ))}
                <Button type="submit" variant="contained" disabled={loading} sx={{ mt: 2 }}>
                    {loading ? <CircularProgress size={24} /> : 'Submit'}
                </Button>
            </Box>
            {result && (
                <Box sx={{ mt: 3 }}>
                    <Typography variant="h6">Score: {result.score}%</Typography>
                    <Typography variant="subtitle1">Recommended Partners:</Typography>
                    <ul>
                        {result.recommended_partners.map((p, i) => (
                            <li key={i}><a href={p.website} target="_blank" rel="noopener noreferrer">{p.name}</a></li>
                        ))}
                    </ul>
                </Box>
            )}
        </Paper>
    );
} 