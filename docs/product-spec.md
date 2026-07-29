# Provider Navigation and Scheduling Agent

## Product Summary

The Provider Navigation and Scheduling Agent helps a health-plan member find an
appropriate provider, verify that the provider participates in the member's
specific network, locate a suitable appointment, and complete a booking through
a conversational experience.

The initial product uses synthetic members, plans, networks, providers, and
appointment data. It should behave like a production system while keeping real
protected health information and external healthcare integrations out of the
MVP. Synthetic services must sit behind replaceable interfaces so that real
payer, provider-directory, eligibility, and scheduling systems can be connected
later.

## Problem

Finding care often requires a member to search multiple directories, understand
plan-specific network rules, call provider offices, compare availability, and
repeat personal preferences. Provider directories may show that a provider
accepts an insurer without establishing that the provider is in-network for the
member's exact plan, location, specialty, service, and requested date.

The product should reduce this work while never inventing provider eligibility,
availability, or booking outcomes.

## Target User

The MVP serves an authenticated health-plan member seeking a non-emergency,
non-clinical appointment for themselves.

The member may express requests conversationally, for example:

> Find me a female dermatologist near Plano who is in-network with my plan and
> available next week.

Future versions may support dependents, caregivers, provider staff, and health
plan service representatives. These users are outside the MVP.

## Product Goal

Enable a member to complete this verified workflow:

```text
Understand request
-> collect missing requirements
-> search providers
-> verify plan-specific network participation
-> find available slots
-> rank options using member preferences
-> present exact appointment details
-> receive explicit member confirmation
-> book idempotently
-> return the source-system confirmation
```

The language model coordinates the conversation. Deterministic application
services remain the source of truth for member eligibility, network
participation, provider data, appointment availability, and booking status.

## MVP Scope

### Included

- Authenticate or identify a synthetic member.
- Load the member's synthetic enrollment and saved preferences.
- Collect specialty, location, date range, appointment modality, and relevant
  provider preferences.
- Search a synthetic provider directory.
- Verify provider network participation against the member's specific plan.
- Search synthetic appointment availability for eligible provider locations.
- Rank verified options using required constraints and member preferences.
- Explain why presented providers match the request.
- Allow the member to select a provider and slot.
- Present a final appointment summary and require explicit confirmation.
- Create one idempotent synthetic booking.
- Return a confirmation number produced by the booking service.
- Handle missing data, unavailable slots, changed slots, tool failures, and
  unsupported requests without fabricating a result.
- Record structured workflow and tool-execution events for evaluation and
  debugging, without exposing hidden model reasoning.

### MVP Assumptions

- All people, identifiers, plans, providers, networks, and appointments are
  synthetic.
- The member books only for themselves.
- The provider directory and scheduling service cover one simulated
  organization or ecosystem.
- Network verification is based on structured synthetic participation records.
- Estimated cost and detailed benefit calculations are not available.
- The application supports English-language text conversations.

## Domain Terminology

| Term | Definition |
| --- | --- |
| Member | A person enrolled in a health plan and using the assistant. |
| Health plan | The member's specific insurance product, not merely the insurer's brand. |
| Network | The provider-participation network associated with a health plan. |
| Provider | A healthcare professional or organization offering services. |
| Provider location | A physical or virtual location where a provider practices. Network status may differ by location. |
| Specialty | The provider's clinical area of practice used for navigation and matching. |
| Network participation | A dated record showing whether a provider, at a location and for a relevant specialty or service, participates in a specific network. |
| In-network | Verified participation in the network associated with the member's plan for the applicable context and date. |
| Out-of-network | Verified non-participation in the member's applicable network. |
| Network unknown | The system lacks enough authoritative data to classify the provider. Unknown must never be presented as in-network. |
| Appointment slot | A bookable period returned by the scheduling service for a provider and location. |
| Member preference | A soft or hard constraint such as distance, language, provider gender, modality, or preferred time. |
| Booking | A scheduling-system transaction that reserves a selected slot. |
| Confirmation | The booking identifier and status returned by the scheduling service after a successful transaction. |

An insurer name or statement that a provider "accepts" an insurer is not proof
that the provider is in-network for a member's plan.

## Functional Requirements

### Request Understanding

