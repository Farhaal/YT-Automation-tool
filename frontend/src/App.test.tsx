import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import App from './App';
import SettingsView from './SettingsView';
import CreatorView from './CreatorView';

describe('Frontend Component Tests', () => {
  it('renders CreatorView correctly with script flow and upload', () => {
    const { getByText, getByPlaceholderText } = render(<CreatorView onJobCreated={() => {}} />);
    expect(getByText(/Or generate from Script/i)).toBeInTheDocument();
    expect(getByText(/Upload Narration Audio/i)).toBeInTheDocument();
    
    const textarea = getByPlaceholderText(/Paste your script here/i);
    fireEvent.change(textarea, { target: { value: 'Test script' } });
    expect(textarea).toHaveValue('Test script');
  });

  it('SettingsView handles provider status properly and masks inputs', () => {
    const { getByPlaceholderText, getByText } = render(<SettingsView />);
    expect(getByText(/Provider Settings/i)).toBeInTheDocument();
    
    // Inputs should be password fields to mask keys
    const pexelsInput = getByPlaceholderText(/Enter Pexels Key/i) as HTMLInputElement;
    expect(pexelsInput.type).toBe('password');
    
    const pixabayInput = getByPlaceholderText(/Enter Pixabay Key/i) as HTMLInputElement;
    expect(pixabayInput.type).toBe('password');
    
    // Free providers listed
    expect(getByText(/Openverse & Wikimedia/i)).toBeInTheDocument();
  });
});
