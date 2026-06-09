from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime


class HospitalAttendance(models.Model):
    _name = "hospital.attendance"
    _description = "Staff Attendance"
    _rec_name = "staff_id"

    staff_id = fields.Many2one("hospital.staff", string="Staff", required=True, tracking=True)
    department_id = fields.Many2one("hospital.department", string="Department", related="staff_id.department_id", store=True)
    date = fields.Date(string="Date", default=fields.Date.today, required=True)
    check_in = fields.Datetime(string="Check In")
    check_out = fields.Datetime(string="Check Out")
    worked_hours = fields.Float(string="Worked Hours", compute="_compute_worked_hours", store=True)
    status = fields.Selection([
        ("present",  "Present"),
        ("absent",   "Absent"),
        ("half_day", "Half Day"),
        ("late",     "Late"),
        ("on_leave", "On Leave"),
    ], string="Status", default="present", tracking=True)
    notes = fields.Char(string="Notes")

    @api.depends("check_in", "check_out")
    def _compute_worked_hours(self):
        for rec in self:
            if rec.check_in and rec.check_out:
                delta = rec.check_out - rec.check_in
                rec.worked_hours = delta.total_seconds() / 3600
            else:
                rec.worked_hours = 0.0

    @api.constrains("check_in", "check_out")
    def _check_times(self):
        for rec in self:
            if rec.check_in and rec.check_out:
                if rec.check_out < rec.check_in:
                    raise ValidationError("Check Out cannot be before Check In!")

    def action_check_in(self):
        self.check_in = datetime.now()

    def action_check_out(self):
        self.check_out = datetime.now()