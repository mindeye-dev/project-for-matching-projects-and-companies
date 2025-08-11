import React, { useState, useEffect } from 'react';
import { useAuth } from '../AuthContext';
import { useNavigate } from 'react-router-dom';
import {
    TextField, Button, Paper, Typography, Box, Table, TableBody, TableCell, TableHead, TableRow,
    Select, MenuItem, FormControl, InputLabel, Checkbox, IconButton, Tooltip, Chip
} from '@mui/material';
import { Delete as DeleteIcon } from '@mui/icons-material';
import { useSnackbar } from 'notistack';
import axios from 'axios';

export default function Admin() {
    const { role } = useAuth();
    const navigate = useNavigate();
    const { enqueueSnackbar } = useSnackbar();
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [newUser, setNewUser] = useState({ username: '', password: '', role: 'user' });
    const [selectedUsers, setSelectedUsers] = useState([]);
    const [bulkRole, setBulkRole] = useState('user');

    useEffect(() => {
        if (role !== 'admin') {
            navigate('/');
            return;
        }
        fetchUsers();
    }, [role, navigate]);

    const fetchUsers = async () => {
        setLoading(true);
        try {
            const res = await axios.get('/api/auth/admin/users');
            setUsers(res.data);
        } catch (err) {
            enqueueSnackbar('Failed to fetch users.', { variant: 'error' });
        }
        setLoading(false);
    };

    const handleCreateUser = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            await axios.post('/api/auth/admin/create_user', newUser);
            enqueueSnackbar('User created successfully!', { variant: 'success' });
            setNewUser({ username: '', password: '', role: 'user' });
            fetchUsers();
        } catch (err) {
            enqueueSnackbar('Failed to create user.', { variant: 'error' });
        }
        setLoading(false);
    };

    const handleUpdateRole = async (username, newRole) => {
        try {
            await axios.put(`/api/auth/admin/users/${username}/role`, { role: newRole });
            enqueueSnackbar('Role updated successfully!', { variant: 'success' });
            fetchUsers();
        } catch (err) {
            enqueueSnackbar('Failed to update role.', { variant: 'error' });
        }
    };

    const handleDeleteUser = async (username) => {
        if (!window.confirm(`Are you sure you want to delete user "${username}"?`)) {
            return;
        }
        try {
            await axios.delete(`/api/auth/admin/users/${username}`);
            enqueueSnackbar('User deleted successfully!', { variant: 'success' });
            fetchUsers();
        } catch (err) {
            enqueueSnackbar('Failed to delete user.', { variant: 'error' });
        }
    };

    const handleBulkRoleUpdate = async () => {
        if (selectedUsers.length === 0) {
            enqueueSnackbar('Please select users first.', { variant: 'warning' });
            return;
        }
        try {
            await axios.put('/api/auth/admin/users/bulk_role', {
                usernames: selectedUsers,
                role: bulkRole
            });
            enqueueSnackbar('Bulk role update successful!', { variant: 'success' });
            setSelectedUsers([]);
            fetchUsers();
        } catch (err) {
            enqueueSnackbar('Failed to update roles.', { variant: 'error' });
        }
    };

    const handleBulkDelete = async () => {
        if (selectedUsers.length === 0) {
            enqueueSnackbar('Please select users first.', { variant: 'warning' });
            return;
        }
        if (!window.confirm(`Are you sure you want to delete ${selectedUsers.length} users?`)) {
            return;
        }
        try {
            await axios.delete('/api/auth/admin/users/bulk_delete', {
                data: { usernames: selectedUsers }
            });
            enqueueSnackbar('Bulk delete successful!', { variant: 'success' });
            setSelectedUsers([]);
            fetchUsers();
        } catch (err) {
            enqueueSnackbar('Failed to delete users.', { variant: 'error' });
        }
    };

    const handleSelectUser = (username) => {
        setSelectedUsers(prev =>
            prev.includes(username)
                ? prev.filter(u => u !== username)
                : [...prev, username]
        );
    };

    const handleSelectAll = () => {
        if (selectedUsers.length === users.length) {
            setSelectedUsers([]);
        } else {
            setSelectedUsers(users.map(u => u.username));
        }
    };

    const formatDate = (dateString) => {
        if (!dateString) return 'Never';
        return new Date(dateString).toLocaleString();
    };

    if (role !== 'admin') {
        return null;
    }

    return (
        <Paper sx={{ p: 3 }}>
            <Typography variant="h5" gutterBottom>Admin Panel</Typography>

            {/* Create User Form */}
            <Box sx={{ mb: 4 }}>
                <Typography variant="h6" gutterBottom>Create New User</Typography>
                <Box component="form" onSubmit={handleCreateUser} sx={{ display: 'flex', flexDirection: 'column', gap: 2, maxWidth: 400 }}>
                    <TextField
                        label="Username"
                        value={newUser.username}
                        onChange={e => setNewUser({ ...newUser, username: e.target.value })}
                        required
                        size="small"
                    />
                    <TextField
                        label="Password"
                        type="password"
                        value={newUser.password}
                        onChange={e => setNewUser({ ...newUser, password: e.target.value })}
                        required
                        size="small"
                    />
                    <FormControl size="small">
                        <InputLabel>Role</InputLabel>
                        <Select
                            value={newUser.role}
                            onChange={e => setNewUser({ ...newUser, role: e.target.value })}
                            label="Role"
                        >
                            <MenuItem value="user">User</MenuItem>
                            <MenuItem value="admin">Admin</MenuItem>
                        </Select>
                    </FormControl>
                    <Button type="submit" variant="contained" disabled={loading}>
                        {loading ? 'Creating...' : 'Create User'}
                    </Button>
                </Box>
            </Box>

            {/* Bulk Operations */}
            {selectedUsers.length > 0 && (
                <Box sx={{ mb: 3, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
                    <Typography variant="h6" gutterBottom>
                        Bulk Operations ({selectedUsers.length} selected)
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                        <FormControl size="small">
                            <InputLabel>Set Role</InputLabel>
                            <Select
                                value={bulkRole}
                                onChange={e => setBulkRole(e.target.value)}
                                label="Set Role"
                            >
                                <MenuItem value="user">User</MenuItem>
                                <MenuItem value="admin">Admin</MenuItem>
                            </Select>
                        </FormControl>
                        <Button variant="contained" onClick={handleBulkRoleUpdate}>
                            Update Roles
                        </Button>
                        <Button variant="contained" color="error" onClick={handleBulkDelete}>
                            Delete Selected
                        </Button>
                    </Box>
                </Box>
            )}

            {/* Users Table */}
            <Box>
                <Typography variant="h6" gutterBottom>All Users</Typography>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell padding="checkbox">
                                <Checkbox
                                    checked={selectedUsers.length === users.length && users.length > 0}
                                    indeterminate={selectedUsers.length > 0 && selectedUsers.length < users.length}
                                    onChange={handleSelectAll}
                                />
                            </TableCell>
                            <TableCell>Username</TableCell>
                            <TableCell>Role</TableCell>
                            <TableCell>Created</TableCell>
                            <TableCell>Last Login</TableCell>
                            <TableCell>Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {users.map((user) => (
                            <TableRow key={user.username}>
                                <TableCell padding="checkbox">
                                    <Checkbox
                                        checked={selectedUsers.includes(user.username)}
                                        onChange={() => handleSelectUser(user.username)}
                                    />
                                </TableCell>
                                <TableCell>{user.username}</TableCell>
                                <TableCell>
                                    <Chip
                                        label={user.role}
                                        color={user.role === 'admin' ? 'primary' : 'default'}
                                        size="small"
                                    />
                                </TableCell>
                                <TableCell>{formatDate(user.created_at)}</TableCell>
                                <TableCell>{formatDate(user.last_login)}</TableCell>
                                <TableCell>
                                    <Box sx={{ display: 'flex', gap: 1 }}>
                                        <FormControl size="small">
                                            <Select
                                                value={user.role}
                                                onChange={(e) => handleUpdateRole(user.username, e.target.value)}
                                                size="small"
                                            >
                                                <MenuItem value="user">User</MenuItem>
                                                <MenuItem value="admin">Admin</MenuItem>
                                            </Select>
                                        </FormControl>
                                        <Tooltip title="Delete User">
                                            <IconButton
                                                size="small"
                                                color="error"
                                                onClick={() => handleDeleteUser(user.username)}
                                            >
                                                <DeleteIcon />
                                            </IconButton>
                                        </Tooltip>
                                    </Box>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </Box>
        </Paper>
    );
} 