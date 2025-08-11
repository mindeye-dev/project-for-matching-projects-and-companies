import React, { useState } from 'react';
import { useAuth } from '../AuthContext';
import { useNavigate } from 'react-router-dom';
import { TextField, Button, Paper, Typography, Box } from '@mui/material';
import { useSnackbar } from 'notistack';

export default function Login() {
    const { login } = useAuth();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const { enqueueSnackbar } = useSnackbar();
    const navigate = useNavigate();

    const handleSubmit = async e => {
        e.preventDefault();
        setLoading(true);
        try {
            await login(username, password);
            enqueueSnackbar('Login successful!', { variant: 'success' });
            navigate('/');
        } catch (err) {
            enqueueSnackbar('Login failed. Check your credentials.', { variant: 'error' });
        }
        setLoading(false);
    };

    return (
        <Paper sx={{ p: 3, maxWidth: 400, margin: 'auto' }}>
            <Typography variant="h5" gutterBottom>Login</Typography>
            <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <TextField label="Username" value={username} onChange={e => setUsername(e.target.value)} required size="small" />
                <TextField label="Password" type="password" value={password} onChange={e => setPassword(e.target.value)} required size="small" />
                <Button type="submit" variant="contained" disabled={loading}>{loading ? 'Logging in...' : 'Login'}</Button>
            </Box>
        </Paper>
    );
} 