The agent must identify known and missing scheduling requirements. It should ask
only for information required to make progress and must not repeatedly request
data already available from the authenticated member profile, saved preferences,
or current conversation.

The agent may help map a member's stated provider type to a specialty, but it
must not diagnose symptoms or determine clinical urgency beyond applying
documented safety escalation rules.

### Provider Search

Provider search must use structured service results. At minimum, a result must
include:

- Stable provider identifier
- Display name
- Specialty
- Provider location
- Appointment modality
- Relevant preference attributes, such as languages and provider gender

The agent must not invent providers or silently change a member's required
constraints. If no suitable provider is found, it may propose an expanded
distance, date range, modality, or preference only after clearly explaining the
change.

### Network Verification

Network status must be evaluated for the authenticated member's active plan and
the applicable provider, location, specialty or service, and requested date.
Every displayed network result must be traceable to a structured participation
record.

The allowed statuses are:

- `in_network`
- `out_of_network`
- `unknown`

Only `in_network` providers may be described as in-network. When the status is
`unknown`, the agent must disclose that verification could not be completed and
must not imply coverage or a guaranteed member cost.

### Availability and Ranking

Availability must come from the scheduling service and must include a stable
slot identifier, provider, location, start time, duration, modality, and current
status.

Required constraints must filter results. Soft preferences may influence
ranking but must not be misrepresented as requirements. Ranking should consider:

- Verified network participation
- Requested specialty
- Distance or requested location
- Date and time preference
- In-person or virtual modality
- Language preference
- Provider gender preference

The response should state the important reasons an option was selected without
revealing private chain-of-thought reasoning.

### Confirmation and Booking

Immediately before booking, the agent must present:

- Provider name
- Specialty
- Location or virtual modality
- Appointment date, time, and time zone
- Verified network status
- Any unresolved limitation relevant to the member's decision

The member must explicitly confirm these details. Selecting an option earlier
in the conversation does not count as final booking confirmation.

Booking must:

- Use the scheduling service rather than model-generated data.
- Validate that the slot is still available.
- Use an idempotency key to prevent duplicate appointments.
- Associate the booking with the authenticated member.
- Return the exact status and confirmation identifier from the service.
- Never report success when the service returns a failure, timeout, or ambiguous
  result.

If a slot is no longer available, the agent should explain what happened and
offer refreshed alternatives.

### Preferences and Memory

The agent may use saved preferences to reduce repeated questions. It must:

- Keep memory isolated by authenticated member.
- Distinguish a preference from a required constraint.
- Allow the member to correct or override a saved preference.
- Avoid storing sensitive conversational content that is not needed for the
  supported workflow.
- Never allow remembered information to override current explicit instructions.

## Supported Conversation Flow

```text
Member:
Find me a female dermatologist near Plano who is in-network and available next
week.

Agent:
Loads the member's active synthetic plan, searches dermatologists, verifies
network participation, checks availability, and presents verified options.

Member:
Book the Tuesday morning appointment with Dr. Sarah Johnson.

Agent:
Please confirm: Dr. Sarah Johnson, Dermatology, Plano Clinic, Tuesday,
May 12 at 10:00 AM Central. The provider is verified in-network for your
current plan. Would you like me to book this appointment?

Member:
Confirm.

Agent:
Calls the booking service and returns its status and confirmation number.
```

The agent must also support:

- Asking for missing specialty, location, or scheduling preferences.
- No matching providers.
- No in-network providers.
- Network status unavailable.
- No available appointments.
- Slot lost before confirmation.
- Duplicate confirmation messages.
- Booking service timeout or failure.
- Member cancellation before booking.
- A request that requires human or emergency assistance.

## Exclusions

The MVP will not:

- Diagnose a condition or provide medical advice.
- Recommend medications or treatment.
- Perform clinical triage beyond emergency-language detection and escalation.
- Interpret medical images, laboratory results, or clinical records.
- Guarantee coverage, benefits, prior authorization, or out-of-pocket cost.
- Treat an insurer name as proof of network participation.
- Book without explicit member confirmation.
- Modify or cancel existing appointments.
- Book for dependents or other people.
- Process real protected health information.
- Integrate with a production payer, EHR, provider directory, or scheduling
  platform.
