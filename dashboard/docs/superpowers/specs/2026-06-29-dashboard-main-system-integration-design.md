# Dashboard Main System Integration Design

**Date:** 2026-06-29

## Goal

Build a dashboard overview page in this repo that matches the main dashboard design language and shows both:

- local case progress from this repo's own Supabase project
- live summary progress from the main dashboard system

The experience should stay simple for a single operator and should not introduce multi-consultant workflow complexity.

## Current Context

This repo already has:

- a dashboard shell with a left sidebar in `app/dashboard/layout.tsx`
- a sidebar/navigation pattern in `app/dashboard/sidebar.tsx`
- a basic overview page in `app/dashboard/page.tsx`
- client-side Supabase access in `lib/supabase.ts`
- case list/detail pages that already use the local `cases` table

The reference dashboard in `C:\Users\Sharky\Documents\kreditlabfullsystem\kredit-lab-dashboard` uses:

- a slate background and dark navy sidebar
- white rounded cards and tables
- cyan/teal accents for actions and progress
- compact headers with summary text
- a four-card KPI row
- a two-column middle section with recent cases and pipeline overview
- a bottom activity section

The main dashboard system currently exposes action-style API routes, but does not yet expose a read-only case progress summary API for dashboard consumption.

## User Requirements

- The dashboard in this repo should visually follow the same theme and layout direction as the main dashboard.
- The dashboard should connect with case progress.
- The dashboard should reflect both local repo data and main dashboard system data.
- The UI should be kept simple for one person handling the workflow.
- The implementation should be production-safe, readable, minimal, and consistent with this repo's conventions.
- Loading, empty, and error states are required.
- Targeted tests are required for non-trivial new logic.

## Recommended Architecture

Use this repo as the UI host and create a narrow server-to-server integration boundary to the main dashboard system.

### In this repo

- Expand `app/dashboard/page.tsx` into the main overview experience.
- Add small focused dashboard UI components for cards, recent cases, pipeline overview, and activity.
- Add local dashboard aggregation helpers that summarize this repo's `cases` table for the page.
- Add one server route that fetches main-system overview data through an authenticated request.

### In the main dashboard repo

- Add one read-only dashboard summary endpoint.
- Protect it with a shared bearer token.
- Return only the fields required for the dashboard view.

### Browser boundary

The browser in this repo should only:

- fetch local data from this repo's Supabase setup
- call this repo's integration route for main-system overview data

The browser should not:

- call the main dashboard service with secrets directly
- connect directly to the main dashboard database

## Data Flow

### Local dashboard data

The page reads the local `cases` table and derives:

- total cases
- active cases
- pending analysis
- pipeline value
- recent cases
- pipeline overview by status/stage
- recent activity snapshot

This keeps local progress tied to this repo's own data model and auth flow.

### Main dashboard data

This repo will expose a route such as:

- `GET /api/dashboard/main-system-overview`

That route will:

- validate required env vars
- call the main dashboard overview endpoint with bearer auth
- normalize the result shape for the local UI
- return a safe JSON payload to the browser

The main dashboard repo will expose a route such as:

- `GET /api/dashboard/overview`

That route will:

- validate bearer auth
- query its own `cases` data
- derive the same high-level summary sections needed by the UI
- return aggregate and preview data only

## UI Structure

The target page structure in this repo is:

1. Header row
   - title
   - short welcome text
   - search input
   - compact operator identity area

2. KPI row
   - total cases
   - active cases
   - pending analysis
   - pipeline value

3. Middle row
   - recent local cases card
   - local pipeline overview card

4. Bottom row
   - recent local activity card

5. Main-system connection section
   - connection/status card or section integrated into the same page
   - shows last successful sync-style fetch state
   - shows main-system KPIs and preview lists using the same visual language

The page should reuse the existing theme:

- `bg-slate-100` outer page
- white rounded cards
- subtle borders and shadows
- cyan/teal accents
- compact text hierarchy matching the current dashboard family

## Component Boundaries

Recommended component split in this repo:

- `DashboardStatCard`
- `DashboardRecentCasesCard`
- `DashboardPipelineCard`
- `DashboardRecentActivityCard`
- `DashboardMainSystemCard`

Supporting logic:

- local dashboard summary helper
- main-system payload normalization helper

These boundaries keep the page readable and allow card-level loading and error states.

## Error Handling

The page must remain useful when one data source fails.

### Local data failure

- show an inline error state for local dashboard sections
- do not crash the page shell
- still allow the main-system section to render

### Main-system failure

- show a dedicated "main system unavailable" or equivalent message
- keep local dashboard sections working normally
- avoid exposing raw internal fetch or secret details

### Missing configuration

This repo's integration route should fail fast when required env vars are absent and return structured safe errors.

The main dashboard overview route should do the same for its own required env vars and auth.

## Loading And Empty States

Each major section should handle loading independently.

### Loading

- KPI cards: compact placeholders
- recent cases: placeholder rows
- pipeline: placeholder bars or text
- activity: placeholder items
- main-system section: isolated loading state

### Empty

- recent cases: "No cases found"
- activity: "No activity yet"
- main-system preview: "No synced data yet" or equivalent

## Security

- Use server-to-server bearer authentication for the cross-repo overview request.
- Keep main-system secrets out of the client.
- Keep the main dashboard endpoint read-only.
- Return only the data required for rendering the dashboard.

## Testing Strategy

Add targeted tests for non-trivial new helpers.

### Local helper tests

- KPI counting
- pipeline grouping
- recent activity shaping
- status handling for active/pending buckets

### Integration normalization tests

- successful payload normalization
- fallback behavior for missing or partial fields

Keep tests aligned with the current lightweight `node --test` approach in this repo.

## Expected Files

### This repo

- `app/dashboard/page.tsx`
- new dashboard UI components under `app/dashboard/` or a nearby dashboard component folder
- `lib/` dashboard summary helpers
- `app/api/dashboard/main-system-overview/route.ts`
- targeted test files for helper logic

### Main dashboard repo

- one new read-only overview route under `app/api/dashboard/`
- one helper if needed for summary shaping
- targeted tests if that repo already has a matching lightweight test path for helper logic

## Required Configuration

This repo will need env vars for:

- its existing local Supabase setup
- the main dashboard base URL
- a shared bearer token for the main dashboard overview request

The main dashboard repo will need:

- the matching shared bearer token for overview route auth

## Out Of Scope

- multi-consultant assignment workflows
- direct browser access to the main dashboard database
- broad redesign of existing cases pages
- unrelated refactoring outside the dashboard integration path

## Implementation Recommendation

Proceed with a single overview page in this repo that mirrors the main dashboard layout, uses local Supabase data for local progress, and adds a server-fetched main-system summary card/section for live external progress.
