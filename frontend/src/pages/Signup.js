import React, { useState } from 'react';
import { useAuth } from '../AuthContext';
import { useNavigate } from 'react-router-dom';
import { TextField, Button, Paper, Typography, Box } from '@mui/material';
import { useSnackbar } from 'notistack';

export default function Signup() {
    const { signup } = useAuth();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const { enqueueSnackbar } = useSnackbar();
    const navigate = useNavigate();

    const handleSubmit = async e => {
        e.preventDefault();
        setLoading(true);
        try {
            await signup(username, password);
            enqueueSnackbar('Signup successful!', { variant: 'success' });
            navigate('/');
        } catch (err) {
            enqueueSnackbar('Signup failed. Username may already exist.', { variant: 'error' });
        }
        setLoading(false);
    };

    return (
        <Paper sx={{ p: 3, maxWidth: 400, margin: 'auto' }}>
            <Typography variant="h5" gutterBottom>Sign Up</Typography>
            <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <TextField label="Username" value={username} onChange={e => setUsername(e.target.value)} required size="small" />
                <TextField label="Password" type="password" value={password} onChange={e => setPassword(e.target.value)} required size="small" />
                <Button type="submit" variant="contained" disabled={loading}>{loading ? 'Signing up...' : 'Sign Up'}</Button>
            </Box>
        </Paper>
    );
} 