import React, { useState } from 'react';
import { 
  Box, 
  Paper, 
  Typography, 
  Button, 
  Alert,
  Container,
  InputAdornment,
  IconButton
} from '@mui/material';
import { Visibility, VisibilityOff, LockOutlined } from '@mui/icons-material';
import StableInput from './StableInput';

/**
 * Login component for password protection
 * 
 * @param {Object} props - Component props
 * @param {Function} props.onLogin - Function to call when login is successful
 * @param {string} props.correctPassword - The correct password to check against
 * @param {string} props.appTitle - The title of the application
 */
const Login = ({ onLogin, correctPassword, appTitle = "Academic Search Engine Comparisons" }) => {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  /**
   * Handle password submission
   * 
   * @param {Event} e - Form submission event
   */
  const handleSubmit = (e) => {
    e.preventDefault();
    // Check if password is correct
    if (password === correctPassword) {
      // Call the onLogin function to update authentication state
      onLogin();
    } else {
      setError('Incorrect password. Please try again.');
      // Clear password field on error
      setPassword('');
    }
  };

  /**
   * Toggle password visibility
   */
  const handleClickShowPassword = () => {
    setShowPassword(!showPassword);
  };

  /**
   * Handle password change
   * 
   * @param {Event} e - Change event
   */
  const handlePasswordChange = (e) => {
    setPassword(e.target.value);
  };

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
        }}
      >
        <Paper
          elevation={3}
          sx={{
            p: 4,
            width: '100%',
            maxWidth: 400,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <LockOutlined sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
          <Typography variant="h5" component="h1" gutterBottom>
            {appTitle}
          </Typography>
          <Typography variant="body1" sx={{ mb: 3 }}>
            This page is password protected
          </Typography>

          {error && (
            <Alert severity="error" sx={{ width: '100%', mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit} sx={{ width: '100%' }}>
            <StableInput
              variant="outlined"
              margin="normal"
              required
              fullWidth
              name="password"
              label="Password"
              type={showPassword ? 'text' : 'password'}
              id="password"
              value={password}
              onChange={handlePasswordChange}
              onSubmit={() => handleSubmit({ preventDefault: () => {} })}
              debounceTime={50}
              updateOnBlur={true}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      aria-label="toggle password visibility"
                      onClick={handleClickShowPassword}
                      edge="end"
                    >
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                )
              }}
              sx={{ mb: 2 }}
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              color="primary"
              sx={{ mt: 2, mb: 2 }}
            >
              Sign In
            </Button>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
};

export default Login; 