from odoo import models, fields

class HospitalShift(models.Model):
    _name = "hospital.shift"
    _description = "Hospital Shift"
    _rec_name = "name"

    name = fields.Char(string="Shift Name", required=True)
    shift_type = fields.Selection([
        ("morning","Morning"),("evening","Evening"),
        ("night","Night"),("rotating","Rotating"),
    ], string="Shift Type", required=True)
    start_time = fields.Float(string="Start Time")
    end_time = fields.Float(string="End Time")
    description = fields.Text(string="Description")
