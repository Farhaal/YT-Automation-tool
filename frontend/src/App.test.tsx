import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent, waitFor } from '@testing-library/react';
import CreatorView from './CreatorView';
import SettingsView from './SettingsView';
import EditorView from './EditorView';
import { ToastProvider } from './ui';

describe('Frontend Component Tests', () => {
  
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(async () => {
      return { json: async () => ({}) };
    }));
  });

  it('renders CreatorView correctly with script flow and upload', () => {
    const { getByText, getByPlaceholderText } = render(
      <ToastProvider>
        <CreatorView onJobCreated={() => {}} />
      </ToastProvider>
    );
    expect(getByText(/From Script/i)).not.toBeNull();
    expect(getByText(/From Audio/i)).not.toBeNull();
    
    const textarea = getByPlaceholderText(/Start writing your script here/i);
    fireEvent.change(textarea, { target: { value: 'Test script' } });
    expect((textarea as HTMLTextAreaElement).value).toBe('Test script');
  });

  it('SettingsView handles provider status properly and masks inputs', async () => {
    const { getAllByPlaceholderText, getByText } = render(
      <ToastProvider>
        <SettingsView />
      </ToastProvider>
    );
    
    await waitFor(() => {
      expect(getByText(/Stock Media/i)).not.toBeNull();
    });
    
    // Inputs should be password fields to mask keys
    const pexelsInputs = getAllByPlaceholderText(/Enter Key/i);
    expect(pexelsInputs.length).toBeGreaterThan(0);
    expect((pexelsInputs[0] as HTMLInputElement).type).toBe('password');
    
    expect(getByText(/Openverse & Wikimedia/i)).not.toBeNull();
  });
});

describe('EditorView Interactions', () => {
  it('renders properly and shows loader without job', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => {
      return { json: async () => ({ status: 'PROCESSING', progress: 50, stage: 'Segmenting' }) };
    }));

    class MockWS {
      onmessage: any = null;
      close = () => {};
    }
    vi.stubGlobal('WebSocket', MockWS);

    const { getByText } = render(
      <ToastProvider>
        <EditorView jobId="123" />
      </ToastProvider>
    );
    
    await waitFor(() => {
      expect(getByText(/Generating Video/i)).not.toBeNull();
    });
  });
});
