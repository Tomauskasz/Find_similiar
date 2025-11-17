import { useCallback, useEffect, useRef, useState } from 'react';

const DEFAULT_TOTALS = {
  items: [],
  totalItems: 0,
  totalPages: 0,
};

export default function useCatalog(apiClient, { enabled = true, page = 1, pageSize = 40 } = {}) {
  const [items, setItems] = useState(DEFAULT_TOTALS.items);
  const [totalItems, setTotalItems] = useState(DEFAULT_TOTALS.totalItems);
  const [totalPages, setTotalPages] = useState(DEFAULT_TOTALS.totalPages);
  const [loading, setLoading] = useState(false);
  const [error, setErrorMessage] = useState(null);

  const isMountedRef = useRef(true);
  const latestRequestRef = useRef(0);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const resetTotals = useCallback(() => {
    setItems(DEFAULT_TOTALS.items);
    setTotalItems(DEFAULT_TOTALS.totalItems);
    setTotalPages(DEFAULT_TOTALS.totalPages);
  }, []);

  const fetchCatalog = useCallback(async () => {
    if (!enabled) {
      resetTotals();
      setLoading(false);
      setErrorMessage(null);
      return;
    }

    const requestId = latestRequestRef.current + 1;
    latestRequestRef.current = requestId;

    setLoading(true);
    setErrorMessage(null);

    try {
      const response = await apiClient.get('/catalog/items', {
        params: { page, page_size: pageSize },
      });
      if (!isMountedRef.current || latestRequestRef.current !== requestId) {
        return;
      }
      setItems(response.data.items || []);
      setTotalItems(response.data.total_items || 0);
      setTotalPages(response.data.total_pages || 0);
    } catch (err) {
      if (!isMountedRef.current || latestRequestRef.current !== requestId) {
        return;
      }
      setErrorMessage(err.response?.data?.detail || 'Failed to load catalog.');
    } finally {
      if (isMountedRef.current && latestRequestRef.current === requestId) {
        setLoading(false);
      }
    }
  }, [apiClient, enabled, page, pageSize, resetTotals]);

  useEffect(() => {
    fetchCatalog();
  }, [fetchCatalog]);

  return {
    items,
    totalItems,
    totalPages,
    loading,
    error,
    refreshCatalog: fetchCatalog,
    setErrorMessage,
  };
}
