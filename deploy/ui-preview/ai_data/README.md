# Preview-only synthetic forecasting input

`new_data.csv` contains 128 fabricated daily records from 2026-07-01 through 2026-11-05. No operational DB or original historical CSV was copied. Counts use deterministic weekday/weekend variations: breakfast `40 + i%9 - weekend*10`, lunch `210 + i%21 - weekend*40`, dinner `130 + i%17 - weekend*20`. Maximum columns are fixed synthetic capacities. Menu strings are marked 합성.

This file supplies the unchanged model pipeline with demo input; it is not training data, retraining, or an accuracy evaluation. Existing pickle files are copied unchanged. Offline SBERT cache is absent in the tested base image: the existing processor falls back without text features. See the deployment verification report before interpreting demo predictions.
