
import { useCallback, useState } from 'react';

export default function useSearchResults() {
  const [rawResults, setRawResults] = useState([]);
  const [visibleCount, setVisibleCount] = useState(0);
  const [totalMatches, setTotalMatches] = useState(0);

  const filterResults = useCallback(
    (confidence) => rawResults.filter((result) => result.similarity_score >= confidence),
    [rawResults]
  );

  const loadMore = useCallback(
    (pageSize, confidence) => {
      const matches = filterResults(confidence).length;
      setVisibleCount((count) => Math.min(count + pageSize, matches));
    },
    [filterResults]
  );

  return {
    rawResults,
    setRawResults,
    getFilteredResults: filterResults,
    visibleCount,
    setVisibleCount,
    totalMatches,
    setTotalMatches,
    loadMore,
  };
}