- Contact a provider by phone, email, or fax.
- Process payments.

## Safety and Trust Boundaries

- The agent must direct emergency requests to appropriate emergency services
  rather than continue the scheduling workflow.
- Operational services, not the language model, are authoritative for network
  status, providers, slots, bookings, and confirmations.
- Tool and retrieved data must be treated as untrusted input and must not alter
  system instructions or authorization rules.
- The application must fail closed when member identity, authorization, network
  status, availability, or booking outcome cannot be established.
- Member data and memory must be isolated across users.
- Logs and evaluation records must not expose secrets, unnecessary personal
  data, or hidden model reasoning.
- The member must be told when information is synthetic, unavailable, stale, or
  uncertain.
- A human-support path must be offered for unsupported or unresolved cases.
- Real member or patient data must not be introduced until privacy, security,
  consent, retention, audit, vendor, and regulatory requirements are completed.

## Synthetic Data Requirements

The synthetic environment should contain enough variation to test realistic
behavior:

- Members enrolled in different plans and networks
- Active, future, and expired enrollments
- Providers practicing at multiple locations
- Location-specific network participation
- Multiple specialties, languages, modalities, and provider genders
- In-network, out-of-network, unknown, and expired participation records
- Available, held, booked, and cancelled appointment slots
- Slot conflicts and simulated integration failures

Synthetic records must use clearly fictitious names and identifiers and must not
be derived from real patient or member data.

## Success Metrics

| Metric | MVP target |
| --- | --- |
| Supported scheduling requests completed without human intervention | At least 80% in the evaluation set |
| Presented in-network results backed by the correct participation record | 100% |
| Fabricated providers, slots, bookings, or confirmations | 0 |
| Bookings made without explicit confirmation | 0 |
| Duplicate bookings from repeated confirmation | 0 |
| Cross-member data or memory exposure | 0 |
| Unsupported or unresolved requests given a safe handoff | 100% |
| Successful bookings returning the service confirmation | 100% |
| Critical safety and authorization evaluations passed | 100% |

Additional operational metrics should include response latency, tool failure
rate, provider-search result quality, network-unknown rate, slot-loss rate,
member abandonment, and the number of conversational turns required to book.

## MVP Acceptance Criteria

The MVP is complete when:

1. An identified synthetic member can request care conversationally.
2. The system derives the member's active synthetic plan and network.
3. Provider results honor required constraints.
4. Every in-network statement is backed by the correct participation record.
5. Available slots originate from the scheduling service.
6. Preferences affect filtering or ranking as documented.
7. The agent presents exact appointment details and waits for confirmation.
8. Repeated confirmation creates no more than one booking.
9. A successful response includes the booking service's confirmation identifier.
10. Failure and safety scenarios pass automated evaluations.
11. No real protected health information is used.

## Future Real-System Integrations

The production architecture should allow synthetic adapters to be replaced with:

- Identity and access management using OAuth 2.0, OpenID Connect, or an
  organization-approved member identity provider
- Payer eligibility and member-enrollment services
- Plan benefit and network-product data
- Authoritative provider-directory and network-participation services
- FHIR-based provider resources such as `Practitioner`,
  `PractitionerRole`, `Organization`, `Location`, and `HealthcareService`
- Scheduling resources or vendor APIs for `Schedule`, `Slot`, and `Appointment`
- SMART on FHIR authorization when integrating with compatible healthcare
  systems
- Eligibility, prior-authorization, and cost-estimation services
- Member communication services for confirmations and reminders
- Customer-service or care-navigation handoff systems
- Consent, audit, retention, monitoring, and security platforms

Each real integration must preserve the deterministic service boundary: the
agent may coordinate and explain actions, but it must not replace authoritative
healthcare data or transactional systems.

## Open Product Decisions

The following decisions are intentionally deferred:

- The first real customer: payer, provider organization, or navigation vendor
- The first production scheduling platform
- Whether provider ranking optimizes member preference, access, cost, or another
  organizational objective
- How network data freshness and directory discrepancies are communicated
- Whether dependent and caregiver workflows are supported
- Whether insurance eligibility and detailed benefit verification are combined
  with network verification
- Which regulations, contractual requirements, and deployment controls apply to
  the eventual operating model
