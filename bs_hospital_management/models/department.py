from odoo import models, fields

class HospitalDepartment(models.Model):
    _name = "hospital.department"
    _description = "Hospital Department"
    _rec_name = "name"

    name = fields.Char(string="Department Name", required=True)
    code = fields.Char(string="Department Code")
    description = fields.Text(string="Description")
    manager_id = fields.Many2one("hospital.staff", string="Department Manager")
    staff_ids = fields.One2many("hospital.staff", "department_id", string="Staff Members")
    staff_count = fields.Integer(string="Staff Count", compute="_compute_staff_count")

    def _compute_staff_count(self):
        for rec in self:
            rec.staff_count = len(rec.staff_ids)
