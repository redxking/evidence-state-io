-- Synthetic, public-safe records for the optional Evidence-State I/O lab.
-- This database is not an authoritative source and is never production evidence.

CREATE TABLE IF NOT EXISTS synthetic_events (
    event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_partition text NOT NULL,
    observed_at timestamptz NOT NULL,
    indicator text NOT NULL,
    details jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS synthetic_events_observed_at_idx
    ON synthetic_events (observed_at);

CREATE INDEX IF NOT EXISTS synthetic_events_indicator_idx
    ON synthetic_events (indicator);

INSERT INTO synthetic_events (source_partition, observed_at, indicator, details)
VALUES
    ('partition-a', '2026-08-21T12:00:00Z', 'synthetic.example/a', '{"origin":"synthetic"}'),
    ('partition-b', '2026-08-21T12:05:00Z', 'synthetic.example/b', '{"origin":"synthetic"}');
