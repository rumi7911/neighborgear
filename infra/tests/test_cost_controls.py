"""Reject budget configurations that hide credit consumption or alert too late."""

from pathlib import Path

from cfnlint.decode import decode


def read_template():
    path = Path(__file__).parents[1] / "cost-controls.yaml"
    assert path.is_file(), "The reviewed cost-control template must exist before deployment"
    template, errors = decode(str(path))
    assert not errors
    return template


def test_budget_tracks_gross_account_cost_not_credit_offset_bill():
    cost_template = read_template()
    resources = cost_template["Resources"]
    assert len(resources) == 1, "Monitoring must not silently create actions or other services"
    resource = resources["CreditSpendBudget"]
    assert resource["Type"] == "AWS::Budgets::Budget"
    budget = resource["Properties"]["Budget"]
    assert budget["BudgetType"] == "COST"
    assert budget["TimeUnit"] == "MONTHLY"
    assert budget["BudgetLimit"] == {"Amount": 20, "Unit": "USD"}
    assert not budget.get("CostFilters"), "Do not miss untagged or non-project credit consumption"
    costs = budget["CostTypes"]
    assert costs["IncludeCredit"] is False
    assert costs["IncludeRefund"] is False
    assert costs["UseBlended"] is False
    assert costs["UseAmortized"] is False
    for key in ("IncludeTax", "IncludeSupport", "IncludeRecurring", "IncludeSubscription",
                "IncludeOtherSubscription", "IncludeUpfront", "IncludeDiscount"):
        assert costs[key] is True


def test_alerts_use_dollar_thresholds_and_only_owner_supplied_email():
    cost_template = read_template()
    notices = cost_template["Resources"]["CreditSpendBudget"]["Properties"]["NotificationsWithSubscribers"]
    assert len(notices) == 5
    actual, forecast = [], []
    for notice in notices:
        rule = notice["Notification"]
        assert rule["ThresholdType"] == "ABSOLUTE_VALUE"
        assert rule["ComparisonOperator"] == "GREATER_THAN"
        assert notice["Subscribers"] == [{"SubscriptionType": "EMAIL", "Address": {"Ref": "AlertEmail"}}]
        if rule["NotificationType"] == "ACTUAL":
            actual.append(rule["Threshold"])
        else:
            assert rule["NotificationType"] == "FORECASTED"
            forecast.append(rule["Threshold"])
    assert sorted(actual) == [1, 5, 10, 20]
    assert forecast == [20]


def test_cost_monitor_is_opt_in_and_has_no_email_default():
    cost_template = read_template()
    params = cost_template["Parameters"]
    assert params["EnableAlerts"]["Default"] == "false"
    assert params["EnableAlerts"]["AllowedValues"] == ["true", "false"]
    assert "Default" not in params["AlertEmail"]
    assert params["AlertEmail"]["NoEcho"] is True
    assert cost_template["Conditions"]["AlertsEnabled"] == {"Fn::Equals": [{"Ref": "EnableAlerts"}, "true"]}
    assert cost_template["Resources"]["CreditSpendBudget"]["Condition"] == "AlertsEnabled"
