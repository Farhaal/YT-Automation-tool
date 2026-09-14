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

import { waitFor } from '@testing-library/react';
import EditorView from './EditorView';

describe('EditorView Interactions', () => {
  it('handles polling and websocket completion, backup swap, and editing', async () => {
    // Mock fetch for initial job load, then polling, then timeline
    let fetchCount = 0;
    global.fetch = async (url) => {
      if (url.toString().includes('timeline')) {
        return {
          json: async () => ({
            audio: { duration: 10 },
            scenes: [
              { id: 's1', start: 0, end: 5, text: 'scene1', asset: { source: 'pexels' }, backup_asset: { source: 'pixabay' } }
            ],
            captions: [{ word: 'test', start: 0, end: 1 }],
            popups: []
          })
        } as Response;
      }
      
      // Simulate progressing -> completed
      fetchCount++;
      if (fetchCount === 1) {
        return { json: async () => ({ status: 'PROCESSING', progress: 50, stage: 'Segmenting' }) } as Response;
      }
      return { json: async () => ({ status: 'COMPLETED', timeline_path: 'ok' }) } as Response;
    };

    // Mock WebSocket
    class MockWS {
      onmessage: any = null;
      close = () => {};
      constructor() {
        setTimeout(() => {
          if (this.onmessage) {
             this.onmessage({ data: JSON.stringify({ status: 'COMPLETED', timeline_path: 'ok' }) });
          }
        }, 100);
      }
    }
    (global as any).WebSocket = MockWS;

    const { getByText, findByText, getByRole, getAllByRole, getByPlaceholderText } = render(<EditorView jobId="123" />);
    
    // Check progressing state
    await waitFor(() => expect(getByText(/Generating Video/i)).toBeInTheDocument());
    
    // Wait for completion and timeline to load
    await waitFor(() => expect(getByText(/Draft Preview/i)).toBeInTheDocument(), { timeout: 2000 });
    
    // Backup swap
    expect(getByText('pexels')).toBeInTheDocument();
    fireEvent.click(getByText(/Swap Backup/i));
    expect(getByText('pixabay')).toBeInTheDocument();
    
    // Edit caption
    const capInput = getAllByRole('textbox')[0]; // The first one might be caption
    fireEvent.change(capInput, { target: { value: 'edited' } });
    expect(capInput).toHaveValue('edited');
    
    // Add popup
    fireEvent.click(getByText(/\+ Add Popup Overlay/i));
    await waitFor(() => expect(getByPlaceholderText(/Text Callout/i)).toBeInTheDocument());
    
    // Test motion dropdown
    const selects = getAllByRole('combobox');
    // Finds the Motion select (first select in the scene block usually)
    const motionSelect = selects.find(s => s.innerHTML.includes('Ken Burns In'));
    if (motionSelect) {
      fireEvent.change(motionSelect, { target: { value: 'kenburns_in' } });
      expect(motionSelect).toHaveValue('kenburns_in');
    }
    
    // Test Re-render / Save payload
    let putPayload = null;
    global.fetch = async (url, options) => {
      if (options?.method === 'PUT' && url.toString().includes('timeline')) {
        putPayload = JSON.parse(options.body as string);
        return { ok: true } as Response;
      }
      return { ok: true, json: async () => ({}) } as Response;
    };
    
    fireEvent.click(getByText(/Re-render Draft/i));
    await waitFor(() => expect(putPayload).not.toBeNull());
    
    expect(putPayload.scenes[0].motion).toBe('kenburns_in');
    expect(putPayload.captions[0].word).toBe('edited');
    expect(putPayload.popups.length).toBe(1);
    expect(putPayload.popups[0].type).toBe('text');
  });
});
