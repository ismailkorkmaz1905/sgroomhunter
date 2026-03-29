# Product Strategy

## Working Name

RoomRadar

## One-Line Pitch

A rental search and outreach assistant that finds room listings you can actually live in, explains why they fit, and helps you contact agents faster.

## Problem

People looking for room rentals waste time on listings that hide critical rules:

- shared bathroom
- no cooking or only microwave
- no visitors or no overnight guests
- landlord stays in unit
- wrong location, price, or lease timing

The current workflow is fragmented:

- search manually across many listings
- open each listing one by one
- guess hidden rules from incomplete descriptions
- message agents manually
- repeat until something works

## Product Thesis

The winning product is not just a listing browser.
It is a qualification and outreach engine.

The key value is:

1. filter listings against the user's real life constraints
2. explain why each listing is accepted or rejected
3. prepare a high-quality outreach message
4. let the user approve or automate contact

## Core User

Primary:

- expats in Singapore searching for room rentals
- Employment Pass / S Pass holders
- young professionals relocating quickly

Secondary:

- students
- relocation consultants
- power users managing multiple housing searches

## Main Use Cases

1. Set criteria
- budget
- areas / MRT lines
- lease start
- cooking rules
- visitor rules
- attached bathroom requirement
- landlord stay preference

2. Review triage feed
- accepted listings
- rejected listings with reasons
- risky listings needing human review

3. Outreach
- one-click approve
- WhatsApp draft
- optional auto-send
- message templates by persona

4. Monitor
- alerts every 30 minutes
- only new matches
- track pending / approved / rejected

## Product Shape

Best first product:

- web app with backend worker

Why not start with iOS first:

- background automation is harder
- WhatsApp/browser workflows are more constrained
- faster iteration is easier on web

## MVP

### Must-have

- onboarding form for rental criteria
- saved search profiles
- listing ingestion pipeline
- rules engine with reason codes
- accepted / rejected / risky tabs
- draft outreach messages
- approval queue
- Telegram or email alerts
- WhatsApp open/send workflow

### Nice-to-have

- multiple personas
- multiple search profiles
- viewing tracker
- notes per listing
- agent response tracker
- duplicate detection

## Monetization

### Option 1: Subscription

Best default model.

Example:

- Free: 1 search profile, manual review only, low alert volume
- Pro: 3-5 search profiles, faster alerts, approval queue, templates
- Premium: advanced filters, auto-send, priority matching, concierge support

### Option 2: Concierge Layer

Strong premium upsell.

- "We shortlist and prepare outreach for you"
- high-touch support for busy expats

### Option 3: B2B

Possible later:

- relocation agencies
- tenant advisory firms
- student housing operators

## Suggested Pricing

Early beta:

- Free
- Pro: SGD 19-29 / month
- Premium: SGD 49-99 / month

Concierge test:

- SGD 99-199 setup / guided search package

## Risks

### Platform Risk

- scraping third-party platforms can break
- rules or markup can change
- aggressive automation may trigger defenses

### Messaging Risk

- WhatsApp automation can look spammy if abused
- too many repetitive outbound messages can increase account risk

### Trust Risk

- false positives create wasted outreach
- false negatives make users miss good listings

## Risk Mitigation

- human approval by default
- low-volume outreach
- transparent rejection reasons
- logs and reviewability
- multiple source adapters later
- per-day send limits and cooldowns

## Differentiation

Most tools only help users search.
This product helps users decide and act.

The strongest positioning:

"We don't just show listings. We show the ones that fit your life."

## Demo Story

The best demo flow:

1. User enters criteria
2. Feed shows accepted and rejected listings
3. Each rejected listing explains why it failed
4. User approves one listing
5. Draft message appears
6. Contact is initiated automatically

## Recommended Build Order

1. polished web dashboard on top of current automation
2. account system and stored search profiles
3. job runner / queue / notifications
4. analytics and response tracking
5. billing
6. iOS companion app

## What Success Looks Like

User says:

- "I stopped wasting time on bad listings."
- "I message the right agents faster."
- "I understand immediately why a listing fits or fails."
