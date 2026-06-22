from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HospitalBill(models.Model):
    _name = "hospital.bill"
    _description = "Hospital Bill"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"

    name = fields.Char(string="Bill Reference", readonly=True, copy=False, tracking=True, default=lambda self: self.env["ir.sequence"].next_by_code("hospital.bill") or "New")
    patient_id = fields.Many2one("hospital.patient", string="Patient", required=True, tracking=True)
    doctor_id = fields.Many2one("hospital.doctor", string="Doctor", tracking=True)
    appointment_id = fields.Many2one("hospital.appointment", string="Appointment")
    bill_date = fields.Date(string="Bill Date", default=fields.Date.today, required=True)
    due_date = fields.Date(string="Due Date")
    notes = fields.Text(string="Notes")
    state = fields.Selection([
        ("draft",     "Draft"),
        ("confirmed", "Confirmed"),
        ("paid",      "Paid"),
        ("cancelled", "Cancelled"),
    ], string="Status", default="draft", tracking=True)
    payment_method = fields.Selection([
        ("cash",      "Cash"),
        ("card",      "Credit/Debit Card"),
        ("bank",      "Bank Transfer"),
        ("insurance", "Insurance"),
        ("other",     "Other"),
    ], string="Payment Method")
    bill_line_ids = fields.One2many("hospital.bill.line", "bill_id", string="Service Items")
    bill_product_ids = fields.One2many("hospital.bill.product", "bill_id", string="Product Items")
    subtotal = fields.Float(string="Subtotal", compute="_compute_totals", store=True)
    discount = fields.Float(string="Discount (%)", default=0.0)
    tax = fields.Float(string="Tax (%)", default=0.0)
    total_amount = fields.Float(string="Total Amount", compute="_compute_totals", store=True)
    amount_paid = fields.Float(string="Amount Paid", default=0.0, tracking=True)
    amount_due = fields.Float(string="Amount Due", compute="_compute_totals", store=True)
    sale_order_id = fields.Many2one("sale.order", string="Sale Order", readonly=True, copy=False)
    invoice_id = fields.Many2one("account.move", string="Invoice", readonly=True, copy=False)
    sale_order_count = fields.Integer(compute="_compute_sale_order_count")
    invoice_count = fields.Integer(compute="_compute_invoice_count")

    def _compute_sale_order_count(self):
        for rec in self:
            rec.sale_order_count = 1 if rec.sale_order_id else 0

    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = 1 if rec.invoice_id else 0

    @api.depends("bill_line_ids.subtotal", "bill_product_ids.subtotal", "discount", "tax", "amount_paid")
    def _compute_totals(self):
        for rec in self:
            service_total = sum(line.subtotal for line in rec.bill_line_ids)
            product_total = sum(line.subtotal for line in rec.bill_product_ids)
            subtotal = service_total + product_total
            discount_amount = subtotal * (rec.discount / 100)
            after_discount = subtotal - discount_amount
            tax_amount = after_discount * (rec.tax / 100)
            total = after_discount + tax_amount
            rec.subtotal = subtotal
            rec.total_amount = total
            rec.amount_due = total - rec.amount_paid

    def action_confirm(self):
        self._check_stock_availability()
        self.state = "confirmed"
        self._deduct_stock()
        self._create_sale_order()

    def action_pay(self):
        self.amount_paid = self.total_amount
        self.state = "paid"
        self._create_and_pay_invoice()

    def action_cancel(self):
        if self.state == "confirmed":
            self._return_stock()
        self.state = "cancelled"

    def action_draft(self):
        self.state = "draft"

    def action_print_receipt(self):
        return self.env.ref("hospital_management.action_report_bill").report_action(self)

    def action_view_sale_order(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "name": "Sale Order", "res_model": "sale.order", "res_id": self.sale_order_id.id, "view_mode": "form", "target": "current"}

    def action_view_invoice(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "name": "Invoice", "res_model": "account.move", "res_id": self.invoice_id.id, "view_mode": "form", "target": "current"}

    def _check_stock_availability(self):
        for line in self.bill_product_ids:
            available = line.product_id.qty_available
            if line.quantity > available:
                raise ValidationError(
                    "Not enough stock for '%s'.\nAvailable: %s | Required: %s" % (
                        line.product_id.name, available, line.quantity
                    )
                )

    def _deduct_stock(self):
        """Deduct stock using stock.quant directly — most reliable method"""
        if not self.bill_product_ids:
            return

        stock_location = self.env.ref("stock.stock_location_stock", raise_if_not_found=False)
        if not stock_location:
            stock_location = self.env["stock.location"].search([
                ("usage", "=", "internal"),
                ("company_id", "=", self.env.company.id),
            ], limit=1)

        customer_location = self.env.ref("stock.location_customers", raise_if_not_found=False)
        if not customer_location:
            customer_location = self.env["stock.location"].search([
                ("usage", "=", "customer"),
            ], limit=1)

        if not stock_location or not customer_location:
            self.message_post(body="⚠️ Stock locations not found. Stock not deducted.")
            return

        picking_type = self.env["stock.picking.type"].search([
            ("code", "=", "outgoing"),
            ("warehouse_id.company_id", "=", self.env.company.id),
        ], limit=1)

        if not picking_type:
            # Fallback: use stock.quant directly
            for line in self.bill_product_ids:
                quant = self.env["stock.quant"].search([
                    ("product_id", "=", line.product_id.id),
                    ("location_id", "=", stock_location.id),
                ], limit=1)
                if quant:
                    quant.quantity -= line.quantity
            self.message_post(body="Stock deducted directly from quants.")
            return

        # Create delivery order
        move_lines = []
        for line in self.bill_product_ids:
            move_lines.append((0, 0, {
                "name": line.product_id.name,
                "product_id": line.product_id.id,
                "product_uom_qty": line.quantity,
                "product_uom": line.product_id.uom_id.id,
                "location_id": stock_location.id,
                "location_dest_id": customer_location.id,
            }))

        picking = self.env["stock.picking"].create({
            "picking_type_id": picking_type.id,
            "location_id": stock_location.id,
            "location_dest_id": customer_location.id,
            "origin": self.name,
            "move_ids": move_lines,
        })

        picking.action_confirm()
        picking.action_assign()

        # Set done quantities
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty

        # Validate picking
        try:
            picking.with_context(skip_backorder=True).button_validate()
            self.message_post(body="✅ Stock deducted. Delivery: <b>%s</b>" % picking.name)
        except Exception as e:
            # Fallback to quant update
            for line in self.bill_product_ids:
                quant = self.env["stock.quant"].search([
                    ("product_id", "=", line.product_id.id),
                    ("location_id", "=", stock_location.id),
                ], limit=1)
                if quant:
                    quant.quantity -= line.quantity
                else:
                    self.env["stock.quant"].create({
                        "product_id": line.product_id.id,
                        "location_id": stock_location.id,
                        "quantity": -line.quantity,
                    })
            self.message_post(body="✅ Stock deducted from inventory.")

    def _return_stock(self):
        """Return stock when bill cancelled"""
        if not self.bill_product_ids:
            return
        stock_location = self.env.ref("stock.stock_location_stock", raise_if_not_found=False)
        if not stock_location:
            return
        for line in self.bill_product_ids:
            quant = self.env["stock.quant"].search([
                ("product_id", "=", line.product_id.id),
                ("location_id", "=", stock_location.id),
            ], limit=1)
            if quant:
                quant.quantity += line.quantity
            else:
                self.env["stock.quant"].create({
                    "product_id": line.product_id.id,
                    "location_id": stock_location.id,
                    "quantity": line.quantity,
                })
        self.message_post(body="✅ Stock returned to inventory.")

    def _get_or_create_partner(self):
        patient = self.patient_id
        partner = self.env["res.partner"].search([("name", "=", patient.name)], limit=1)
        if not partner:
            partner = self.env["res.partner"].create({
                "name": patient.name,
                "phone": patient.phone or "",
                "email": patient.email or "",
                "street": patient.address or "",
                "customer_rank": 1,
                "company_type": "person",
            })
        else:
            if partner.customer_rank == 0:
                partner.customer_rank = 1
        return partner

    def _get_or_create_service_product(self, service):
        product_tmpl = self.env["product.template"].search([
            ("name", "=", service.name),
            ("type", "=", "service"),
        ], limit=1)
        if not product_tmpl:
            product_tmpl = self.env["product.template"].create({
                "name": service.name,
                "type": "service",
                "list_price": service.price,
                "sale_ok": True,
                "purchase_ok": False,
                "invoice_policy": "order",
            })
        return product_tmpl.product_variant_id

    def _create_sale_order(self):
        if self.sale_order_id:
            return
        partner = self._get_or_create_partner()
        order_lines = []
        for line in self.bill_line_ids:
            product = self._get_or_create_service_product(line.service_id)
            order_lines.append((0, 0, {
                "product_id": product.id,
                "product_uom_qty": line.quantity,
                "price_unit": line.unit_price,
                "discount": self.discount,
                "name": line.description or line.service_id.name,
            }))
        for line in self.bill_product_ids:
            order_lines.append((0, 0, {
                "product_id": line.product_id.id,
                "product_uom_qty": line.quantity,
                "price_unit": line.unit_price,
                "discount": self.discount,
                "name": line.product_id.name,
            }))
        sale_order = self.env["sale.order"].create({
            "partner_id": partner.id,
            "date_order": fields.Datetime.now(),
            "validity_date": self.due_date,
            "client_order_ref": self.name,
            "note": self.notes or "",
            "order_line": order_lines,
            "origin": self.name,
        })
        sale_order.action_confirm()
        self.sale_order_id = sale_order.id
        self.message_post(body="Sale Order <b>%s</b> created in Sales." % sale_order.name)

    def _get_payment_journal(self):
        if self.payment_method == "cash":
            journal = self.env["account.journal"].search([("type", "=", "cash"), ("company_id", "=", self.env.company.id)], limit=1)
        else:
            journal = self.env["account.journal"].search([("type", "=", "bank"), ("company_id", "=", self.env.company.id)], limit=1)
        if not journal:
            journal = self.env["account.journal"].search([("type", "in", ["cash", "bank"]), ("company_id", "=", self.env.company.id)], limit=1)
        return journal

    def _create_and_pay_invoice(self):
        if not self.sale_order_id:
            self._create_sale_order()
        if self.invoice_id:
            return
        invoices = self.sale_order_id._create_invoices()
        if not invoices:
            return
        invoice = invoices[0]
        invoice.invoice_date = self.bill_date
        invoice.action_post()
        self.invoice_id = invoice.id
        journal = self._get_payment_journal()
        if not journal:
            self.message_post(body="No payment journal found. Please register payment manually.")
            return
        payment = self.env["account.payment"].create({
            "journal_id": journal.id,
            "amount": self.total_amount,
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": self.sale_order_id.partner_id.id,
            "date": self.bill_date,
            "memo": self.name,
        })
        payment.action_post()
        invoice_lines = invoice.line_ids.filtered(lambda l: l.account_id.account_type == "asset_receivable")
        payment_lines = payment.line_ids.filtered(lambda l: l.account_id.account_type == "asset_receivable")
        if invoice_lines and payment_lines:
            (invoice_lines + payment_lines).reconcile()
        self.message_post(body="Invoice <b>%s</b> created and payment registered." % invoice.name)


