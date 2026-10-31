export function formatNumber(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'N/A';
  return Number(value).toLocaleString(undefined, {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  });
}

export function shortTime(value) {
  if (!value) return 'N/A';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function mapDecisionPreview(preview) {
  const decision = preview?.decision;
  const state = preview?.state;
  if (!decision || !state) {
    return {
      situation: 'No deterministic backend decision is loaded yet.',
      options: [{ label: 'Do Nothing', impact: '0 MW' }],
      selected: 'Do Nothing',
      duration: 'current replay interval',
      expectedImpact: 0,
      explanation: 'The API state has not been loaded.',
    };
  }

  const actions = decision.actions?.length
    ? decision.actions
    : [{ action: decision.action?.action, estimated_saving_MW: 0 }];

  return {
    situation: decision.opportunity?.reason ?? 'No opportunity information returned.',
    options: actions.map((action) => ({
      label: action.action,
      impact: `${formatNumber(action.estimated_saving_MW ?? 0)} MW`,
      validation: action.validation,
    })),
    selected: decision.action?.action ?? 'Do Nothing',
    duration: 'current replay interval',
    expectedImpact: Number(decision.action?.estimated_saving_MW ?? 0),
    explanation: [
      `Opportunity: ${decision.opportunity?.type ?? 'UNKNOWN'}.`,
      `Safety: ${decision.selected_validation?.safety_status ?? 'NOT_APPLICABLE'}.`,
      'The selected action and impact come from the deterministic Python agent and what-if engine.',
    ].join(' '),
    opportunity: decision.opportunity,
    state,
  };
}

export function mapDecisionRecord(record) {
  const executed = record.Execution_Status === 'SUCCESS' || record.Execution_Status === 'SIMULATED';
  return {
    id: `${record.Decision_Timestamp}-${record.Action}`,
    time: shortTime(record.Decision_Timestamp),
    situation: record.Opportunity_Reason,
    selected: record.Selected_Action,
    expectedImpact: Number(record.What_If_Estimated_Impact_MW ?? 0),
    status: executed ? 'EXECUTED (SIMULATED)' : record.Control_Origin === 'AGENT_RECOMMENDATION_ONLY' ? 'RECOMMENDATION ONLY' : record.Execution_Status,
    safetyStatus: record.Safety_Status,
    verificationStatus: record.Verification_Status,
    ruleId: record.Rule_ID,
    simulationResult: {
      before: record.Load_Before_MW,
      after: record.Load_After_MW,
    },
    explanation: record.Impact_Semantics,
    executionReason: record.Rejection_Reason ?? (executed ? 'Safety checks passed and the simulated adapter verified the result.' : record.Control_Origin === 'AGENT_RECOMMENDATION_ONLY' ? 'Agent control was OFF or device AI control was disabled.' : 'No execution was recorded.'),
    raw: record,
  };
}
