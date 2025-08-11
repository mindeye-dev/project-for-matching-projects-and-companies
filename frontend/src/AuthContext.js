import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext();

export function useAuth() {
    return useContext(AuthContext);
}

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(localStorage.getItem('token'));
    const [role, setRole] = useState(localStorage.getItem('role'));
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (token) {
            axios.get('/api/auth/me', { headers: { Authorization: `Bearer ${token}` } })
                .then(res => {
                    setUser(res.data);
                    setRole(res.data.role);
                    localStorage.setItem('role', res.data.role);
                })
                .catch(() => {
                    setUser(null);
                    setToken(null);
                    setRole(null);
                    localStorage.removeItem('token');
                    localStorage.removeItem('role');
                })
                .finally(() => setLoading(false));
        } else {
            setLoading(false);
        }
    }, [token]);

    const login = async (username, password) => {
        const res = await axios.post('/api/auth/login', { username, password });
        setToken(res.data.access_token);
        setRole(res.data.role);
        localStorage.setItem('token', res.data.access_token);
        localStorage.setItem('role', res.data.role);
        const me = await axios.get('/api/auth/me', { headers: { Authorization: `Bearer ${res.data.access_token}` } });
        setUser(me.data);
    };

    const signup = async (username, password) => {
        await axios.post('/api/auth/register', { username, password });
        await login(username, password);
    };

    const logout = () => {
        setUser(null);
        setToken(null);
        setRole(null);
        localStorage.removeItem('token');
        localStorage.removeItem('role');
    };

    return (
        <AuthContext.Provider value={{ user, token, role, login, logout, signup, loading }}>
            {children}
        </AuthContext.Provider>
    );
} 