class HospitalBillLine(models.Model):
    _name = "hospital.bill.line"
    _description = "Bill Line - Services"

    bill_id = fields.Many2one("hospital.bill", string="Bill", required=True)
    service_id = fields.Many2one("hospital.service", string="Service", required=True)
    description = fields.Char(string="Description")
    quantity = fields.Float(string="Quantity", default=1.0)
    unit_price = fields.Float(string="Unit Price")
    subtotal = fields.Float(string="Subtotal", compute="_compute_subtotal", store=True)

    @api.depends("quantity", "unit_price")
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.quantity * rec.unit_price

    @api.onchange("service_id")
    def _onchange_service_id(self):
        if self.service_id:
            self.unit_price = self.service_id.price
            self.description = self.service_id.name


class HospitalBillProduct(models.Model):
    _name = "hospital.bill.product"
    _description = "Bill Line - Products"

    bill_id = fields.Many2one("hospital.bill", string="Bill", required=True)
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
        domain="[('type','in',['product','consu'])]"
    )
    description = fields.Char(string="Description")
    quantity = fields.Float(string="Quantity", default=1.0)
    unit_price = fields.Float(string="Unit Price")
    qty_available = fields.Float(
        string="In Stock",
        related="product_id.qty_available",
        readonly=True
    )
    subtotal = fields.Float(string="Subtotal", compute="_compute_subtotal", store=True)

    @api.depends("quantity", "unit_price")
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.quantity * rec.unit_price

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.unit_price = self.product_id.lst_price
            self.description = self.product_id.name