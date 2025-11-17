import { useState } from 'react';

const VALID_VIEWS = ['search', 'catalog'];

export default function useCatalogView(initialView = 'search') {
  const [activeView, setActiveView] = useState(initialView);

  const selectView = (view) => {
    setActiveView(VALID_VIEWS.includes(view) ? view : initialView);
  };

  return [activeView, selectView];
}
