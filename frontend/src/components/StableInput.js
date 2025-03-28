import React, { useEffect, useRef, useState } from 'react';
import { TextField } from '@mui/material';

/**
 * A stable input component that manages its own state internally
 * and only updates parent state on completion to prevent re-renders
 * 
 * @param {Object} props - Component props
 * @param {string} props.value - The controlled value from parent
 * @param {Function} props.onChange - Parent change handler
 * @param {Function} props.onSubmit - Optional submit handler
 * @param {boolean} props.updateOnBlur - Whether to update parent on blur (default: false)
 * @param {number} props.debounceTime - Debounce time in ms (default: 300)
 * @returns {React.ReactElement} Stable input component
 */
const StableInput = (props) => {
  const {
    value: externalValue,
    onChange,
    onSubmit,
    updateOnBlur = false,
    debounceTime = 300,
    ...otherProps
  } = props;
  
  // Use refs to avoid re-renders
  const inputRef = useRef(null);
  const internalValueRef = useRef(externalValue || '');
  const timeoutRef = useRef(null);
  
  // Use state only for forcing renders when absolutely needed
  const [, forceRender] = useState({});
  
  // Sync internal value with external value when it changes from outside
  useEffect(() => {
    if (externalValue !== undefined && externalValue !== internalValueRef.current) {
      internalValueRef.current = externalValue;
      // Force a render to show the new value
      forceRender({});
    }
  }, [externalValue]);
  
  // Handle internal change without triggering parent updates
  const handleChange = (e) => {
    const newValue = e.target.value;
    internalValueRef.current = newValue;
    
    // Force render to update the visible value
    forceRender({});
    
    // Clear any existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    
    // Set a new timeout for debouncing
    timeoutRef.current = setTimeout(() => {
      if (onChange && internalValueRef.current !== externalValue) {
        const syntheticEvent = {
          target: { value: internalValueRef.current },
          preventDefault: () => {},
          stopPropagation: () => {}
        };
        onChange(syntheticEvent);
      }
    }, debounceTime);
  };
  
  // Handle blur event
  const handleBlur = (e) => {
    if (updateOnBlur && onChange && internalValueRef.current !== externalValue) {
      const syntheticEvent = {
        target: { value: internalValueRef.current },
        preventDefault: () => {},
        stopPropagation: () => {}
      };
      onChange(syntheticEvent);
    }
    
    if (props.onBlur) {
      props.onBlur(e);
    }
  };
  
  // Handle key press for submission
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && onSubmit) {
      e.preventDefault();
      onSubmit(internalValueRef.current);
    }
    
    if (props.onKeyPress) {
      props.onKeyPress(e);
    }
  };
  
  // Clean up timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);
  
  return (
    <TextField
      {...otherProps}
      inputRef={inputRef}
      value={internalValueRef.current}
      onChange={handleChange}
      onBlur={handleBlur}
      onKeyPress={handleKeyPress}
      autoComplete="off"
      InputProps={{
        ...otherProps.InputProps,
        autoComplete: 'off',
        spellCheck: 'false'
      }}
    />
  );
};

export default StableInput; 