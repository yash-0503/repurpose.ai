export default function StepIndicator({ currentStep }) {
  const steps = [
    { number: 1, label: 'Input' },
    { number: 2, label: 'Process' },
    { number: 3, label: 'Output' },
  ];

  const getStepClass = (stepNumber) => {
    if (stepNumber < currentStep) return 'step completed';
    if (stepNumber === currentStep) return 'step active';
    return 'step';
  };

  return (
    <div className="step-indicator">
      {steps.map((step) => (
        <div key={step.number} className={getStepClass(step.number)}>
          <div className="step-circle">
            {step.number < currentStep ? '✓' : step.number}
          </div>
          <span className="step-label">{step.label}</span>
          <div className="step-line" />
        </div>
      ))}
    </div>
  );
}

