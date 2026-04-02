import { create } from 'zustand';

const useDocumentStore = create((set) => ({
  documents: [],
  selectedDoc: null,
  vizData: null,
  loading: false,
  error: null,
  viewerOpen: false,
  activeHighlight: null,

  setDocuments: (docs) => set({ documents: docs }),
  
  setSelectedDoc: (doc) => set({ selectedDoc: doc }),
  
  setVizData: (data) => set({ vizData: data }),
  
  setLoading: (loading) => set({ loading }),
  
  setError: (error) => set({ error }),
  
  setViewerOpen: (open) => set({ viewerOpen: open }),
  
  setActiveHighlight: (highlight) => set({ activeHighlight: highlight }),
  
  resetViz: () => set({ 
    selectedDoc: null, 
    vizData: null, 
    activeHighlight: null, 
    viewerOpen: false,
    error: null 
  }),
}));

export default useDocumentStore;
