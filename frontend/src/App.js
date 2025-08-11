import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import { SnackbarProvider } from 'notistack';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Container from '@mui/material/Container';
import Dashboard from './pages/Dashboard';
import SubmitOpportunity from './pages/SubmitOpportunity';
import Reports from './pages/Reports';
import Partners from './pages/Partners';
import Login from './pages/Login';
import Signup from './pages/Signup';
import ResetPassword from './pages/ResetPassword';
import { AuthProvider, useAuth } from './AuthContext';
import CircularProgress from '@mui/material/CircularProgress';
import Admin from './pages/Admin';

function ProtectedRoute({ children }) {
    const { user, loading } = useAuth();
    if (loading) return <Container sx={{ mt: 4, textAlign: 'center' }}><CircularProgress /></Container>;
    if (!user) return <Navigate to="/login" />;
    return children;
}

function AppBarWithAuth() {
    const { user, role, logout } = useAuth();
    return (
        <AppBar position="static">
            <Toolbar>
                <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
                    Consultancy Automation
                </Typography>
                <Button color="inherit" component={Link} to="/">Dashboard</Button>
                <Button color="inherit" component={Link} to="/submit">Submit</Button>
                <Button color="inherit" component={Link} to="/reports">Reports</Button>
                <Button color="inherit" component={Link} to="/partners">Partners</Button>
                {role === 'admin' && (
                    <Button color="inherit" component={Link} to="/admin">Admin</Button>
                )}
                {user ? (
                    <>
                        <Typography sx={{ ml: 2, mr: 1 }}>{user.username} ({role})</Typography>
                        <Button color="inherit" onClick={logout}>Logout</Button>
                    </>
                ) : (
                    <>
                        <Button color="inherit" component={Link} to="/login">Login</Button>
                        <Button color="inherit" component={Link} to="/signup">Sign Up</Button>
                    </>
                )}
            </Toolbar>
        </AppBar>
    );
}

function AppRoutes() {
    return (
        <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/submit" element={<ProtectedRoute><SubmitOpportunity /></ProtectedRoute>} />
            <Route path="/reports" element={<ProtectedRoute><Reports /></ProtectedRoute>} />
            <Route path="/partners" element={<ProtectedRoute><Partners /></ProtectedRoute>} />
            <Route path="/admin" element={<ProtectedRoute><Admin /></ProtectedRoute>} />
        </Routes>
    );
}

function App() {
    return (
        <AuthProvider>
            <SnackbarProvider maxSnack={3} autoHideDuration={3000}>
                <Router>
                    <AppBarWithAuth />
                    <Container sx={{ mt: 4 }}>
                        <AppRoutes />
                    </Container>
                </Router>
            </SnackbarProvider>
        </AuthProvider>
    );
}

export default App; 