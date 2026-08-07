"""
The evaluation dataset. Each entry is (question, role, ground_truth) —
ground_truth is a reference answer used by Ragas's context_recall metric
and (indirectly) as a sanity check on faithfulness/relevancy.

HONESTY NOTE: these ground truths were written by checking the actual
source documents directly (grep'd during this phase), not guessed from
memory — but "I checked it once" is not the same bar as "a human on this
project has verified this is exactly the reference answer we want." Per
standard practice, a golden eval set deserves real human review before
you trust CI thresholds (Phase 11) against it. Treat this as a solid
first draft, not a finished golden set — read through it once yourself
before it gates your CI.

Kept intentionally small (10 examples) for this phase — the point is to
get the evaluation MECHANISM working correctly first. Expanding to the
50-200 examples a real golden set needs is a good next iteration once
you've confirmed this works end to end.
"""

EVAL_EXAMPLES = [
    {
        "question": "What is FinSolve's annual leave entitlement?",
        "role": "hr",
        "ground_truth": "Employees get 15-21 days of privilege/annual leave per year, accrued monthly, as per the state Shops & Establishments Act.",
    },
    {
        "question": "How many sick leave days do employees get per year?",
        "role": "hr",
        "ground_truth": "Employees get 12 days of sick leave per year, non-cumulative. A medical certificate is required for sick leave longer than 2 days.",
    },
    {
        "question": "What was FinSolve's Q1 2024 revenue?",
        "role": "finance",
        "ground_truth": "Q1 2024 revenue was $2.1 billion, up 22% year-over-year.",
    },
    {
        "question": "How did FinSolve's revenue change over the course of 2024?",
        "role": "finance",
        "ground_truth": "Revenue increased from $2.1 billion in Q1 to $2.6 billion in Q4 2024, with consistent year-over-year growth across all quarters.",
    },
    {
        "question": "What frontend technologies does FinSolve's engineering team use?",
        "role": "engineering",
        "ground_truth": "The frontend stack uses React 18, Redux Toolkit, and Tailwind CSS, with TypeScript, React Query, and D3.js as supporting technologies.",
    },
    {
        "question": "How much did new customer acquisition grow in 2024 according to marketing?",
        "role": "marketing",
        "ground_truth": "New customer acquisition grew by 20% year-over-year in 2024, outpacing the industry average of 10% growth.",
    },
    {
        "question": "What was the ROI on FinSolve's InstantWire Global Expansion campaign?",
        "role": "marketing",
        "ground_truth": "The InstantWire Global Expansion campaign achieved a 3.5x return on investment, generating $17.5M in revenue from $5M spent.",
    },
    {
        "question": "What maternity leave benefits does FinSolve offer?",
        "role": "marketing",  # any role works here — maternity leave is in the general handbook, visible to everyone
        "ground_truth": "FinSolve offers 26 weeks of paid maternity leave for the first two children, and 12 weeks for subsequent children.",
    },
    {
        "question": "What is the process for applying for leave?",
        "role": "engineering",
        "ground_truth": "Leave is applied for via the HRMS/leave portal at least 3 days in advance, except in emergencies, and requires approval from the reporting manager and HR.",
    },
    {
        "question": "What insurance benefits does FinSolve provide employees?",
        "role": "finance",
        "ground_truth": "FinSolve provides group health insurance (family floater covering employee, spouse, and up to 2 children) and additional accident & life insurance for accidental death or disability.",
    },
]