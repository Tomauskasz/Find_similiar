import { useEffect, useRef, useState } from 'react';

const DEFAULT_POLL_INTERVAL = 1000;
const MAX_POLL_INTERVAL = 5000;

function getNextDelay(attempt) {
  return Math.min(MAX_POLL_INTERVAL, DEFAULT_POLL_INTERVAL * attempt);
}

export default function useBackendStats(apiClient) {
  const [backendReady, setBackendReady] = useState(false);
  const [backendStats, setBackendStats] = useState(null);
  const [backendAttempts, setBackendAttempts] = useState(0);
  const [backendError, setBackendError] = useState(null);
  const timeoutRef = useRef(null);
  const cancelledRef = useRef(false);

  useEffect(() => {
    async function checkBackend(attempt = 1) {
      if (cancelledRef.current) return;
      setBackendAttempts(attempt);
      setBackendError(null);
      try {
        const response = await apiClient.get('/stats', { timeout: 3000 });
        if (!cancelledRef.current) {
          setBackendReady(true);
          setBackendStats(response.data);
        }
      } catch (err) {
        if (cancelledRef.current) return;
        setBackendReady(false);
        setBackendError(err.message ?? 'Backend unavailable');
        const nextAttempt = attempt + 1;
        timeoutRef.current = setTimeout(() => checkBackend(nextAttempt), getNextDelay(nextAttempt));
      }
    }

    cancelledRef.current = false;
    checkBackend(1);

    return () => {
      cancelledRef.current = true;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [apiClient]);

  return {
    backendReady,
    backendStats,
    backendAttempts,
    backendError,
  };
}
