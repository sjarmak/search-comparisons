import React, { createContext, useState, useContext, useEffect } from 'react';

/**
 * Authentication context for managing login state
 */
const AuthContext = createContext(null);

/**
 * Default password that will be used for authentication
 * We use an environment variable to avoid storing the password in the codebase
 * If no environment variable is set, a placeholder value is used
 */
export const DEFAULT_PASSWORD = process.env.REACT_APP_AUTH_PASSWORD || 'default-password-placeholder';

/**
 * Provider component for the AuthContext
 * 
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Child components
 * @returns {React.ReactElement} AuthProvider component
 */
export const AuthProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  // Check local storage for authentication on component mount
  useEffect(() => {
    const checkAuth = () => {
      const authStatus = localStorage.getItem('isAuthenticated');
      if (authStatus === 'true') {
        setIsAuthenticated(true);
      }
      setLoading(false);
    };

    checkAuth();
  }, []);

  /**
   * Handle successful login
   */
  const login = () => {
    setIsAuthenticated(true);
    localStorage.setItem('isAuthenticated', 'true');
  };

  /**
   * Handle logout
   */
  const logout = () => {
    setIsAuthenticated(false);
    localStorage.removeItem('isAuthenticated');
  };

  // Provide authentication state and methods to children
  return (
    <AuthContext.Provider value={{ isAuthenticated, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

/**
 * Custom hook to use the authentication context
 * 
 * @returns {Object} Authentication context
 */
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext; 