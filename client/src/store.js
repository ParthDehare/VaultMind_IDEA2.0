import { create } from 'zustand';

export const useAppStore = create((set, get) => {
  const createSetter = (key) => (valOrFn) => 
    set(state => ({ [key]: typeof valOrFn === 'function' ? valOrFn(state[key]) : valOrFn }));

  return {
    theme: 'dark',
    setTheme: createSetter('theme'),

    page: 'command',
    setPage: createSetter('page'),

    profileSearch: '',
    setProfileSearch: createSetter('profileSearch'),

    rosterPage: 1,
    setRosterPage: createSetter('rosterPage'),

    rosterSearch: '',
    setRosterSearch: createSetter('rosterSearch'),

    rosterRole: 'ALL',
    setRosterRole: createSetter('rosterRole'),

    rosterTier: 'ALL',
    setRosterTier: createSetter('rosterTier'),

    graphSearch: '',
    setGraphSearch: createSetter('graphSearch'),

    selectedNode: null,
    setSelectedNode: createSetter('selectedNode'),

    scoredTxns: [],
    setScoredTxns: createSetter('scoredTxns'),

    employeeMetadata: {},
    setEmployeeMetadata: createSetter('employeeMetadata'),

    isLoadingInitial: true,
    setIsLoadingInitial: createSetter('isLoadingInitial'),

    autoRefresh: true,
    setAutoRefresh: createSetter('autoRefresh'),

    evidencePage: 1,
    setEvidencePage: createSetter('evidencePage'),

    newEvidenceIds: new Set(),
    setNewEvidenceIds: createSetter('newEvidenceIds'),

    vaultEvidence: [],
    setVaultEvidence: createSetter('vaultEvidence'),

    confirmedIncidents: [],
    setConfirmedIncidents: createSetter('confirmedIncidents'),

    falseAlarms: [],
    setFalseAlarms: createSetter('falseAlarms'),

    generateTarget: '',
    setGenerateTarget: createSetter('generateTarget'),

    isGeneratingDossier: false,
    setIsGeneratingDossier: createSetter('isGeneratingDossier'),
  };
});
