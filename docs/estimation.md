# Estimation model

## Observations and epochs

For each window, a sample may contain:

```text
timestamp, received_at, used_percent, reset_at, duration_minutes,
cumulative_usage, usage_unit, model, estimated_credits, cost_usd,
input_tokens, cached_input_tokens, output_tokens, provider, limit_id
```

Unavailable fields remain `null`. A sample is only fitted when its cumulative usage has a known, compatible unit. Provider, source signature, and limit identity must remain stable within the fit.

A new epoch starts when the limit identity changes, reset time changes materially, or official usage falls from a high value to near zero. Old/duplicate samples are ignored; completed epochs are retained.

## Robust fit

The model is:

```text
C = a + bP
```

where `C` is cumulative usage and `P` is official used percentage. For every pair of valid samples whose percentage differs by more than 0.25 points:

```text
b_ij = (C_j - C_i) / (P_j - P_i)
```

The fitted slope `b` is the median of all pairwise slopes. The intercept `a` is the median of `C_i - bP_i`. It is deliberately not forced to zero, so monitoring can begin midway through a cycle.

The estimated total is:

```text
Q = 100b
used = Q × P_current / 100
remaining = max(0, Q - used)
```

The app does not use `current cumulative / current percentage × 100` as its long-term estimator.

## Warm-up and availability

- No valid cumulative usage: **Unavailable**.
- Less than 5.0 percentage points of valid span: **Calibrating**.
- At least 5.0 points but fewer than three valid samples: **Unavailable**, with the reason shown.
- Non-positive or non-finite robust slope: **Unavailable**.
- Stable identity, sufficient span, at least three samples, and positive slope: **Estimated**.

When completed historical epochs exist, their median can be shown during current-cycle warm-up, clearly labeled as historical rather than current.

## Confidence score

The 0–100 score combines:

| Component | Weight | Construction |
|---|---:|---|
| Sample count | 18% | saturates after roughly ten samples |
| Percentage span | 22% | saturates at 40 points |
| Residual quality | 20% | MAD and 90th-percentile residual tail relative to usage range |
| Slope consistency | 15% | MAD and 90th-percentile pairwise-slope deviation |
| Completeness | 10% | valid cumulative usage fraction |
| Freshness | 8% | decays to zero at the stale threshold |
| Transport delay | 7% | decays over five minutes |

Missing model information applies a small penalty. More than one observed model applies a larger penalty and adds a warning that credit-to-quota conversion may be model-dependent. Scores are capped at 70 with fewer than four samples, 60 below 10 points of span, and 25 when stale.

Labels are Low below 45, Medium from 45, High from 70, and Very High from 85.

## Likely range and precision

The lower and upper range uses the 10th and 90th percentiles of pairwise slopes, widened by robust residual scale and a 0.5-percentage-point rounding allowance. Values are rounded by magnitude so the UI does not imply false decimal precision.

This is an engineering uncertainty range, not a formal probabilistic confidence interval.

## Historical baseline and change detection

At least two completed ready epochs with the same unit form a baseline:

```text
center = median(completed totals)
spread = 1.4826 × MAD(completed totals)
```

A possible quota change is raised only when the current estimate has confidence of at least 75, differs by at least 10%, and exceeds both twice the robust historical spread and 2% of the baseline. Early-cycle noise cannot trigger the alert.

## Unit limitations

The current App Server account-usage response exposes a lifetime token counter but not a per-window quota-credit ledger, per-model token split, estimated credits, or USD cost. Therefore the active estimator reports **tokens**. Tokens are not renamed as quota credits, API-equivalent USD, or subscription price.
