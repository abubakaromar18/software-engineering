"""Reporting helpers that grew one method at a time."""


class ReportManager:
    """Builds every report the shop has ever needed."""

    def __init__(self, orders):
        self.orders = orders

    def daily(self):
        return [o for o in self.orders if o["period"] == "day"]

    def weekly(self):
        return [o for o in self.orders if o["period"] == "week"]

    def monthly(self):
        return [o for o in self.orders if o["period"] == "month"]

    def yearly(self):
        return [o for o in self.orders if o["period"] == "year"]

    def by_customer(self, customer_id):
        return [o for o in self.orders if o["customer"] == customer_id]

    def by_region(self, region):
        return [o for o in self.orders if o["region"] == region]

    def refunds(self):
        return [o for o in self.orders if o["refunded"]]

    def to_csv(self):
        return "\n".join(",".join(map(str, o.values())) for o in self.orders)

    def to_html(self):
        return "<table>" + "".join(f"<tr><td>{o}</td></tr>" for o in self.orders) + "</table>"

    def email(self, address):  # smell: ignore[long-method]
        return f"to:{address}\n{self.to_csv()}"
