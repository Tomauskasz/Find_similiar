import { useCallback, useMemo, useState } from 'react';

export default function useConfidence(initialValue = 0.8) {
  const [confidence, setConfidence] = useState(initialValue);
  const [sliderValue, setSliderValue] = useState(initialValue);
  const [lastSearchConfidence, setLastSearchConfidence] = useState(initialValue);

  const sliderDirty = Math.abs(sliderValue - confidence) > 0.0001;
  const sliderPercent = useMemo(() => Math.round(sliderValue * 100), [sliderValue]);
  const appliedConfidencePercent = useMemo(() => Math.round(confidence * 100), [confidence]);

  const handleSliderChange = useCallback((event) => {
    setSliderValue(parseFloat(event.target.value));
  }, []);

  const commitSlider = useCallback(() => {
    setConfidence((current) => {
      if (Math.abs(sliderValue - current) < 0.0001) {
        return current;
      }
      return sliderValue;
    });
  }, [sliderValue]);

  const markSearchConfidence = useCallback((value) => {
    setLastSearchConfidence(value);
  }, []);

  const syncBackendConfidence = useCallback((value) => {
    setConfidence(value);
    setSliderValue(value);
    setLastSearchConfidence(value);
  }, []);

  return {
    confidence,
    sliderValue,
    sliderPercent,
    appliedConfidencePercent,
    sliderDirty,
    lastSearchConfidence,
    setSliderValue,
    setConfidence,
    handleSliderChange,
    commitSlider,
    markSearchConfidence,
    syncBackendConfidence,
  };
}
