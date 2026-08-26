# Cost guardrail. The spec's estimate is ~$0.01-0.06/month, so a $5 cap is
# roughly 80x the expected spend -- it is a runaway-detector, not a real
# budget. Scoped to this resource group only, never the subscription: a
# subscription-wide budget would also alarm on the state-backend resource
# group, which has a deliberately separate lifecycle.
resource "azurerm_consumption_budget_resource_group" "this" {
  name              = "budget-docaudit-prod-ne"
  resource_group_id = azurerm_resource_group.this.id

  amount     = var.budget_amount
  time_grain = "Monthly"

  time_period {
    # Azure requires a Monthly budget's start date to be the first of a
    # month, and a past start date must fall inside the current time grain
    # -- i.e. it has to be the first of the *current* month. A hardcoded
    # date would therefore work today and then fail the moment the stack is
    # destroyed and recreated in a later month, which Task 15 requires it to
    # survive. Deriving it from timestamp() keeps every fresh create valid.
    #
    # timestamp() is normally a perpetual-diff trap; ignore_changes below
    # neutralises that, and the value only ever needs to be correct at
    # create time.
    start_date = formatdate("YYYY-MM-01'T'00:00:00'Z'", timestamp())
    end_date   = "2030-01-01T00:00:00Z"
  }

  # Early warning. At the expected run rate this is ~20x normal spend, so it
  # should never fire on ordinary usage -- if it does, something is wrong
  # while the absolute loss is still about a dollar.
  notification {
    enabled        = true
    threshold      = 25.0
    threshold_type = "Actual"
    operator       = "GreaterThan"
    contact_emails = [var.budget_contact_email]
  }

  # Trend alarm: catches a runaway before it actually reaches the cap.
  notification {
    enabled        = true
    threshold      = 100.0
    threshold_type = "Forecasted"
    operator       = "GreaterThan"
    contact_emails = [var.budget_contact_email]
  }

  lifecycle {
    ignore_changes = [time_period[0].start_date]
  }
}
