# v3 dev results (all variants, ranked by F1; selection rule below)

| variant | P | R | TP/FP/FN |
|---|---|---|---|
| minimax-m3 · strict | 1.0 | 0.5 | 1/0/1 |
| minimax-m3 · strict_or_evasive | 1.0 | 0.5 | 1/0/1 |
| minimax-m3 · depth_close | 1.0 | 0.5 | 1/0/1 |
| minimax-m3 · strict_pet1.5 | 1.0 | 0.5 | 1/0/1 |
| v2 AND qwen3.6-35b · strict | 1.0 | 0.5 | 1/0/1 |
| v2 AND qwen3.6-35b · strict_or_evasive | 1.0 | 0.5 | 1/0/1 |
| v2 AND qwen3.6-35b · depth_close | 1.0 | 0.5 | 1/0/1 |
| v2 AND qwen3.6-35b · strict_pet1.5 | 1.0 | 0.5 | 1/0/1 |
| vote2of3[qwen3.8-27b+gemma-4-26b+minimax-m3] · strict | 1.0 | 0.5 | 1/0/1 |
| vote2of3[gemma-4-26b+minimax-m3+gemma-4-31b] · strict | 1.0 | 0.5 | 1/0/1 |
| vote2of3[qwen3.8-27b+gemma-4-26b+minimax-m3] · strict_or_evasive | 1.0 | 0.5 | 1/0/1 |
| vote2of3[gemma-4-26b+minimax-m3+gemma-4-31b] · strict_or_evasive | 1.0 | 0.5 | 1/0/1 |
| vote2of3[qwen3.8-27b+gemma-4-26b+minimax-m3] · depth_close | 1.0 | 0.5 | 1/0/1 |
| vote2of3[gemma-4-26b+minimax-m3+gemma-4-31b] · depth_close | 1.0 | 0.5 | 1/0/1 |
| vote2of3[qwen3.8-27b+gemma-4-26b+minimax-m3] · strict_pet1.5 | 1.0 | 0.5 | 1/0/1 |
| vote2of3[gemma-4-26b+minimax-m3+gemma-4-31b] · strict_pet1.5 | 1.0 | 0.5 | 1/0/1 |
| vote2of3[qwen3.6-35b+minimax-m3+gemma-4-31b] · strict | 0.4 | 1.0 | 2/3/0 |
| vote2of3[qwen3.6-35b+minimax-m3+gemma-4-31b] · strict_or_evasive | 0.4 | 1.0 | 2/3/0 |
| vote2of3[qwen3.6-35b+minimax-m3+gemma-4-31b] · depth_close | 0.4 | 1.0 | 2/3/0 |
| vote2of3[qwen3.6-35b+minimax-m3+gemma-4-31b] · strict_pet1.5 | 0.4 | 1.0 | 2/3/0 |
| vote2of3[qwen3.6-35b+qwen3.8-27b+minimax-m3] · strict_pet1.5 | 0.33 | 1.0 | 2/4/0 |
| vote2of3[qwen3.6-35b+qwen3.8-27b+minimax-m3] · strict | 0.29 | 1.0 | 2/5/0 |
| vote2of3[qwen3.6-35b+qwen3.8-27b+minimax-m3] · strict_or_evasive | 0.29 | 1.0 | 2/5/0 |
| vote2of3[qwen3.6-35b+qwen3.8-27b+minimax-m3] · depth_close | 0.29 | 1.0 | 2/5/0 |
| v2 AND qwen3.8-27b · strict | 0.33 | 0.5 | 1/2/1 |
| v2 AND qwen3.8-27b · strict_or_evasive | 0.33 | 0.5 | 1/2/1 |
| v2 AND qwen3.8-27b · depth_close | 0.33 | 0.5 | 1/2/1 |
| v2 AND qwen3.8-27b · strict_pet1.5 | 0.33 | 0.5 | 1/2/1 |
| v2 AND gemma-4-31b · strict | 0.33 | 0.5 | 1/2/1 |
| v2 AND gemma-4-31b · strict_or_evasive | 0.33 | 0.5 | 1/2/1 |
| v2 AND gemma-4-31b · depth_close | 0.33 | 0.5 | 1/2/1 |
| v2 AND gemma-4-31b · strict_pet1.5 | 0.33 | 0.5 | 1/2/1 |
| vote2of3[kimi-k2.6+qwen3.8-27b+minimax-m3] · strict | 0.33 | 0.5 | 1/2/1 |
| vote2of3[kimi-k2.6+minimax-m3+gemma-4-31b] · strict | 0.33 | 0.5 | 1/2/1 |
| vote2of3[kimi-k2.6+qwen3.8-27b+minimax-m3] · strict_or_evasive | 0.33 | 0.5 | 1/2/1 |
| vote2of3[kimi-k2.6+minimax-m3+gemma-4-31b] · strict_or_evasive | 0.33 | 0.5 | 1/2/1 |
| vote2of3[kimi-k2.6+qwen3.8-27b+minimax-m3] · depth_close | 0.33 | 0.5 | 1/2/1 |
| vote2of3[kimi-k2.6+minimax-m3+gemma-4-31b] · depth_close | 0.33 | 0.5 | 1/2/1 |
| vote2of3[kimi-k2.6+qwen3.8-27b+minimax-m3] · strict_pet1.5 | 0.33 | 0.5 | 1/2/1 |
| vote2of3[kimi-k2.6+minimax-m3+gemma-4-31b] · strict_pet1.5 | 0.33 | 0.5 | 1/2/1 |
| vote2of3[kimi-k2.6+qwen3.8-27b+gemma-4-31b] · strict | 0.22 | 1.0 | 2/7/0 |
| vote2of3[qwen3.8-27b+gemma-4-26b+gemma-4-31b] · strict | 0.22 | 1.0 | 2/7/0 |
| vote2of3[qwen3.8-27b+minimax-m3+gemma-4-31b] · strict | 0.22 | 1.0 | 2/7/0 |
| vote2of3[kimi-k2.6+qwen3.8-27b+gemma-4-31b] · strict_or_evasive | 0.22 | 1.0 | 2/7/0 |
| vote2of3[qwen3.8-27b+gemma-4-26b+gemma-4-31b] · strict_or_evasive | 0.22 | 1.0 | 2/7/0 |
| vote2of3[qwen3.8-27b+minimax-m3+gemma-4-31b] · strict_or_evasive | 0.22 | 1.0 | 2/7/0 |
| vote2of3[kimi-k2.6+qwen3.8-27b+gemma-4-31b] · depth_close | 0.22 | 1.0 | 2/7/0 |
| vote2of3[qwen3.8-27b+gemma-4-26b+gemma-4-31b] · depth_close | 0.22 | 1.0 | 2/7/0 |
| vote2of3[qwen3.8-27b+minimax-m3+gemma-4-31b] · depth_close | 0.22 | 1.0 | 2/7/0 |
| vote2of3[kimi-k2.6+qwen3.8-27b+gemma-4-31b] · strict_pet1.5 | 0.22 | 1.0 | 2/7/0 |
| vote2of3[qwen3.8-27b+gemma-4-26b+gemma-4-31b] · strict_pet1.5 | 0.22 | 1.0 | 2/7/0 |
| vote2of3[qwen3.8-27b+minimax-m3+gemma-4-31b] · strict_pet1.5 | 0.22 | 1.0 | 2/7/0 |
| vote2of3[qwen3.6-35b+gemma-4-26b+gemma-4-31b] · strict | 0.25 | 0.5 | 1/3/1 |
| vote2of3[qwen3.6-35b+gemma-4-26b+gemma-4-31b] · strict_or_evasive | 0.25 | 0.5 | 1/3/1 |
| vote2of3[qwen3.6-35b+gemma-4-26b+gemma-4-31b] · depth_close | 0.25 | 0.5 | 1/3/1 |
| vote2of3[qwen3.6-35b+gemma-4-26b+gemma-4-31b] · strict_pet1.5 | 0.25 | 0.5 | 1/3/1 |
| gemma-4-31b · strict | 0.2 | 1.0 | 2/8/0 |
| gemma-4-31b · strict_or_evasive | 0.2 | 1.0 | 2/8/0 |
| gemma-4-31b · depth_close | 0.2 | 1.0 | 2/8/0 |
| gemma-4-31b · strict_pet1.5 | 0.2 | 1.0 | 2/8/0 |
| vote2of3[qwen3.6-35b+qwen3.8-27b+gemma-4-31b] · strict_pet1.5 | 0.2 | 1.0 | 2/8/0 |
| qwen3.8-27b · strict_pet1.5 | 0.18 | 1.0 | 2/9/0 |
| vote2of3[qwen3.6-35b+qwen3.8-27b+gemma-4-31b] · strict | 0.18 | 1.0 | 2/9/0 |
| vote2of3[qwen3.6-35b+qwen3.8-27b+gemma-4-31b] · strict_or_evasive | 0.18 | 1.0 | 2/9/0 |
| vote2of3[qwen3.6-35b+qwen3.8-27b+gemma-4-31b] · depth_close | 0.18 | 1.0 | 2/9/0 |
| v2 | 0.2 | 0.5 | 1/4/1 |
| qwen3.6-35b · strict_pet1.5 | 0.2 | 0.5 | 1/4/1 |
| vote2of3[qwen3.6-35b+kimi-k2.6+gemma-4-31b] · strict | 0.2 | 0.5 | 1/4/1 |
| vote2of3[qwen3.6-35b+kimi-k2.6+gemma-4-31b] · strict_or_evasive | 0.2 | 0.5 | 1/4/1 |
| vote2of3[qwen3.6-35b+kimi-k2.6+gemma-4-31b] · depth_close | 0.2 | 0.5 | 1/4/1 |
| vote2of3[qwen3.6-35b+kimi-k2.6+gemma-4-31b] · strict_pet1.5 | 0.2 | 0.5 | 1/4/1 |
| vote2of3[qwen3.6-35b+qwen3.8-27b+gemma-4-26b] · strict_pet1.5 | 0.2 | 0.5 | 1/4/1 |
| qwen3.8-27b · strict | 0.15 | 1.0 | 2/11/0 |
| qwen3.8-27b · strict_or_evasive | 0.15 | 1.0 | 2/11/0 |
| qwen3.8-27b · depth_close | 0.15 | 1.0 | 2/11/0 |
| qwen3.6-35b · strict | 0.17 | 0.5 | 1/5/1 |
| qwen3.6-35b · strict_or_evasive | 0.17 | 0.5 | 1/5/1 |
| qwen3.6-35b · depth_close | 0.17 | 0.5 | 1/5/1 |
| vote2of3[qwen3.6-35b+qwen3.8-27b+gemma-4-26b] · strict | 0.17 | 0.5 | 1/5/1 |
| vote2of3[qwen3.6-35b+qwen3.8-27b+gemma-4-26b] · strict_or_evasive | 0.17 | 0.5 | 1/5/1 |
| vote2of3[qwen3.6-35b+qwen3.8-27b+gemma-4-26b] · depth_close | 0.17 | 0.5 | 1/5/1 |
| vote2of3[qwen3.6-35b+kimi-k2.6+qwen3.8-27b] · strict_pet1.5 | 0.17 | 0.5 | 1/5/1 |
| kinematic-only (no model) | 0.14 | 0.5 | 1/6/1 |
| vote2of3[qwen3.6-35b+kimi-k2.6+qwen3.8-27b] · strict | 0.14 | 0.5 | 1/6/1 |
| vote2of3[qwen3.6-35b+kimi-k2.6+qwen3.8-27b] · strict_or_evasive | 0.14 | 0.5 | 1/6/1 |
| vote2of3[qwen3.6-35b+kimi-k2.6+qwen3.8-27b] · depth_close | 0.14 | 0.5 | 1/6/1 |
| v1 | 0.0 | 0.0 | 0/3/2 |
| gemma-4-26b@risk >= 3 | None | 0.0 | 0/0/2 |
| gemma-4-26b@risk >= 4 | None | 0.0 | 0/0/2 |
| gemma-4-26b@risk >= 5 | None | 0.0 | 0/0/2 |
| gemma-4-26b@risk >= 6 | None | 0.0 | 0/0/2 |
| gemma-4-26b@risk >= 7 | None | 0.0 | 0/0/2 |
| gemma-4-26b@risk >= 8 | None | 0.0 | 0/0/2 |
| gemma-4-26b@risk >= 9 | None | 0.0 | 0/0/2 |
| gemma-4-31b@risk >= 3 | None | 0.0 | 0/0/2 |
| gemma-4-31b@risk >= 4 | None | 0.0 | 0/0/2 |
| gemma-4-31b@risk >= 5 | None | 0.0 | 0/0/2 |
| gemma-4-31b@risk >= 6 | None | 0.0 | 0/0/2 |
| gemma-4-31b@risk >= 7 | None | 0.0 | 0/0/2 |
| gemma-4-31b@risk >= 8 | None | 0.0 | 0/0/2 |
| gemma-4-31b@risk >= 9 | None | 0.0 | 0/0/2 |
| qwen3.6-35b@risk >= 3 | None | 0.0 | 0/0/2 |
| qwen3.6-35b@risk >= 4 | None | 0.0 | 0/0/2 |
| qwen3.6-35b@risk >= 5 | None | 0.0 | 0/0/2 |
| qwen3.6-35b@risk >= 6 | None | 0.0 | 0/0/2 |
| qwen3.6-35b@risk >= 7 | None | 0.0 | 0/0/2 |
| qwen3.6-35b@risk >= 8 | None | 0.0 | 0/0/2 |
| qwen3.6-35b@risk >= 9 | None | 0.0 | 0/0/2 |
| qwen3.6-35b · evasive_only | None | 0.0 | 0/0/2 |
| kimi-k2.6 · strict | 0.0 | 0.0 | 0/2/2 |
| kimi-k2.6 · strict_or_evasive | 0.0 | 0.0 | 0/2/2 |
| kimi-k2.6 · depth_close | 0.0 | 0.0 | 0/2/2 |
| kimi-k2.6 · strict_pet1.5 | 0.0 | 0.0 | 0/2/2 |
| kimi-k2.6 · evasive_only | 0.0 | 0.0 | 0/1/2 |
| qwen3.8-27b · evasive_only | None | 0.0 | 0/0/2 |
| gemma-4-26b · strict | None | 0.0 | 0/0/2 |
| gemma-4-26b · strict_or_evasive | None | 0.0 | 0/0/2 |
| gemma-4-26b · depth_close | None | 0.0 | 0/0/2 |
| gemma-4-26b · strict_pet1.5 | None | 0.0 | 0/0/2 |
| gemma-4-26b · evasive_only | None | 0.0 | 0/0/2 |
| minimax-m3 · evasive_only | None | 0.0 | 0/0/2 |
| gemma-4-31b · evasive_only | None | 0.0 | 0/0/2 |
| v2 AND qwen3.6-35b · evasive_only | None | 0.0 | 0/0/2 |
| v2 AND kimi-k2.6 · strict | 0.0 | 0.0 | 0/1/2 |
| v2 AND kimi-k2.6 · strict_or_evasive | 0.0 | 0.0 | 0/1/2 |
| v2 AND kimi-k2.6 · depth_close | 0.0 | 0.0 | 0/1/2 |
| v2 AND kimi-k2.6 · strict_pet1.5 | 0.0 | 0.0 | 0/1/2 |
| v2 AND kimi-k2.6 · evasive_only | 0.0 | 0.0 | 0/1/2 |
| v2 AND qwen3.8-27b · evasive_only | None | 0.0 | 0/0/2 |
| v2 AND gemma-4-26b · strict | None | 0.0 | 0/0/2 |
| v2 AND gemma-4-26b · strict_or_evasive | None | 0.0 | 0/0/2 |
| v2 AND gemma-4-26b · depth_close | None | 0.0 | 0/0/2 |
| v2 AND gemma-4-26b · strict_pet1.5 | None | 0.0 | 0/0/2 |
| v2 AND gemma-4-26b · evasive_only | None | 0.0 | 0/0/2 |
| v2 AND minimax-m3 · strict | None | 0.0 | 0/0/2 |
| v2 AND minimax-m3 · strict_or_evasive | None | 0.0 | 0/0/2 |
| v2 AND minimax-m3 · depth_close | None | 0.0 | 0/0/2 |
| v2 AND minimax-m3 · strict_pet1.5 | None | 0.0 | 0/0/2 |
| v2 AND minimax-m3 · evasive_only | None | 0.0 | 0/0/2 |
| v2 AND gemma-4-31b · evasive_only | None | 0.0 | 0/0/2 |
| vote2of3[qwen3.6-35b+kimi-k2.6+gemma-4-26b] · strict | 0.0 | 0.0 | 0/1/2 |
| vote2of3[qwen3.6-35b+kimi-k2.6+minimax-m3] · strict | 0.0 | 0.0 | 0/1/2 |
| vote2of3[qwen3.6-35b+gemma-4-26b+minimax-m3] · strict | None | 0.0 | 0/0/2 |
| vote2of3[kimi-k2.6+qwen3.8-27b+gemma-4-26b] · strict | 0.0 | 0.0 | 0/2/2 |
| vote2of3[kimi-k2.6+gemma-4-26b+minimax-m3] · strict | None | 0.0 | 0/0/2 |
| vote2of3[kimi-k2.6+gemma-4-26b+gemma-4-31b] · strict | 0.0 | 0.0 | 0/2/2 |
| vote2of3[qwen3.6-35b+kimi-k2.6+gemma-4-26b] · strict_or_evasive | 0.0 | 0.0 | 0/1/2 |
| vote2of3[qwen3.6-35b+kimi-k2.6+minimax-m3] · strict_or_evasive | 0.0 | 0.0 | 0/1/2 |
| vote2of3[qwen3.6-35b+gemma-4-26b+minimax-m3] · strict_or_evasive | None | 0.0 | 0/0/2 |
| vote2of3[kimi-k2.6+qwen3.8-27b+gemma-4-26b] · strict_or_evasive | 0.0 | 0.0 | 0/2/2 |
| vote2of3[kimi-k2.6+gemma-4-26b+minimax-m3] · strict_or_evasive | None | 0.0 | 0/0/2 |
| vote2of3[kimi-k2.6+gemma-4-26b+gemma-4-31b] · strict_or_evasive | 0.0 | 0.0 | 0/2/2 |
| vote2of3[qwen3.6-35b+kimi-k2.6+gemma-4-26b] · depth_close | 0.0 | 0.0 | 0/1/2 |
| vote2of3[qwen3.6-35b+kimi-k2.6+minimax-m3] · depth_close | 0.0 | 0.0 | 0/1/2 |
| vote2of3[qwen3.6-35b+gemma-4-26b+minimax-m3] · depth_close | None | 0.0 | 0/0/2 |
| vote2of3[kimi-k2.6+qwen3.8-27b+gemma-4-26b] · depth_close | 0.0 | 0.0 | 0/2/2 |
| vote2of3[kimi-k2.6+gemma-4-26b+minimax-m3] · depth_close | None | 0.0 | 0/0/2 |
| vote2of3[kimi-k2.6+gemma-4-26b+gemma-4-31b] · depth_close | 0.0 | 0.0 | 0/2/2 |
| vote2of3[qwen3.6-35b+kimi-k2.6+gemma-4-26b] · strict_pet1.5 | 0.0 | 0.0 | 0/1/2 |
| vote2of3[qwen3.6-35b+kimi-k2.6+minimax-m3] · strict_pet1.5 | 0.0 | 0.0 | 0/1/2 |
| vote2of3[qwen3.6-35b+gemma-4-26b+minimax-m3] · strict_pet1.5 | None | 0.0 | 0/0/2 |
| vote2of3[kimi-k2.6+qwen3.8-27b+gemma-4-26b] · strict_pet1.5 | 0.0 | 0.0 | 0/2/2 |
| vote2of3[kimi-k2.6+gemma-4-26b+minimax-m3] · strict_pet1.5 | None | 0.0 | 0/0/2 |
| vote2of3[kimi-k2.6+gemma-4-26b+gemma-4-31b] · strict_pet1.5 | 0.0 | 0.0 | 0/2/2 |
| vote2of3[qwen3.6-35b+kimi-k2.6+qwen3.8-27b] · evasive_only | None | 0.0 | 0/0/2 |
| vote2of3[qwen3.6-35b+kimi-k2.6+gemma-4-26b] · evasive_only | None | 0.0 | 0/0/2 |
| vote2of3[qwen3.6-35b+kimi-k2.6+minimax-m3] · evasive_only | None | 0.0 | 0/0/2 |
| vote2of3[qwen3.6-35b+kimi-k2.6+gemma-4-31b] · evasive_only | None | 0.0 | 0/0/2 |
| vote2of3[qwen3.6-35b+qwen3.8-27b+gemma-4-26b] · evasive_only | None | 0.0 | 0/0/2 |
| vote2of3[qwen3.6-35b+qwen3.8-27b+minimax-m3] · evasive_only | None | 0.0 | 0/0/2 |
| vote2of3[qwen3.6-35b+qwen3.8-27b+gemma-4-31b] · evasive_only | None | 0.0 | 0/0/2 |
| vote2of3[qwen3.6-35b+gemma-4-26b+minimax-m3] · evasive_only | None | 0.0 | 0/0/2 |
| vote2of3[qwen3.6-35b+gemma-4-26b+gemma-4-31b] · evasive_only | None | 0.0 | 0/0/2 |
| vote2of3[qwen3.6-35b+minimax-m3+gemma-4-31b] · evasive_only | None | 0.0 | 0/0/2 |
| vote2of3[kimi-k2.6+qwen3.8-27b+gemma-4-26b] · evasive_only | None | 0.0 | 0/0/2 |
| vote2of3[kimi-k2.6+qwen3.8-27b+minimax-m3] · evasive_only | None | 0.0 | 0/0/2 |
| vote2of3[kimi-k2.6+qwen3.8-27b+gemma-4-31b] · evasive_only | None | 0.0 | 0/0/2 |
| vote2of3[kimi-k2.6+gemma-4-26b+minimax-m3] · evasive_only | None | 0.0 | 0/0/2 |
| vote2of3[kimi-k2.6+gemma-4-26b+gemma-4-31b] · evasive_only | None | 0.0 | 0/0/2 |
| vote2of3[kimi-k2.6+minimax-m3+gemma-4-31b] · evasive_only | None | 0.0 | 0/0/2 |
| vote2of3[qwen3.8-27b+gemma-4-26b+minimax-m3] · evasive_only | None | 0.0 | 0/0/2 |
| vote2of3[qwen3.8-27b+gemma-4-26b+gemma-4-31b] · evasive_only | None | 0.0 | 0/0/2 |
| vote2of3[qwen3.8-27b+minimax-m3+gemma-4-31b] · evasive_only | None | 0.0 | 0/0/2 |
| vote2of3[gemma-4-26b+minimax-m3+gemma-4-31b] · evasive_only | None | 0.0 | 0/0/2 |
