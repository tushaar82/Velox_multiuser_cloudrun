import { useState, useEffect } from 'react';
import { Box, Alert, CircularProgress } from '@mui/material';
import CurrentLossDisplay from './CurrentLossDisplay';
import MaxLossLimitModal from './MaxLossLimitModal';
import LossLimitBreachModal from './LossLimitBreachModal';
import { apiClient } from '../../services/api';
import type { TradingMode, RiskLimits } from '../../types';

interface RiskManagementPanelProps {
  accountId: string;
  tradingMode: TradingMode;
  onLimitUpdated?: () => void;
}

export default function RiskManagementPanel({
  accountId,
  tradingMode,
  onLimitUpdated,
}: RiskManagementPanelProps) {
  const [riskLimits, setRiskLimits] = useState<RiskLimits | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [showEditModal, setShowEditModal] = useState(false);
  const [showBreachModal, setShowBreachModal] = useState(false);

  const fetchRiskLimits = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await apiClient.getRiskLimits(accountId, tradingMode);
      setRiskLimits(data);
      
      // Show breach modal if limit is breached and not yet acknowledged
      if (data.isBreached && !data.acknowledged) {
        setShowBreachModal(true);
      }
    } catch (err: any) {
      if (err.response?.status === 404) {
        // No limits set yet - this is expected for new accounts
        setRiskLimits(null);
      } else {
        setError(err.response?.data?.message || 'Failed to load risk limits');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRiskLimits();
    
    // Poll for updates every 5 seconds
    const interval = setInterval(fetchRiskLimits, 5000);
    return () => clearInterval(interval);
  }, [accountId, tradingMode]);

  const handleSaveLimit = async (limit: number) => {
    try {
      await apiClient.setMaxLossLimit(accountId, tradingMode, limit);
      setShowEditModal(false);
      await fetchRiskLimits();
      onLimitUpdated?.();
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to set loss limit');
    }
  };

  const handleAcknowledgeBreach = async (newLimit?: number) => {
    try {
      await apiClient.acknowledgeLimitBreach(accountId, tradingMode, newLimit);
      setShowBreachModal(false);
      await fetchRiskLimits();
      onLimitUpdated?.();
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to acknowledge breach');
    }
  };

  if (loading && !riskLimits) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!riskLimits) {
    return (
      <Alert severity="info" sx={{ mb: 2 }}>
        No loss limit configured for {tradingMode === 'paper' ? 'paper' : 'live'} trading mode.
        Set a limit before activating strategies.
      </Alert>
    );
  }

  return (
    <Box>
      <CurrentLossDisplay
        riskLimits={riskLimits}
        tradingMode={tradingMode}
        onEditLimit={() => setShowEditModal(true)}
      />

      <MaxLossLimitModal
        open={showEditModal}
        tradingMode={tradingMode}
        currentLimit={riskLimits.maxLossLimit}
        onClose={() => setShowEditModal(false)}
        onSave={handleSaveLimit}
      />

      {riskLimits.isBreached && !riskLimits.acknowledged && (
        <LossLimitBreachModal
          open={showBreachModal}
          tradingMode={tradingMode}
          currentLimit={riskLimits.maxLossLimit}
          currentLoss={riskLimits.currentLoss}
          onClose={() => setShowBreachModal(false)}
          onAcknowledge={handleAcknowledgeBreach}
        />
      )}
    </Box>
  );
}
