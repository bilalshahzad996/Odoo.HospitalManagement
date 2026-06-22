from odoo import models, fields, api
from odoo.exceptions import ValidationError

class HospitalLeave(models.Model):
    _name = "hospital.leave"
    _description = "Staff Leave"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"

    name = fields.Char(string="Leave Reference", readonly=True, copy=False, default=lambda self: self.env["ir.sequence"].next_by_code("hospital.leave") or "New")
    staff_id = fields.Many2one("hospital.staff", string="Staff", required=True, tracking=True)
    department_id = fields.Many2one("hospital.department", string="Department", related="staff_id.department_id", store=True)
    leave_type = fields.Selection([
        ("sick","Sick Leave"),("casual","Casual Leave"),("annual","Annual Leave"),
        ("emergency","Emergency Leave"),("maternity","Maternity Leave"),("unpaid","Unpaid Leave"),
    ], string="Leave Type", required=True, tracking=True)
    date_from = fields.Date(string="From Date", required=True, tracking=True)
    date_to = fields.Date(string="To Date", required=True, tracking=True)
    total_days = fields.Integer(string="Total Days", compute="_compute_total_days", store=True)
    reason = fields.Text(string="Reason")
    state = fields.Selection([
        ("draft","Draft"),("pending","Pending Approval"),
        ("approved","Approved"),("refused","Refused"),("cancelled","Cancelled"),
    ], string="Status", default="draft", tracking=True)

    @api.depends("date_from","date_to")
    def _compute_total_days(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                rec.total_days = (rec.date_to - rec.date_from).days + 1
            else:
                rec.total_days = 0

    @api.constrains("date_from","date_to")
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_to < rec.date_from:
                raise ValidationError("End date cannot be before start date!")

    def action_submit(self): self.state = "pending"
    def action_approve(self):
        self.state = "approved"
        self.staff_id.state = "on_leave"
    def action_refuse(self): self.state = "refused"
    def action_cancel(self): self.state = "cancelled"
    def action_draft(self): self.state = "draft"
