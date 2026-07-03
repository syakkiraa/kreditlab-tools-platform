alter table public.cases
add column if not exists consultant_reminder_sent_at timestamptz;
