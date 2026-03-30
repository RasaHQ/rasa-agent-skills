# Skill examples

### "Create a skill that books flights"

Well-defined multi-step process → **flow-based**.

- **Flows**: `book_flight`, `select_destination` (child), `choose_seats` (child)
- **Slots**: `departure_city`, `destination_city`, `travel_date`, `return_date`,
  `passenger_count`, `seat_preference`, `selected_flight`
- **Actions**: `action_search_flights`, `action_book_flight`

→ `rasa-building-flows`

### "Create a skill that explores stock options"

Open-ended research with dynamic tool selection → **sub-agent**.

- **Flows**: `stock_research` (thin wrapper calling the sub-agent)
- **Sub-agent**: `stock_explorer` — ReAct agent with financial data MCP server
- **Slots**: `portfolio_id` (input), `analysis_result` (output)

→ `rasa-setting-up-react-agents`

### "Create a payment skill"

High-risk financial domain → **flow-based**.

- **Flows**: `process_payment`, `select_payment_method` (child),
  `verify_payment` (child)
- **Slots**: `payment_amount`, `payment_method`, `card_last_four`, `payment_confirmed`
- **Actions**: `action_validate_payment`, `action_process_payment`

→ `rasa-building-flows`

### "Create an insurance claim skill"

Deterministic collection but open-ended policy search → **hybrid**.

- **Flows**: `file_insurance_claim` (orchestrator), `confirm_and_submit_claim` (child)
- **Sub-agent**: `policy_search_agent` — searches policy clauses autonomously
- **Slots**: `claim_type`, `incident_date`, `incident_description`, `matching_policy`

```yaml
flows:
  file_insurance_claim:
    description: Helps users file an insurance claim and find relevant policy coverage.
    steps:
      - collect: claim_type
      - collect: incident_date
      - collect: incident_description
      - call: policy_search_agent
        exit_if:
          - slots.matching_policy is not null
      - action: utter_claim_summary
      - call: confirm_and_submit_claim
```

→ `rasa-building-flows` + `rasa-setting-up-react-agents`

### "Create a Jira ticket skill"

Depends on scope — ask the user:

- Fixed fields, single API call → **flow-based** with a custom action.
- Needs to search projects, look up tickets, pick from many operations →
  **sub-agent** with Jira MCP server.
