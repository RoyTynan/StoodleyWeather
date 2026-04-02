/**
 * @jest-environment jsdom
 *
 * Component tests for MainContent.
 *
 * These tests verify the two most important UI behaviours:
 *   1. When IndexedDB holds no data, clicking a view button shows a status message.
 *   2. While a fetch request is in flight, the fetch button is disabled.
 *
 * IndexedDB (weather-db) and fetch are both mocked — no real browser storage
 * or network calls are made. The jsdom environment provides a simulated DOM.
 *
 * To run:
 *   npm test
 *   npm test -- --testPathPattern=main-content.test   (this file only)
 */
import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import MainContent from './main-content';
import { loadWeatherData, saveWeatherData } from '../lib/weather-db';

jest.mock('../lib/weather-db');

const mockLoad = loadWeatherData as jest.MockedFunction<typeof loadWeatherData>;
const mockSave = saveWeatherData as jest.MockedFunction<typeof saveWeatherData>;

describe('MainContent', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // loadWeatherData returns null when IndexedDB has no saved data.
  // Clicking Show Rain (or any view button) should display a prompt to fetch first.
  it('shows status message when storage is empty and a view button is clicked', async () => {
    mockLoad.mockResolvedValue(null);

    render(<MainContent />);
    fireEvent.click(screen.getByText('Show Rain'));

    await waitFor(() => {
      expect(
        screen.getByText('No weather data in storage. Fetch it first.')
      ).toBeInTheDocument();
    });
  });

  // The fetch button must be disabled while a request is pending to prevent
  // duplicate API calls. A never-resolving promise simulates a slow request.
  // console.error is suppressed — the mock returns a 500 which the catch block logs.
  // settle() is wrapped in act() so React can flush the resulting state updates cleanly.
  it('disables the fetch button while a request is in flight', async () => {
    jest.spyOn(console, 'error').mockImplementation(() => {});
    let settle: () => void;
    const pending = new Promise<Response>((resolve) => {
      settle = () => resolve({ ok: false, status: 500 } as Response);
    });
    global.fetch = jest.fn().mockReturnValue(pending);
    mockSave.mockResolvedValue(undefined);

    render(<MainContent />);
    fireEvent.click(screen.getByText('Get Weather Data'));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Fetching...' })).toBeDisabled();
    });

    await act(async () => { settle!(); });
    jest.restoreAllMocks();
  });
});
