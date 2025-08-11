import React, { useState } from 'react';
import axios from 'axios';
import { TextField, Button, Paper, Typography, Box } from '@mui/material';
import { useSnackbar } from 'notistack';

export default function ResetPassword() {
    const [username, setUsername] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const { enqueueSnackbar } = useSnackbar();

    const handleSubmit = async e => {
        e.preventDefault();
        setLoading(true);
        try {
            await axios.post('/api/auth/reset_password', { username, new_password: newPassword });
            enqueueSnackbar('Password reset successful!', { variant: 'success' });
        } catch (err) {
            enqueueSnackbar('Password reset failed.', { variant: 'error' });
        }
        setLoading(false);
    };

    return (
        <Paper sx={{ p: 3, maxWidth: 400, margin: 'auto' }}>
            <Typography variant="h5" gutterBottom>Reset Password</Typography>
            <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <TextField label="Username" value={username} onChange={e => setUsername(e.target.value)} required size="small" />
                <TextField label="New Password" type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} required size="small" />
                <Button type="submit" variant="contained" disabled={loading}>{loading ? 'Resetting...' : 'Reset Password'}</Button>
            </Box>
        </Paper>
    );
} 