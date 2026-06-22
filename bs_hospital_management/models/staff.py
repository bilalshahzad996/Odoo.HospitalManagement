from odoo import models, fields, api


class HospitalStaff(models.Model):
    _name = "hospital.staff"
    _description = "Hospital Staff"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"

    name = fields.Char(string="Full Name", required=True, tracking=True)
    ref = fields.Char(string="Employee ID", readonly=True, copy=False, default=lambda self: self.env["ir.sequence"].next_by_code("hospital.staff") or "New")
    job_type = fields.Selection([
        ("doctor",       "Doctor"),
        ("nurse",        "Nurse"),
        ("pharmacist",   "Pharmacist"),
        ("technician",   "Lab Technician"),
        ("receptionist", "Receptionist"),
        ("admin",        "Admin"),
        ("security",     "Security"),
        ("cleaner",      "Cleaner"),
        ("other",        "Other"),
    ], string="Job Type", required=True, tracking=True)
    department_id = fields.Many2one("hospital.department", string="Department", tracking=True)
    shift_id = fields.Many2one("hospital.shift", string="Shift", tracking=True)
    gender = fields.Selection([("male","Male"),("female","Female"),("other","Other")], string="Gender", required=True)
    date_of_birth = fields.Date(string="Date of Birth")
    date_joining = fields.Date(string="Date of Joining", default=fields.Date.today)
    phone = fields.Char(string="Phone", tracking=True)
    email = fields.Char(string="Email")
    address = fields.Text(string="Address")
    salary = fields.Float(string="Monthly Salary")
    qualification = fields.Char(string="Qualification")
    experience_years = fields.Integer(string="Years of Experience")
    notes = fields.Text(string="Notes")
    state = fields.Selection([
        ("active",     "Active"),
        ("on_leave",   "On Leave"),
        ("resigned",   "Resigned"),
        ("terminated", "Terminated"),
    ], string="Status", default="active", tracking=True)

    attendance_ids = fields.One2many("hospital.attendance", "staff_id", string="Attendance")
    leave_ids = fields.One2many("hospital.leave", "staff_id", string="Leaves")
    attendance_count = fields.Integer(string="Attendance", compute="_compute_attendance_count")
    leave_count = fields.Integer(string="Leaves", compute="_compute_leave_count")

    def _compute_attendance_count(self):
        for rec in self:
            rec.attendance_count = len(rec.attendance_ids)

    def _compute_leave_count(self):
        for rec in self:
            rec.leave_count = len(rec.leave_ids)

    def action_view_attendance(self):
        return {"type": "ir.actions.act_window", "name": "Attendance", "res_model": "hospital.attendance", "view_mode": "list,form", "domain": [("staff_id","=",self.id)], "context": {"default_staff_id": self.id}}

    def action_view_leaves(self):
        return {"type": "ir.actions.act_window", "name": "Leaves", "res_model": "hospital.leave", "view_mode": "list,form", "domain": [("staff_id","=",self.id)], "context": {"default_staff_id": self.id}}

    def action_active(self): self.state = "active"
    def action_on_leave(self): self.state = "on_leave"
    def action_resigned(self): self.state = "resigned"
    def action_terminated(self): self.state = "terminated"